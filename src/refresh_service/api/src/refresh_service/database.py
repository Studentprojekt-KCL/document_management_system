"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from mysql import connector
from shared_functions.initialisation_tools import read_env_variable

class Database:
    """Service class for the database."""

    host: str
    user: str
    password: str
    database: str

    def __init__(self) -> None:
        self.host = read_env_variable("REFSERVICE_DB_URL")
        self.user = read_env_variable("REFSERVICE_DB_USER")
        self.password = read_env_variable("REFSERVICE_DB_PASSW")
        self.database = read_env_variable("REFSERVICE_DB_DATABASE")
