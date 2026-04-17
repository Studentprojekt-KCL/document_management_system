"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import argparse
from os import environ

from dmis_logger import dms_error
from initialisation_tools import read_env_variable


class VectorConfig:
    """Vector search service configuration.

    Attributes:
        embedding_url: URL for the TEI embedding container.
        qdrant_url: URL for the Qdrant vector database.
    """

    embedding_url: str
    qdrant_url: str


class MinistralConfig:
    """Ministral LLM configuration.

    Attributes:
        url: URL for the Ministral LLM container.
        model: model identifier for Ministral.
        timeout: timeout for Ministral requests.
    """

    url: str
    model: str
    timeout: int


class ServiceConfig:
    """External service connection configuration.

    Attributes:
        tei_url: URL for the TEI reranker container.
        classifier_url: URL for the TEI classifier container.
        connector_url: connector url.
        escalation_threshold: score gap threshold for classification escalation.
        ministral: Ministral LLM configuration.
        vector: vector search service configuration.
    """

    tei_url: str
    classifier_url: str
    connector_url: str
    escalation_threshold: float
    ministral: MinistralConfig
    vector: VectorConfig


class APIConfiguration:
    """API Configuration.

    Attributes:
        bind: which address to bind to.
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
        self.services.vector = VectorConfig()
        self.services.ministral = MinistralConfig()

        required = {
            "TEI_URL": read_env_variable("TEI_URL"),
            "CLASSIFIER_URL": read_env_variable("CLASSIFIER_URL"),
            "MINISTRAL_URL": read_env_variable("MINISTRAL_URL"),
            "MINISTRAL_MODEL": read_env_variable("MINISTRAL_MODEL"),
            "MINISTRAL_TIMEOUT": read_env_variable("MINISTRAL_TIMEOUT"),
            "CONNECTOR_ADDRESS": read_env_variable("CONNECTOR_ADDRESS"),
            "ESCALATION_THRESHOLD": read_env_variable("ESCALATION_THRESHOLD"),
            "EMBEDDING_URL": read_env_variable("EMBEDDING_URL"),
            "QDRANT_URL": read_env_variable("QDRANT_URL"),
        }

        for name, value in required.items():
            if value is None:
                dms_error(f"{name} is not defined.")
                return

        self.services.tei_url = required["TEI_URL"]
        self.services.classifier_url = required["CLASSIFIER_URL"]
        self.services.connector_url = required["CONNECTOR_ADDRESS"]
        self.services.escalation_threshold = float(required["ESCALATION_THRESHOLD"])
        self.services.ministral.url = required["MINISTRAL_URL"]
        self.services.ministral.model = required["MINISTRAL_MODEL"]
        self.services.ministral.timeout = int(required["MINISTRAL_TIMEOUT"])
        self.services.vector.embedding_url = required["EMBEDDING_URL"]
        self.services.vector.qdrant_url = required["QDRANT_URL"]
