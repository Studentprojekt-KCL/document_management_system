from os import environ
from subprocess import run, CompletedProcess
from dmis_logger import dms_error

class Samba:
    host: str | None
    share: str | None
    user: str | None
    password: str | None

    def __init__(self) -> None:
        host: str | None = environ.get("SC_SAMBA_HOST")
        share: str | None = environ.get("SC_SAMBA_SHARE")
        user: str | None = environ.get("SC_SAMBA_USER")
        password: str | None = environ.get("SC_SAMBA_PASS")

        if host is None: dms_error("Expected variable SC_SAMBA_HOST to be defined.")
        if share is None: dms_error("Expected variable SC_SAMBA_SHARE to be defined.")
        if user is None: dms_error("Expected variable SC_SAMBA_USER to be defined.")
        if password is None: dms_error("Expected variable SC_SAMBA_PASS to be defined.")

        self.host = host
        self.share = share
        self.user = user
        self.password = password

    def mount(self) -> None:
        command: str = f"mount --mkdir -t cifs //{self.host}/{self.share} /mnt -o username={self.user},password={self.password},iocharset=utf8,uid=1000,gid=1000"
        res: CompletedProcess = run(command)
        if res.returncode != 0:
            dms_error(f"Failed to mount Samba share {self.host}/{self.share} with user {self.user}.")
