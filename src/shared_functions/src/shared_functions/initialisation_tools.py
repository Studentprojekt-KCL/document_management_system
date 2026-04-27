"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from os import environ
from shared_functions.dmis_logger import dms_error


def read_port(env_variable: str, allowed_ports: tuple[int, ...] = tuple(range(0, 65536))) -> int:
    """Read port number from local env variable.

    Args:
        env_variable: Name of env variable.
    """
    port = environ.get(env_variable)
    if port is None or not isinstance(port, str) or not port.isdigit():
        dms_error(f"Export {env_variable} in environment (must be a digit).")
    int_port = int(port)  # type: ignore
    if int_port not in allowed_ports:
        dms_error(f"Port number set in {env_variable} ({int_port}) is not allowed, must be in {allowed_ports}")
    return int_port


def read_env_variable(env_variable: str, required: bool = True) -> str | None:
    """Read env_variable from local environement.

    Args:
        env_varaible: Name of env variable.
    """
    variable = environ.get(env_variable)
    if (not variable or not isinstance(variable, str)) and required:
        dms_error(f"{env_variable} must be set in local environement.")
    return variable  # type: ignore
