"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from datetime import datetime
import base64
from os import DirEntry, environ, scandir, walk
import os
from subprocess import run, CompletedProcess
from dmis_logger import dms_error


class Samba:
    """Service for the Samba contection.

    Variables:
        host: string containing the host of the SMB share.
        share: name of the share.
        user: user to access the share with.
        password: user password.
        path: where to mount the share.
    """

    host: str | None
    share: str | None
    user: str | None
    password: str | None
    path: str

    def __init__(self) -> None:
        """Constructor."""
        host: str | None = environ.get("SC_SAMBA_HOST")
        share: str | None = environ.get("SC_SAMBA_SHARE")
        user: str | None = environ.get("SC_SAMBA_USER")
        password: str | None = environ.get("SC_SAMBA_PASS")
        path: str = environ.get("SC_SAMBA_PATH", "/mnt")

        if host is None:
            dms_error("Expected variable SC_SAMBA_HOST to be defined.")
        if share is None:
            dms_error("Expected variable SC_SAMBA_SHARE to be defined.")
        if user is None:
            dms_error("Expected variable SC_SAMBA_USER to be defined.")
        if password is None:
            dms_error("Expected variable SC_SAMBA_PASS to be defined.")

        self.host = host
        self.share = share
        self.user = user
        self.password = password
        self.path = path

    def mount(self) -> None:
        """Mount the SMB share."""
        command: list = [
            "mount",
            "-t",
            "cifs",
            "-o",
            f"username={self.user},password={self.password},iocharset=utf8,actimeo=60",
            f"//{self.host}/{self.share}",
            f"{self.path}",
        ]
        res: CompletedProcess = run(command)
        if res.returncode != 0:
            dms_error(f"Failed to mount Samba share {self.host}/{self.share} with user {self.user}.")

    def _scan_dir(self, path: str, last_time: datetime | None) -> list[str]:
        pointers: list[str] = []
        with scandir(path) as dir:
            for entry in dir:
                if entry.is_file():
                    edited = datetime.fromtimestamp(entry.stat().st_mtime)
                    if last_time is None or edited > last_time:
                        pointers.append(f"//{self.host}/{self.share}{entry.path}")
                elif entry.is_dir():
                    pointers.extend(self._scan_dir(entry.path, last_time))
        return pointers


    def get_files(self, subdata: str | None) -> dict:
        """Get new files from SMB share.

        Args:
            subdata: date and tim in iso format encoded with base64, represents the newest file date.
        Return: Dict containting a list of file pointers and subdata.

        """
        last_edit: datetime | None = None

        if subdata is not None:
            last_edit = datetime.fromisoformat(base64.b64decode(subdata).decode("utf-8"))

        pointers: list = self._scan_dir(self.path, last_edit)
        subdata = base64.b64encode(datetime.now().isoformat().encode("utf-8")).decode("utf-8")

        return {"pointers": pointers, "subdata": subdata}
