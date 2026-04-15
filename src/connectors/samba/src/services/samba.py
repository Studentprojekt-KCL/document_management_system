"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from datetime import datetime
import threading
import uuid
from smbprotocol.connection import Connection
from smbprotocol.session import Session
from smbprotocol.tree import TreeConnect
from smbprotocol.change_notify import ChangeNotifyFlags, CompletionFilter, FileNotifyInformation, FileSystemWatcher
from initialisation_tools import read_env_variable, read_port
from smbclient import register_session, scandir
from base64 import urlsafe_b64encode

from smbprotocol.open import (
    CreateDisposition,
    CreateOptions,
    DirectoryAccessMask,
    FileAttributes,
    ImpersonationLevel,
    Open,
    ShareAccess,
)
from uvicorn.config import is_dir

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

    channges: dict[str, str]

    def __init__(self) -> None:
        """Constructor."""
        self.host = read_env_variable("SC_SAMBA_HOST")
        self.port = read_port("SC_SAMBA_PORT")
        self.share = rf"\\{self.host}\{read_env_variable("SC_SAMBA_SHARE")}"
        self.user = read_env_variable("SC_SAMBA_USER")
        self.password = read_env_variable("SC_SAMBA_PASS")

        self.changes = {}
        register_session(self.host, port=self.port, username=self.user, password=self.password)


    def start_watch(self):
        thread = threading.Thread(
            target=Samba._watch_files,
            args=(self.host, self.port, self.share, self.user, self.password, self.changes)
        ) 
        thread.start()
    
    @staticmethod
    def _watch_files(host: str, port: int, share: str, user: str, password: str, changes: dict[str, str]):
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
                    print(type(path))
                    pointer: str = f"{share}\\{path}".replace("\\", "/")
                    changes[path] = pointer
                        
        finally:
            connection.disconnect()

    def _full_scan(self, path: str) -> list[str]:
        pointers: list[str] = []
        print(f"checking: {path}")
        for file in scandir(rf"{path}"):
            if file.is_file():
                pointers.append(file.path.replace("\\", "/"))
            elif file.is_dir():
                pointers.extend(self._full_scan(file.path))

        return pointers

    def get_files(self, subdata: str | None) -> dict:
        """Get new files from SMB share.

        Args:
            subdata: date and tim in iso format encoded with base64, represents the newest file date.
        Return: Dict containting a list of file pointers and subdata.

        """
        changes = {}
        if subdata is None:
            changes["pointers"] = self._full_scan(self.share)
            changes["subdata"] = urlsafe_b64encode("jeppe".encode("utf-8")).decode("utf-8")
        else:
            changes["pointers"] = [item for item in self.changes.values()]
            changes["subdata"] = urlsafe_b64encode("jeppe".encode("utf-8")).decode("utf-8")
            self.changes.clear()
        return changes
