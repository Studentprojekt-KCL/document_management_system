from os import environ

from se_api.exceptions import SeAPIException

class MinIO:
    host: str
    user: str
    password: str

    def __init__(self) -> None:
        host: str | None = environ.get("SE_API_MINIO_HOST")
        user: str | None = environ.get("SE_API_MINIO_USER")
        password: str | None = environ.get("SE_API_MINIO_PASSWORD")

        if host is None:
            raise SeAPIException("Environment varibale SE_API_MINIO_HOST is not set.")
        if user is None:
            raise SeAPIException("Environment varibale SE_API_MINIO_USER is not set.")
        if password is None:
            raise SeAPIException("Environment varibale SE_API_MINIO_USER is not set.")

        self.host = host
        self.user = user
        self.password = password

