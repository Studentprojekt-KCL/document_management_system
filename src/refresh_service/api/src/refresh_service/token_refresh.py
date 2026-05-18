"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import asyncio

import aiohttp
from celery import Celery

# Refresh service is not installed in pylint env.
from refresh_service.database import RedisDataBase  # pylint: disable=E0611
from refresh_service.session_encryption_tools import SessionEncryption  # pylint: disable=E0611

from shared_functions.initialisation_tools import read_env_variable
from shared_functions.dmis_logger import dms_warning

DEFAULT_EXPIRY_TIME: int = 1800  # NOTE; 401 should probably be signaled by connector to execute refresh.

REDIS_BROKER = f"redis://{read_env_variable("REFSERVICE_REDIS_HOST")}:{read_env_variable("REFSERVICE_REDIS_PORT")}/0"
CELERY_APP = Celery("celery_application", broker=REDIS_BROKER, backend=REDIS_BROKER)

REDIS_DATABASE = RedisDataBase()

SESSION_ENCRYPTION = SessionEncryption(read_env_variable("REFSERVICE_SESSION_ENC_PASSW"))


async def execute_get_request(url: str, headers: dict | None) -> dict | list:
    """Execute get request to specified URL with specified headers."""
    async with aiohttp.ClientSession() as session, session.get(url, headers=headers) as response:
        return await response.json()


def insert_session(user: str, service_name: str, refresh_url: str, session_variables: dict) -> bool:
    """Insert new session token for given user and service in database."""
    enc_session_vars = SESSION_ENCRYPTION.encrypt_session_vars(session_variables)
    expiry_time = session_variables.get("expires_in")
    if not isinstance(expiry_time, int):
        dms_warning(f"Refresh service recieved Oauth token without expiry_time ({session_variables})")
        expiry_time = DEFAULT_EXPIRY_TIME

    if expiry_time > DEFAULT_EXPIRY_TIME:
        expiry_time = DEFAULT_EXPIRY_TIME

    insert_status = REDIS_DATABASE.insert_session_token(user, service_name, expiry_time, refresh_url, enc_session_vars)
    if insert_status is False:
        return False
    adjusted_expiry_time = expiry_time - 300  # NOTE; This might need to be more dynamic
    session_refresh_task.apply_async(args=[user, service_name], countdown=adjusted_expiry_time)
    return True


def update_session_token(user: str, service: str) -> None:
    """Retrieve new session token for given user and service, and insert in database."""
    session_token, refresh_url = REDIS_DATABASE.get_session_token(user, service)
    decrypted_session = SESSION_ENCRYPTION.decrypt_session_variables(session_token)
    headers = {"refresh-token": decrypted_session.get("refresh_token")}

    new_token = asyncio.run(execute_get_request(refresh_url, headers))
    if not isinstance(new_token, dict):
        dms_warning(f"Unexpected token format recieved (expected dict): {new_token}")
        return
    if insert_session(user, service, refresh_url, new_token) is False:
        dms_warning(f"Failed to update '{user}'s session token for {service}")


@CELERY_APP.task(name="refresh_service.token_refresh.session_refresh_task")
def session_refresh_task(user: str, service: str) -> None:
    """Session refresh task."""
    update_session_token(user, service)


def run() -> None:
    """Entrypoint for celery runner."""
    CELERY_APP.worker_main(argv=["worker", "--loglevel=info"])
