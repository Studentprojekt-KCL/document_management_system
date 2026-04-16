"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from datetime import datetime
from os import scandir
import threading
import uuid
from dmis_logger import dms_error, dms_info
from smbprotocol.connection import Connection
from smbprotocol.session import Session
from smbprotocol.tree import TreeConnect
from smbprotocol.change_notify import ChangeNotifyFlags, CompletionFilter, FileNotifyInformation, FileSystemWatcher
from initialisation_tools import read_env_variable, read_port
from base64 import urlsafe_b64encode
from subprocess import run, CompletedProcess

from smbprotocol.open import (
    CreateDisposition,
    CreateOptions,
    DirectoryAccessMask,
    FileAttributes,
    ImpersonationLevel,
    Open,
    ShareAccess,
)

class Samba:
    """Service for the Samba contection.

    Variables:
        host: string containing the host of the SMB share.
        share: name of the share.
        user: user to access the share with.
        password: user password.
        path: where to mount the share.
    """

    host: str
    port: int
    share: str
    user: str
    password: str
    mount_path: str

    changes: set[str]

    def __init__(self) -> None:
        """Constructor."""
        self.host = read_env_variable("SC_SAMBA_HOST")
        self.port = read_port("SC_SAMBA_PORT")
        self.share = rf"\\{self.host}\{read_env_variable("SC_SAMBA_SHARE")}"
        self.user = read_env_variable("SC_SAMBA_USER")
        self.password = read_env_variable("SC_SAMBA_PASS")
        self.mount_path = read_env_variable("SC_SAMBA_MOUNT_PATH")

        self.changes = set([])

    def start_watch(self):
        thread = threading.Thread(
            target=Samba._watch_files,
            args=(self.host, self.port, self.share, self.user, self.password, self.changes)
        ) 
        thread.start()
    
    @staticmethod
    def _watch_files(host: str, port: int, share: str, user: str, password: str, changes: set[str]):
        connection = Connection(uuid.uuid4(), host, port)
        connection.connect()
        try:
            session = Session(connection, username=user, password=password)
            session.connect()
            tree = TreeConnect(session, share)
            tree.connect()
            dir_open = Open(tree, "")
            dir_open.create(
                ImpersonationLevel.Impersonation,
                DirectoryAccessMask.GENERIC_READ,
                FileAttributes.FILE_ATTRIBUTE_DIRECTORY,
                ShareAccess.FILE_SHARE_READ | ShareAccess.FILE_SHARE_WRITE,
                CreateDisposition.FILE_OPEN_IF,
                CreateOptions.FILE_DIRECTORY_FILE,
            )
            while True:
                watcher = FileSystemWatcher(dir_open) 
                watcher.start(
                    CompletionFilter.FILE_NOTIFY_CHANGE_LAST_WRITE,
                    flags=ChangeNotifyFlags.SMB2_WATCH_TREE
                )
                results: list[FileNotifyInformation] | None = watcher.wait()
                if results is None:
                    continue
                for result in results:
                    path: str = result["file_name"].get_value()
                    pointer: str = f"{share}\\{path}".replace("\\", "/")
                    changes.add(pointer)
                        
        finally:
            connection.disconnect()

    def _mount(self):
        command: list = [
            "mount",
            "-t", "cifs",
            "-o", f"username={self.user},password={self.password},iocharset=utf8,port={self.port}",
            self.share.replace("\\","/"),
            self.mount_path
        ]
        res: CompletedProcess = run(command)
        if res.returncode != 0:
            dms_error(f"Failed to mount Samba share {self.share} with user {self.user}.")

    def _full_scan(self, path: str) -> list[str]:
        pointers: list[str] = []
        for file in scandir(path):
            if file.is_file():
                pointers.append(file.path)
            elif file.is_dir():
                pointers.extend(self._full_scan(file.path))

        return pointers

    def inital_run(self):
        dms_info("Mounting smb.")
        self._mount() 
        dms_info("Find files.")
        changes = self._full_scan(self.mount_path)
        for change in changes:
            self.changes.add(change)

    def get_files(self) -> dict:
        """Get new files from SMB share.

        Args:
            subdata: date and tim in iso format encoded with base64, represents the newest file date.
        Return: Dict containting a list of file pointers and subdata.

        """
        changes = {}
        changes["pointers"] = self.changes
        changes["subdata"] = urlsafe_b64encode("jeppe".encode("utf-8")).decode("utf-8")
        self.changes.clear()
        print(len(changes["pointers"]))
        return changes

    def check_index_needed(self) -> dict:
        return {"index_needed": self.changes != {}}
