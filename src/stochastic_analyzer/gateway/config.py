"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from os import environ
import argparse

from dmis_logger import dms_error


class ServiceConfig:
    """External service connection configuration.

    Attributes:
        tei_url: URL for the TEI reranker container.
        classifier_url: URL for the TEI classifier container.
        ministral_url: URL for the Ministral LLM container.
        ministral_model: model identifier for Ministral.
        connector_url: connector url
    """

    tei_url: str
    classifier_url: str
    ministral_url: str
    ministral_model: str
    connector_url: str


class APIConfiguration:
    """API Configuration.

    Attributes:
        BIND: which address to bind to.
        port: port to bind on.
        log_level: log level.
        device: compute device identifier.
        services: external service configuration.
    """

    bind: str
    port: int
    log_level: str
    device: str
    services: ServiceConfig
    MAX_PORT: int = 65536

    def __init__(self) -> None:
        self._load_log_level()
        self._load_bind()
        self._load_port()
        self._load_service_config()

    def _load_log_level(self) -> None:
        """Load log level from arguments."""
        parser = argparse.ArgumentParser()
        _ = parser.add_argument("--dev", action="store_true")
        args = parser.parse_args()

        if args.dev:
            self.log_level = "debug"
        else:
            self.log_level = "info"

    def _load_bind(self) -> None:
        """Load bind configuration."""
        bind: str | None = environ.get("BIND")

        if bind is None:
            dms_error("BIND is not defined.")
            return

        self.bind = bind

    def _load_port(self) -> None:
        """Load and verify port environment variable."""
        # Note: This will be migrated to a shared solution
        port: str | None = environ.get("PORT")

        if port is None:
            dms_error("PORT is not defined.")
            return

        if not port.isdigit():
            dms_error("PORT is expected to be an integer.")
            return

        if int(port) < 0 or int(port) >= self.MAX_PORT:
            dms_error(f"PORT should be between 0 and {self.MAX_PORT}.")
            return

        self.port = int(port)

    def _load_service_config(self) -> None:
        """Load external service configuration."""
        self.device = environ.get("DEVICE", "external")
        self.services = ServiceConfig()

        tei_url: str | None = environ.get("TEI_URL")
        classifier_url: str | None = environ.get("CLASSIFIER_URL")
        ministral_url: str | None = environ.get("MINISTRAL_URL")
        ministral_model: str | None = environ.get("MINISTRAL_MODEL")
        address: str | None = environ.get("CONNECTOR_ADDRESS")

        if tei_url is None:
            dms_error("TEI_URL is not defined.")
            return

        if classifier_url is None:
            dms_error("CLASSIFIER_URL is not defined.")
            return

        if ministral_url is None:
            dms_error("MINISTRAL_URL is not defined.")
            return

        if ministral_model is None:
            dms_error("MINISTRAL_MODEL is not defined.")
            return

        if address is None:
            dms_error("CONNECTOR_ADDRESS is not defined.")
            return

        self.services.tei_url = tei_url
        self.services.classifier_url = classifier_url
        self.services.ministral_url = ministral_url
        self.services.ministral_model = ministral_model
        self.services.connector_url = address
