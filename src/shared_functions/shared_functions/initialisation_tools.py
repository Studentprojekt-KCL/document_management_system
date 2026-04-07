from os import environ
from dmis_logger import dms_error

def read_port(env_variable: str, allowed_ports: tuple = tuple(range(0, 65536))):
    """Read port number from local env variable.

    Args:
        env_variable: Name of env variable.
    """
    port = environ.get(env_variable)
    if port is None or not port.isdigit():
        dms_error(f"Export {env_variable} in environment (must be a digit).")
    int_port = int(port)
    if int_port not in allowed_ports:
        dms_error(f"Port number set in {env_variable} ({int_port}) is not allowed, must be in {allowed_ports}")
    return int_port

def read_env_variable(env_variable: str):
    """Read host from local environement variable.

    Args:
        env_varaible: Name of env variable.
    """
    host = environ.get(env_variable)
    if host is None:
        dms_error(f"{env_variable} must be set in local environement.")
    return host
