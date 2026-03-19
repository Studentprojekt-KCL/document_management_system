from datetime import datetime
from os import environ, walk
import os
from subprocess import run, CompletedProcess
from dmis_logger import dms_error

class Samba:
    host: str | None
    share: str | None
    user: str | None
    password: str | None
    path: str

    def __init__(self) -> None:
        host: str | None = environ.get("SC_SAMBA_HOST")
        share: str | None = environ.get("SC_SAMBA_SHARE")
        user: str | None = environ.get("SC_SAMBA_USER")
        password: str | None = environ.get("SC_SAMBA_PASS")
        path: str = environ.get("SC_SAMBA_PATH", "/mnt")

        if host is None: dms_error("Expected variable SC_SAMBA_HOST to be defined.")
        if share is None: dms_error("Expected variable SC_SAMBA_SHARE to be defined.")
        if user is None: dms_error("Expected variable SC_SAMBA_USER to be defined.")
        if password is None: dms_error("Expected variable SC_SAMBA_PASS to be defined.")

        self.host = host
        self.share = share
        self.user = user
        self.password = password
        self.path = path

    def mount(self) -> None:
        command: list = [
            "mount",
            "-t", "cifs",
            "-o", f"username={self.user},password={self.password},iocharset=utf8",
            f"//{self.host}/{self.share}",
            f"{self.path}"
        ]
        res: CompletedProcess = run(command)
        if res.returncode != 0:
            dms_error(f"Failed to mount Samba share {self.host}/{self.share} with user {self.user}.")

    def get_files(self, subdata: str) -> list:
        pointers: list = []


        for (root, dirs, files) in walk("/mnt"):
            for file in files:
                file_path = f"{root}/{file}"
                edited = datetime.fromtimestamp(os.path.getmtime(file_path))
                print(f"{file_path}: {edited.isoformat()}")
                pointers.append(f"{file_path}")

        return pointers
