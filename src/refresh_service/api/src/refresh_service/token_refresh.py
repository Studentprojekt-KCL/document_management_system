"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import aiohttp
import asyncio

from celery import Celery

from refresh_service.database import RedisDataBase

from refresh_service.session_encryption_tools import SessionEncryption
from shared_functions.initialisation_tools import read_env_variable
from shared_functions.dmis_logger import dms_warning


DEFAULT_EXPIRY_TIME: int = 1800 #NOTE; 401 should probably be signaled by connector to execute refresh.

redis_broker = f"redis://{read_env_variable("REFSERVICE_REDIS_HOST")}:{read_env_variable("REFSERVICE_REDIS_PORT")}/0"
celery_app = Celery(
            "celery_application",
            broker=redis_broker,
            backend=redis_broker
        )

redis_database = RedisDataBase()

session_encryption = SessionEncryption(read_env_variable("REFSERVICE_SESSION_ENC_PASSW"))

async def exexute_get_request(url, headers):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            return await response.json()


def insert_session(user: str, service_name: str, refresh_url: str, session_variables: dict) -> bool:
    enc_session_vars = session_encryption.encrypt_session_vars(session_variables)
    expiry_time = session_variables.get("expires_in")
    if expiry_time is None:
        dms_warning(f"Refresh service recieved Oauth token without expiry_time ({session_variables})")
        expiry_time = DEFAULT_EXPIRY_TIME

    insert_status = redis_database.insert_session_token(user, service_name, expiry_time, refresh_url, enc_session_vars)
    if insert_status is False:
        return False
    adjusted_expiry_time = expiry_time - 7195 #TODO; update this
    session_refresh_task.apply_async(args=[user, service_name], countdown=adjusted_expiry_time)
    return True


def update_session_token(user, service):
    session_token, refresh_url = redis_database.get_session_token(user, service)
    decrypted_session = session_encryption.decrypt_session_variables(session_token)
    headers = {"refresh-token": decrypted_session.get("refresh_token")}

    new_token = asyncio.run(exexute_get_request(refresh_url, headers))

    if insert_session(user, service, refresh_url, new_token) is False:
        dms_warning(f"Failed to update '{user}'s session token for {service}")


@celery_app.task(name="refresh_service.token_refresh.session_refresh_task")
def session_refresh_task(user, service):
    update_session_token(user, service)

def run():
    celery_app.worker_main(argv=['worker', '--loglevel=info'])
