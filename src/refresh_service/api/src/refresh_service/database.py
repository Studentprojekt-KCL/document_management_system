"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import time

from shared_functions.initialisation_tools import read_env_variable
from shared_functions.dmis_logger import dms_warning

from mysql import connector

from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.pooling import PooledMySQLConnection

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

    def connect(self) -> PooledMySQLConnection | MySQLConnectionAbstract:
        """Return database connection."""
        return connector.connect(host=self.host, user=self.user, database=self.database, password=self.password)

    def get_session_token(self, user: str, service: str):
        """Retrive session token from database.

        Args:
        ----
            user: Users sub UUID.
            service: Name of service token authenticates against.
        """
        db = self.connect()
        cursor = db.cursor()
        query: str = "SELECT token FROM user_sessions WHERE user_id = %s AND service = %s"
        _ = cursor.execute(query, (user, service))
        result = cursor.fetchall()

        if len(result) != 1:
            return []

        return result[0][0]

    def insert_session_token(self, user: str, service: str, enc_obj: str, expiry_time: int) -> bool:
        """Insert encrypted user tokens into database.

        Args:
        ----
            user: Users sub UUID.
            service: Name of service token authenticates against.
            enc_obj: Encrypted session token.
            expiry_time: Number of seconds until token expires.

        Returns:
        -------
            True if insertion was possible, else false.
        """
        success: bool = False
        timestamp = int(time.time()) + expiry_time

        try:
            db = self.connect()
            cursor = db.cursor()
            sql = """
            INSERT INTO user_sessions (user_id, service, token, expiry_time)
            VALUES (%s, %s, %s, FROM_UNIXTIME(%s))
            ON DUPLICATE KEY UPDATE
                token = %s,
                expiry_time = FROM_UNIXTIME(%s)
            """
            cursor.execute(sql, (user, service, enc_obj, timestamp, enc_obj, timestamp))
            db.commit()
            success = True
        except connector.Error as err:
            dms_warning(f"Unable to insert session value into database: {err}")
        finally:
            cursor.close()
            db.close()

        return success
