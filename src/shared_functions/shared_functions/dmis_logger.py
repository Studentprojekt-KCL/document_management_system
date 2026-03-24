"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import os
from logging import error, warning, info
from datetime import datetime
from typing import Any
from socket import gethostname

import requests


def dms_error(msg: str, *_: Any, **__: Any) -> None:
    """Logging service which will handeling errors.

    Args:
    ----
        msg: Error message.
    """
    error(msg)
    timestamp: datetime = datetime.now()
    log_service = os.environ.get("LOG_SERVICE")
    if not isinstance(log_service, str):
        warning("Log service not set, export 'LOG_SERVICE'.")
    else:
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
    warning(msg)
    timestamp: datetime = datetime.now()
    log_service = os.environ.get("LOG_SERVICE")
    if not isinstance(log_service, str):
        warning("Log service not set, export 'LOG_SERVICE'.")
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
    info(msg)
    timestamp: datetime = datetime.now()
    log_service = os.environ.get("LOG_SERVICE")
    if not isinstance(log_service, str):
        warning("Log service not set, export 'LOG_SERVICE'.")
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
