"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from asyncio import Queue, create_task
from datetime import datetime
from os import scandir
import json
import os
from collections.abc import AsyncGenerator
from base64 import b64decode, urlsafe_b64decode, urlsafe_b64encode, b64encode
from pathlib import Path

from subprocess import CalledProcessError, run
from uuid import uuid4
import aiofiles
import aiofiles.os

from smbprotocol.connection import Connection
from smbprotocol.session import Session

from models import FileInfo, MountOptions, ShareHost
from services.share_watcher import ShareWatcher
from shared_functions.dmis_logger import dms_error, dms_info, dms_warning
from shared_functions.initialisation_tools import read_env_variable, read_port
from shared_functions.file_type_logic import determine_file_type, get_file_resource
from smbprotocol.exceptions import LogonFailure


class Samba:
    """Service for the Samba contection.

    Variables:
        host: string containing the host of the SMB share.
        share: name of the share.
        user: user to access the share with.
        password: user password.
        path: where to mount the share.
    """

    NUM_WORKERS: int = 16

    file_info: FileInfo
    share_host: ShareHost
    mount_options: MountOptions

    source_system: str

    changes: set[str]
    watcher: ShareWatcher

    start: datetime

    def __init__(self) -> None:
        """Constructor."""

        host = read_env_variable("CONSMB_SMB_SHARE_ADDR")
        port = read_port("CONSMB_SMB_SHARE_PORT")
        user = read_env_variable("CONSMB_SMB_SHARE_SERVICE_USER")
        password = read_env_variable("CONSMB_SMB_SHARE_SERVICE_PASS")
        service_mount = read_env_variable("CONSMB_SMB_SERVICE_MOUNT_PATH").rstrip("/")  # type: ignore
        user_mount = read_env_variable("CONSMB_SMB_USER_MOUNT_PATH").rstrip("/")  # type: ignore
        self.source_system = read_env_variable("CONSMB_SYSTEM_NAME")  # type: ignore

        share = rf"//{host}/{read_env_variable("CONSMB_SMB_SHARE_NAME")}"

        self.share_host = ShareHost(host, port, share)  # type: ignore
        self.mount_options = MountOptions(user, password, service_mount, user_mount)  # type: ignore

        file_extentions = []
        extention_descriptions = {}

        file_types: list = get_file_resource()
        for file_type in file_types:
            extension: str | None = file_type.get("extension")
            description: str | None = file_type.get("description")
            if extension is None or description is None:
                continue
            file_extentions.append(extension)
            extention_descriptions[extension] = description

        self.file_info = FileInfo(file_extentions, extention_descriptions)

        try:
            self._mount(user, password, service_mount)  # type: ignore
        except CalledProcessError:
            dms_error(f"Failed to mount {share} at {service_mount} as {user}.")

        self.changes = set([])
        self.watcher = ShareWatcher(self.share_host, self.mount_options, self.changes)

        self.start = datetime.now()

    def start_watch(self) -> None:
        """Start notification watcher."""
        dms_info(f"Launching notification watcher for {self.share_host.share}.")
        self.watcher.start()

    def stop_watch(self) -> None:
        """Stop notification watcher."""
        self.watcher.stop()
        dms_info(f"Closed notification watcher for {self.share_host.share}.")

    async def check_index_needed(self, subdata: str | None) -> dict:
        """Check if an index is needed.

        Args:
            subdata: base64 encoded date.
        Returns: dict with true or false.
        """

        last: datetime | None = datetime.fromisoformat(urlsafe_b64decode(subdata).decode("utf-8")) if subdata is not None else None
        index_needed = False
        if last is None or last < self.start:
            index_needed = await self._full_check(self.mount_options.service_mount, last)
        else:
            index_needed = len(self.changes) != 0
        return {"index_needed": index_needed}

    def check_auth(self, authorization: str | None) -> bool:
        """Check if credentials are valid.

        Args:
            authorization: credentials in base64
        Returns: true / false
        """
        if authorization is None:
            return False

        username: str | None = None
        password: str | None = None
        try:
            username, password = tuple(b64decode(authorization.lstrip("Basic").encode("utf-8")).decode("utf-8").split(":"))
        except (UnicodeDecodeError, UnicodeEncodeError, ValueError) as err:
            dms_warning(f"Failed to decode authorization: {err}")
        if username is None or password is None:
            return False

        connection = Connection(uuid4(), self.share_host.host, self.share_host.port)
        try:
            connection.connect()
            session = Session(connection, username, password)
            session.connect()
        except LogonFailure:
            return False
        finally:
            connection.disconnect(True)
        return True

    def grab_files(self, content: dict, authorization: str, include_content: bool, include_last_edit_date: bool) -> list[dict]:
        """Grab the requested files.

        Mounts the share as the requesting user and grabs the requested files.

        Args:
            content: json body.
            include_content: to include file content or not.
            include_last_edit_date: to include the modification date.
        Returns: list of files.
        """
        username: str | None = None
        password: str | None = None
        try:
            username, password = tuple(b64decode(authorization.lstrip("Basic").encode("utf-8")).decode("utf-8").split(":"))
        except UnicodeDecodeError:
            dms_warning("Failed to decode authorization header for base64 decoding.")
        except UnicodeEncodeError:
            dms_warning("Failed to encode authorization header after base64 decoding.")
        except ValueError:
            dms_warning("Might be too many arguments in authorization header.")
        pointers: list[str] | None = content.get("file_pointers")

        if pointers is None or username is None or password is None:
            return []

        try:
            self._mount(username, password, self.mount_options.user_mount)
        except CalledProcessError:
            return []

        files: list[dict] = []
        for pointer in pointers:
            path: str = f"{self.mount_options.user_mount}{pointer[len(self.share_host.share):]}"
            try:
                with open(path, "rb") as f:
                    status = os.stat(path)
                    name: str = path.rsplit("/", maxsplit=1)[-1]
                    file = {
                        "unique_pointer": pointer,
                        "name": name,
                        "size": status.st_size,
                        "source_system": self.source_system,
                    } | determine_file_type(name, self.file_info.file_extentions, self.file_info.extention_descriptions)
                    if include_last_edit_date:
                        file["last_edit_date"] = datetime.fromtimestamp(status.st_mtime).isoformat()
                    if include_content:
                        file["content"] = b64encode(f.read()).decode("utf-8")
                    files.append(file)
            except FileNotFoundError:
                dms_warning(
                    f"Failed to read file: {path}, {self.share_host.share}, {pointer}, {pointer[len(self.share_host.share):]}."
                )
        try:
            self._umount(self.mount_options.user_mount)
        except CalledProcessError:
            dms_warning(f"Failed to umount {self.share_host.share} at {self.mount_options.user_mount}.")

        return files

    async def stream_files_to_index(self, subdata: str | None) -> AsyncGenerator[bytes]:
        """Stream new content from SMB.

        If the subdatas last run date is none, grab all files on the SMB. If it is before the
        startup date, check all files on the SMB and grab the files with a modification date
        earlier than it. If it is after the start up date, use the changes set.

        Args:
            subdata: base64 encoded date.
        Returns: Stream of data.
        """

        task_queue: Queue = Queue()
        output_queue: Queue = Queue()
        last_run: datetime | None = (
            datetime.fromisoformat(urlsafe_b64decode(subdata).decode("utf-8")) if subdata is not None else None
        )

        if last_run is None or last_run < self.start:
            await self._find_files(last_run, self.mount_options.service_mount, task_queue)
        else:
            for file_path in self.changes:
                await task_queue.put(file_path)
            self.changes.clear()

        load_tasks: list = [create_task(self._load_files(task_queue, output_queue)) for _ in range(self.NUM_WORKERS)]

        async def producer() -> None:
            """Shutdown signaling to each worker defined in stream_files_to_index."""
            await task_queue.join()
            for _ in load_tasks:
                await task_queue.put(None)

            await output_queue.put(None)

        create_task(producer())

        yield json.dumps({"subdata": urlsafe_b64encode(datetime.now().isoformat().encode("utf-8")).decode("utf-8")}).encode("utf-8")

        while True:
            chunk = await output_queue.get()
            if chunk is None:
                break
            yield json.dumps({"data": chunk}).encode("utf-8")

    async def _load_files(self, task_queue: Queue, output_queue: Queue) -> None:
        """Load file content and metadata, and prepear it for transfer.

        Args:
            task_queue: files to load.
            output_queue: files ready for transfer.
        """

        while True:
            path: str | None = await task_queue.get()
            if path is None:
                break

            try:
                async with aiofiles.open(path, mode="rb") as f:
                    status = await aiofiles.os.stat(path)
                    content = await f.read()
                    name = path.split("/")[-1]
                    extention_description = determine_file_type(
                        name, self.file_info.file_extentions, self.file_info.extention_descriptions
                    )
                    file = {
                        "metadata": {
                            "unique_pointer": f"{self.share_host.share}/{path.lstrip(self.mount_options.service_mount)}",
                            "name": name,
                            "size": status.st_size,
                            "source_system": self.source_system,
                            "last_edit_date": datetime.fromtimestamp(status.st_mtime).isoformat(),
                        }
                        | extention_description,
                        "content": b64encode(content).decode("utf-8"),
                    }
                    await output_queue.put(file)
            except UnicodeDecodeError:
                dms_warning(f"Failed to decode file content (utf-8): {path}")
            except FileNotFoundError:
                dms_warning(f"Could not find file: {path}")
            task_queue.task_done()

    async def _find_files(self, last_date: datetime | None, path: str, task_queue: Queue) -> None:
        """Walk through a directory checking for new/modified files.

        Args:
            last_date: Last time it ran.
            path: directory path.
            task_queue: load tasks.
        """

        dirs = [path]
        while dirs:
            items = await aiofiles.os.scandir(dirs.pop())
            for item in items:
                if item.is_file():
                    status = await aiofiles.os.stat(item.path)
                    modified = datetime.fromtimestamp(status.st_mtime)
                    if last_date is None or modified > last_date:
                        await task_queue.put(item.path)
                elif item.is_dir():
                    dirs.append(item.path)

    async def _full_check(self, path: str, last: datetime | None) -> bool:
        """Preforms a full pointer fetch from the share.

        Expects service level access through service mount,
        environment variable SC_SAMBA_SERVICE_MOUNT_PATH.

        Args:
            path: start path.
        Returns: list of pointers.
        """

        for file in scandir(path):
            if file.is_file():
                stats = await aiofiles.os.stat(file.path)
                if last is None or last < datetime.fromtimestamp(stats.st_mtime):
                    return True
            elif file.is_dir():
                if await self._full_check(file.path, last):
                    return True

        return False

    def _mount(self, username: str, password: str, path: str) -> None:
        """Mount a SMB share.

        Args:
            username: username for authentication.
            password: password for user.
            path: where to mount it.
        """

        if not os.path.isdir(path):
            Path(path).mkdir(parents=True, exist_ok=True)
        command = [
            "mount",
            "-t",
            "cifs",
            "-o",
            f"username={username},password={password},port={self.share_host.port}",
            self.share_host.share.replace("\\", "/"),
            path,
        ]
        run(command, check=True)

    def _umount(self, path: str) -> None:
        """Unmounts a SMB Share.

        Args:
            path: path to mounted share.
        """

        command: list = ["umount", path]
        run(command, check=True)
