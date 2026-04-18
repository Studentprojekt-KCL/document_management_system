"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from asyncio import Queue, create_task
from os.path import isdir
import aiofiles
import aiofiles.os
from datetime import datetime
from os import scandir
import json
import os
from typing import AsyncGenerator
from dmis_logger import dms_error, dms_info, dms_warning
from services.share_watcher import ShareWatcher
from initialisation_tools import read_env_variable, read_port
from base64 import b64decode, urlsafe_b64decode, urlsafe_b64encode, b64encode
from subprocess import run, CompletedProcess
from pathlib import Path

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

    host: str
    port: int
    share: str
    user: str
    password: str
    service_mount: str
    user_mount: str
    source_system: str

    changes: set[str]
    watcher: ShareWatcher

    start: datetime

    def __init__(self) -> None:
        """Constructor."""
        self.host = read_env_variable("SC_SAMBA_HOST")
        self.port = read_port("SC_SAMBA_PORT")
        self.user = read_env_variable("SC_SAMBA_USER")
        self.password = read_env_variable("SC_SAMBA_PASS")
        self.service_mount = read_env_variable("SC_SAMBA_SERVICE_MOUNT_PATH").rstrip("/")
        self.user_mount = read_env_variable("SC_SAMBA_USER_MOUNT_PATH").rstrip("/")
        self.source_system = read_env_variable("SC_SYSTEM_NAME")

        share = rf"\\{self.host}\{read_env_variable("SC_SAMBA_SHARE")}"
        self.share = share.replace("\\", "/")

        self.changes = set([])

        self._mount(self.user, self.password, self.service_mount)
        self.watcher = ShareWatcher(self.host, self.port, share, self.user, self.password, self.changes)

        self.start = datetime.now()

    def start_watch(self):
        dms_info(f"Launching notification watcher for {self.share}.")
        self.watcher.start()

    def stop_watch(self):
        self.watcher.stop()
        dms_info(f"Closed notification watcher for {self.share}.")

    def get_file_pointers(self) -> dict:
        """Get new files from SMB share.

        Args:
            subdata: date and tim in iso format encoded with base64, represents the newest file date.
        Return: Dict containting a list of file pointers and subdata.

        """
        changes = {}
        changes["pointers"] = list(self.changes)
        changes["subdata"] = urlsafe_b64encode(datetime.now().isoformat().encode("utf-8")).decode("utf-8")
        self.changes.clear()
        return changes

    def check_index_needed(self, subdata: str | None) -> dict:
        if subdata is None:
            changes = self._full_scan(self.service_mount)
            for change in changes:
                self.changes.add(change)
        return {"index_needed": len(self.changes) != 0 }

    def grab_files(self, pointers: list[str], include_content: bool, include_last_edit_date: bool) -> list[dict]:
        self._mount(self.user, self.password, self.user_mount)
        files: list[dict] = []
        for pointer in pointers:
            path: str = f"{self.user_mount}/{pointer.lstrip(self.share)}"
            with open(path, 'r') as f:
                status = os.stat(path)
                metadata = {
                    "unique_pointer": pointer,
                    "name": path.split("/")[-1],
                    "size": status.st_size,
                    "source_system": self.source_system,
                }
                if include_last_edit_date:
                    metadata["last_edit_date"] = datetime.fromtimestamp(status.st_mtime).isoformat()
                file: dict = {"metadata": metadata}
                if include_content:
                    file["content"] = b64encode(f.read().encode("utf-8")).decode("utf-8")
                files.append(file)
        self._umount(self.user_mount)
        return files

    async def stream_files_to_index(self, subdata: str | None) ->  AsyncGenerator[bytes]:
        find_queue: Queue = Queue()
        task_queue: Queue = Queue()
        output_queue: Queue = Queue()
        last_run: datetime | None = datetime.fromisoformat(urlsafe_b64decode(subdata).decode("utf-8")) if subdata is not None else None

        dirs = await self._grab_directories(self.service_mount)
        for dir_path in dirs:
            await find_queue.put(dir_path)

        find_tasks: list = [create_task(self._find_files(last_run, find_queue, task_queue)) for _ in range(self.NUM_WORKERS)]
        load_tasks: list = [create_task(self._load_files(task_queue, output_queue)) for _ in range(self.NUM_WORKERS)]

        async def producer() -> None:
            """Shutdown signaling to each worker defined in stream_files_to_index."""
            await find_queue.join()
            for _ in find_tasks:
                await find_queue.put(None)

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
        while True:
            item: dict | None = await task_queue.get()
            if item is None:
                break

            path: str | None = item.get("path")
            modified: datetime | None = item.get("modified")

            if path is None or modified is None:
                continue

            try:
                async with aiofiles.open(path, 'r') as f:
                    status = await aiofiles.os.stat(path)
                    content = await f.read()
                    file = {
                        "metadata": {
                            "unique_pointer": f"{self.share}/{path.lstrip(self.service_mount)}",
                            "name": path.split("/")[-1],
                            "size": status.st_size,
                            "source_system": self.source_system,
                            "last_edit_date": modified.isoformat()
                        },
                        "content": b64encode(content.encode("utf-8")).decode("utf-8")
                    }
                    await output_queue.put(file)
            except UnicodeDecodeError:
                dms_warning(f"Failed to decode file content (utf-8): {path}")
            except FileNotFoundError:
                dms_warning(f"Could not find file: {path}")
            task_queue.task_done()

    async def _find_files(self, last_date: datetime | None, look_queue: Queue, task_queue: Queue) -> None:
        while True:
            dir_path: str | None = await look_queue.get()
            if dir_path is None:
                break
            try:
                items = await aiofiles.os.scandir(dir_path)
                for item in items:
                    if item.is_file():
                        status = await aiofiles.os.stat(item.path)
                        modified = datetime.fromtimestamp(status.st_mtime)
                        if last_date is None or modified < last_date or last_date < self.start:
                            await task_queue.put({"path": item.path, "modified": modified})
            except FileNotFoundError as e:
                dms_warning(f"Could not find file: {e.filename}")
            look_queue.task_done()

    async def _grab_directories(self, path) -> list[str]:
        items = await aiofiles.os.scandir(path)
        dirs: list[str] = [path]
        for item in items:
            if item.is_dir():
                children = await self._grab_directories(item.path)
                dirs.extend(children)
        return dirs


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
            "-t", "cifs",
            "-o", f"username={username},password={password},iocharset=utf8,port={self.port}",
            self.share.replace("\\","/"),
            path
        ]
        res: CompletedProcess = run(command)
        if res.returncode != 0:
            dms_error(f"Failed to mount Samba share {self.share} with user {self.user}.")
        dms_info(f"Mounted {self.share} at {path}.")

    def _umount(self, path: str) -> None:
        """Unmounts a SMB Share.

        Args:
            path: path to mounted share.
        """

        command: list = ["umount", path]
        res: CompletedProcess = run(command)
        if res.returncode != 0:
            dms_error(f"Failed to unmount Samba share {self.share} at {path}.")
        dms_info(f"Unmounted {self.share} at {path}.")

    def _full_scan(self, path: str) -> list[str]:
        """Preforms a full pointer fetch from the share.

        Expects service level access through service mount,
        environment variable SC_SAMBA_SERVICE_MOUNT_PATH.

        Args:
            path: start path.
        Returns: list of pointers.
        """
        pointers: list[str] = []
        for file in scandir(path):
            if file.is_file():
                pointers.append(f"{self.share}/{file.path.lstrip(self.service_mount)}")
            elif file.is_dir():
                pointers.extend(self._full_scan(file.path))

        return pointers

