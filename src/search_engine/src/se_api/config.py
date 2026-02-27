"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from os import environ
import argparse

# from logger import dms_error  # pylint: disable=no-name-in-module


class APIConfiguration:
    """API Configuration

    Attributes:
        port: port to host on.
        host: which address to bind to.
        log_level: log level.
    """

    port: int
    host: str
    log_level: str

    def __init__(self) -> None:
        try:
            self._load_port()
            self._load_host()
            self._load_log_level()
        except RuntimeError as e:
            dms_error(repr(e))
            self.port = 0
            self.host = ""
            self.log_level = ""

    def _load_port(self) -> None:
        """Load and verify port environment variable."""

        temp: str | None = environ.get("SE_API_PORT", None)
        port: int = 0

        if temp is None:
            port = 8080
        else:
            try:
                port = int(temp)
            except ValueError as e:
                raise e

        if port < 0 or port > 65536:
            raise RuntimeError(f"SE_API_PORT expected value to be between 0 and 65536, but is {port}")

        self.port = port

    def _load_host(self) -> None:
        """Load host configuration."""

        self.host = "0.0.0.0"

    def _load_log_level(self) -> None:
        """Load log level from arguments."""

        parser = argparse.ArgumentParser()
        _ = parser.add_argument("--dev", action="store_true")
        args = parser.parse_args()

        if args.dev:
            self.log_level = "debug"
        else:
            self.log_level = ""
