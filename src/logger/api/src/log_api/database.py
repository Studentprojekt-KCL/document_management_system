"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

import os
import mysql.connector
from .models import Log


def connect():
    """Return database connection."""

    host = os.environ.get("LOGGER_DB_HOST")
    user = os.environ.get("LOGGER_DB_USER")
    password = os.environ.get("LOGGER_DB_PASS")
    database = os.environ.get("LOGGER_DB_DATABASE")

    return mysql.connector.connect(host=host, user=user, database=database, password=password)


def database_get_logs():
    """Grab all logs."""

    db = connect()
    cursor = db.cursor()
    _ = cursor.execute("SELECT * FROM logs")
    results = cursor.fetchall()
    for result in results:
        print(result)


def database_add_log(log: Log) -> Log:
    """Add new log to database and return a Log."""

    db = connect()
    cursor = db.cursor()
    sql = "INSERT INTO logs (occured, message, event_type, service) VALUES (%s, %s, %s, %s)"
    _ = cursor.execute(sql, log.to_values())
    _ = db.commit()
    return log
