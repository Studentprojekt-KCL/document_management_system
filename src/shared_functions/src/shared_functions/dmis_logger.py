"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import os
from datetime import datetime
from logging import error, warning, info
from typing import Any
from socket import gethostname

import requests


def dms_error(msg: str, *_: Any, **__: Any) -> None:
    """Logging service which will handeling errors.

    Args:
    ----
        msg: Error message.
    """
    error(f"[{datetime.now().strftime("%Y-%m-%d:%H:%M:%S")}] {msg}")
    timestamp: datetime = datetime.now()
    log_service = os.environ.get("LOG_SERVICE")
    if not isinstance(log_service, str) and not os.environ.get("SERVICE_NOT_SET_SENT"):
        warning("Log service not set, export 'LOG_SERVICE'.")
        os.environ["SERVICE_NOT_SET_SENT"] = "true"
        os._exit(1)
    if not isinstance(log_service, str):
        os._exit(1)
    _res = requests.post(
        log_service,
        json={
            "service": gethostname(),  # Probably not the best solution
            "message": msg,
            "event_type": "ERROR",
            "occured": timestamp.isoformat(),
        },
        timeout=60,
    )
    os._exit(1)


def dms_warning(msg: str, *_: Any, **__: Any) -> None:
    """Logging service which will handeling warnings.

    Args:
    ----
        msg: Warning message.
    """
    warning(f"[{datetime.now().strftime("%Y-%m-%d:%H:%M:%S")}] {msg}")
    timestamp: datetime = datetime.now()
    log_service = os.environ.get("LOG_SERVICE")
    if not isinstance(log_service, str) and not os.environ.get("SERVICE_NOT_SET_SENT"):
        warning("Log service not set, export 'LOG_SERVICE'.")
        os.environ["SERVICE_NOT_SET_SENT"] = "true"
        return
    if not isinstance(log_service, str):
        return
    _res = requests.post(
        log_service,
        json={
            "service": gethostname(),  # Probably not the best solution
            "message": msg,
            "event_type": "WARNING",
            "occured": timestamp.isoformat(),
        },
        timeout=60,
    )


def dms_info(msg: str, *_: Any, **__: Any) -> None:
    """Logging service which will handeling info messages.

    Args:
    ----
        msg: Info message.
    """
    info(f"[{datetime.now().strftime("%Y-%m-%d:%H:%M:%S")}] {msg}")
    timestamp: datetime = datetime.now()
    log_service = os.environ.get("LOG_SERVICE")
    if not isinstance(log_service, str) and not os.environ.get("SERVICE_NOT_SET_SENT"):
        warning("Log service not set, export 'LOG_SERVICE'.")
        os.environ["SERVICE_NOT_SET_SENT"] = "true"
        return
    if not isinstance(log_service, str):
        return
    _res = requests.post(
        log_service,
        json={
            "service": gethostname(),  # Probably not the best solution
            "message": msg,
            "event_type": "INFO",
            "occured": timestamp.isoformat(),
        },
        timeout=60,
    )
