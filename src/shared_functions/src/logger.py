"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import os
from logging import error, warning, info
from datetime import datetime
from typing import Any

import requests


def dms_error(msg: str, *_: Any, **__: Any) -> None:
    """Logging service which will handeling errors.

    Args:
    ----
        msg: Error message.
    """
    error(msg)
    timestamp = int(datetime.now().timestamp())
    log_service = os.environ.get("LOG_SERVICE")
    if not isinstance(log_service, str):
        error("Log service not set, export 'LOG_SERVICE'.")
        return
    requests.put(log_service, {"log": {"err": msg}, "timespamp": timestamp}, timeout=60)


def dms_warning(msg: str, *_: Any, **__: Any) -> None:
    """Logging service which will handeling warnings.

    Args:
    ----
        msg: Warning message.
    """
    warning(msg)
    timestamp = int(datetime.now().timestamp())
    log_service = os.environ.get("LOG_SERVICE")
    if not isinstance(log_service, str):
        error("Log service not set, export 'LOG_SERVICE'.")
        return
    requests.put(
        log_service,
        {"log": {"warning": msg}, "timestamp": timestamp},
        timeout=60,
    )


def dms_info(msg: str, *_: Any, **__: Any) -> None:
    """Logging service which will handeling info messages.

    Args:
    ----
        msg: Info message.
    """
    info(msg)
    timestamp = int(datetime.now().timestamp())
    log_service = os.environ.get("LOG_SERVICE")
    if not isinstance(log_service, str):
        error("Log service not set, export 'LOG_SERVICE'.")
        return
    requests.put(log_service, {"log": {"info": msg}, "timestamp": timestamp}, timeout=60)
