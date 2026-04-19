"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from threading import Event, Thread
import uuid

from models import MountOptions, ShareHost
from smbprotocol import exceptions
from smbprotocol.change_notify import ChangeNotifyFlags, CompletionFilter, FileNotifyInformation, FileSystemWatcher
from smbprotocol.connection import Connection
from smbprotocol.open import (
    CreateDisposition,
    CreateOptions,
    DirectoryAccessMask,
    FileAttributes,
    FilePipePrinterAccessMask,
    ImpersonationLevel,
    Open,
    ShareAccess,
)
from smbprotocol.session import Session
from smbprotocol.tree import TreeConnect

from shared_functions.dmis_logger import dms_warning


class ShareWatcher(Thread):
    """Thread class watching for notifications from the SMB share."""

    share_host: ShareHost
    mount_options: MountOptions

    changes: set[str]

    stop_event: Event

    def __init__(self, share_host: ShareHost, mount_options: MountOptions, changes: set[str]) -> None:
        """Constructor."""

        self.share_host = share_host
        self.mount_options = mount_options
        self.changes = changes
        self.stop_event = Event()

        super().__init__()

    def stop(self) -> None:
        """Stop the thread and join."""
        self.stop_event.set()
        self.join()

    def run(self) -> None:
        """Start notification monitoring."""
        connection = Connection(uuid.uuid4(), self.share_host.host, self.share_host.port)
        connection.connect()
        try:
            session = Session(connection, username=self.mount_options.user, password=self.mount_options.password)
            session.connect()
            tree = TreeConnect(session, self.share_host.share.replace("/", "\\"))
            tree.connect()
            dir_open = Open(tree, "")
            dir_open.create(
                ImpersonationLevel.Impersonation,
                DirectoryAccessMask.GENERIC_READ,
                FileAttributes.FILE_ATTRIBUTE_DIRECTORY,
                ShareAccess.FILE_SHARE_READ,
                CreateDisposition.FILE_OPEN_IF,
                CreateOptions.FILE_DIRECTORY_FILE,
            )

            watcher = FileSystemWatcher(dir_open)
            watcher.start(CompletionFilter.FILE_NOTIFY_CHANGE_LAST_WRITE, flags=ChangeNotifyFlags.SMB2_WATCH_TREE)
            while True:
                if self.stop_event.wait(timeout=5):
                    watcher.cancel()
                    break
                results: list[FileNotifyInformation] | None = watcher.result
                if results is None:
                    continue
                watcher = FileSystemWatcher(dir_open)
                watcher.start(
                    CompletionFilter.FILE_NOTIFY_CHANGE_LAST_WRITE | CompletionFilter.FILE_NOTIFY_CHANGE_FILE_NAME,
                    flags=ChangeNotifyFlags.SMB2_WATCH_TREE,
                )
                for result in results:
                    path: str = result["file_name"].get_value()
                    if not self._is_file(tree, path):
                        continue
                    full_path: str = f"{self.mount_options.service_mount}\\{path}".replace("\\", "/")
                    self.changes.add(full_path)

        finally:
            connection.disconnect()

    def _is_file(self, tree: TreeConnect, path: str) -> bool:
        """Check if path leads to a file.

        Args:
            tree: SMB share connection.
            path: path relative to share.
        Returns: True if file, else False
        """

        file = Open(tree, path)
        is_file = True
        try:
            file.create(
                ImpersonationLevel.Impersonation,
                FilePipePrinterAccessMask.GENERIC_READ,
                FileAttributes.FILE_ATTRIBUTE_NORMAL,
                ShareAccess.FILE_SHARE_READ,
                CreateDisposition.FILE_OPEN,
                CreateOptions.FILE_NON_DIRECTORY_FILE,
            )
        except exceptions.FileIsADirectory:
            is_file = False
        except exceptions.SharingViolation:
            dms_warning(f"Sharing violation, impersonation failed for: {path}.")
        finally:
            file.close()
        return is_file
