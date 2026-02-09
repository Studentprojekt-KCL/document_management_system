import mysql.connector
import os
from .models import Log

def connect():
    host = os.environ.get('LOGGER_DB_HOST')
    user = os.environ.get('LOGGER_DB_USER')
    password = os.environ.get('LOGGER_DB_PASS')
    database = os.environ.get('LOGGER_DB_DATABASE')

    return mysql.connector.connect(
        host=host,
        user=user,
        database=database,
        password=password
    )


def database_get_logs():
    db = connect()
    cursor = db.cursor()
    _ = cursor.execute("SELECT * FROM logs")
    results = cursor.fetchall()
    for result in results:
        print(result)


def database_add_log(log: Log) -> Log:
    db = connect()
    cursor = db.cursor()
    sql = "INSERT INTO logs (occured, message, event_type, service) VALUES (%s, %s, %s, %s)"
    val = (log.occured, log.message, log.event_type, log.service)
    _ = cursor.execute(sql, val)
    _ = db.commit()
    return log
