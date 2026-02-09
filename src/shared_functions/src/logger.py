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
    requests.put(
        os.environ.get("LOG_ENDPOINT"), {"log": {"err": msg}, "timespamp": timestamp}, timeout=60
    )


def dms_warning(msg: str, *_: Any, **__: Any) -> None:
    """Logging service which will handeling warnings.

    Args:
    ----
        msg: Warning message.
    """
    warning(msg)
    timestamp = int(datetime.now().timestamp())
    requests.put(
        os.environ.get("LOG_ENDPOINT"),
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
    requests.put(
        os.environ.get("LOG_ENDPOINT"), {"log": {"info": msg}, "timestamp": timestamp}, timeout=60
    )
