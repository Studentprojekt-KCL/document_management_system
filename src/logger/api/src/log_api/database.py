"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from datetime import datetime
import mysql.connector
from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.pooling import PooledMySQLConnection
from mysql.connector.types import RowItemType, RowType
from log_api.models import Log

from shared_functions.initialisation_tools import read_env_variable


class Database:
    """Service class for the database."""

    host: str
    user: str
    password: str
    database: str

    def __init__(self) -> None:
        self.host = read_env_variable("LOGGER_DB_HOST")
        self.user = read_env_variable("LOGGER_DB_USER")
        self.password = read_env_variable("LOGGER_DB_PASS")
        self.database = read_env_variable("LOGGER_DB_DATABASE")

    def connect(self) -> PooledMySQLConnection | MySQLConnectionAbstract:
        """Return database connection."""
        return mysql.connector.connect(host=self.host, user=self.user, database=self.database, password=self.password)

    def extract_row_data(self, row: RowType | dict[str, RowItemType]) -> Log:
        """Extract each values from a row validating the type.

        Keyword arguments:
        row -- Row from the database.
        """

        if not isinstance(row, tuple):
            raise TypeError("Row is of wrong type.")

        log_id: int | None = row[0] if isinstance(row[0], int) else None
        occured: datetime | None = row[1] if isinstance(row[1], datetime) else None
        message: str | None = row[2] if isinstance(row[2], str) else None
        event_type: str | None = row[3] if isinstance(row[3], str) else None
        service: str | None = row[4] if isinstance(row[4], str) else None

        if log_id is None:
            raise TypeError("Id is of wrong type.")
        if occured is None:
            raise TypeError("Occured is of wrong type.")
        if message is None:
            raise TypeError("Message is of wrong type.")
        if event_type is None:
            raise TypeError("Event Type is of wrong type.")
        if service is None:
            raise TypeError("Service is of wrong type.")

        return Log(id=log_id, occured=occured, message=message, event_type=event_type, service=service)

    def database_get_logs(self, start: datetime, end: datetime) -> list[Log]:
        """Grab all logs."""

        db = self.connect()
        cursor = db.cursor()
        query: str = "SELECT * FROM logs WHERE occured BETWEEN %s AND %s"
        _ = cursor.execute(query, (start, end))
        result = cursor.fetchall()

        return [self.extract_row_data(row) for row in result]

    def database_add_log(self, log: Log) -> Log:
        """Add new log to database and return a Log."""

        db = self.connect()
        cursor = db.cursor()
        sql = "INSERT INTO logs (occured, message, event_type, service) VALUES (%s, %s, %s, %s)"
        _ = cursor.execute(sql, log.to_values())
        _ = db.commit()
        return log
