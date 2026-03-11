"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

import logging
import argparse
from os import environ
from dmis_logger import dms_error


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
        self._load_port()
        self._load_host()
        self._load_log_level()

    def _load_port(self) -> None:
        """Load and verify port environment variable."""

        port = environ.get("SE_API_PORT", None)

        if port is None:
            self.port = 8080
        elif not port.isdigit():
            dms_error("Port is expected to be an integer.")
        elif int(port) < 0 or int(port) > 65536:
            dms_error("Port should be between 0 and 65536.")
        else:
            self.port = int(port)

    def _load_host(self) -> None:
        """Load host configuration."""

        self.host = "0.0.0.0"

    def _load_log_level(self) -> None:
        """Load log level from arguments."""

        logging.basicConfig()

        parser = argparse.ArgumentParser()
        _ = parser.add_argument("--dev", action="store_true")
        args = parser.parse_args()

        if args.dev:
            self.log_level = "debug"
            logging.getLogger().setLevel(logging.DEBUG)
        else:
            logging.getLogger().setLevel(logging.INFO)
            self.log_level = "info"
