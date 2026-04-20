"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import argparse
from os import environ

from shared_functions.dmis_logger import dms_error
from shared_functions.initialisation_tools import read_env_variable


class VectorConfig:
    """Vector search service configuration.

    Attributes:
        embedding_url: URL for the TEI embedding container.
        qdrant_url: URL for the Qdrant vector database.
        batch_size: Number of documents per batch.
        max_chars: Maximum characters per documents sent for embedding.
    """

    embedding_url: str
    qdrant_url: str
    batch_size: int
    max_chars: int


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
        classifier_url: URL for the TEI classifier container.
        connector_url: connector url.
        escalation_threshold: score gap threshold for classification escalation.
        ministral: Ministral LLM configuration.
        vector: vector search service configuration.
    """

    classifier_url: str
    connector_url: str
    escalation_threshold: float
    any_llm: MinistralConfig
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
        bind: str | None = environ.get("STOCHAN_BIND_ADDR")

        if bind is None:
            dms_error("BIND is not defined.")
            return

        self.bind = bind

    def _load_port(self) -> None:
        """Load and verify port environment variable."""
        # Note: This will be migrated to a shared solution
        port: str | None = environ.get("STOCHAN_BIND_PORT")

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
        self.services.any_llm = MinistralConfig()

        required = {
            "STOCHAN_CLASSIFIER_URL": read_env_variable("STOCHAN_CLASSIFIER_URL"),
            "STOCHAN_LLM_URL": read_env_variable("STOCHAN_LLM_URL"),
            "STOCHAN_LLM_MODEL": read_env_variable("STOCHAN_LLM_MODEL"),
            "STOCHAN_LLM_TIMEOUT": read_env_variable("STOCHAN_LLM_TIMEOUT"),
            "STOCHAN_CONNECTOR_ADDRESS": read_env_variable("STOCHAN_CONNECTOR_ADDRESS"),
            "STOCHAN_ESCALATION_THRESHOLD": read_env_variable("STOCHAN_ESCALATION_THRESHOLD"),
            "STOCHAN_EMBEDDING_URL": read_env_variable("STOCHAN_EMBEDDING_URL"),
            "STOCHAN_QDRANT_URL": read_env_variable("STOCHAN_QDRANT_URL"),
        }

        for name, value in required.items():
            if value is None:
                dms_error(f"{name} is not defined.")
                return

        self.services.classifier_url = required["STOCHAN_CLASSIFIER_URL"]
        self.services.connector_url = required["STOCHAN_CONNECTOR_ADDRESS"]
        self.services.escalation_threshold = float(required["STOCHAN_ESCALATION_THRESHOLD"])
        self.services.any_llm.url = required["STOCHAN_LLM_URL"]
        self.services.any_llm.model = required["STOCHAN_LLM_MODEL"]
        self.services.any_llm.timeout = int(required["STOCHAN_LLM_TIMEOUT"])
        self.services.vector.embedding_url = required["STOCHAN_EMBEDDING_URL"]
        self.services.vector.qdrant_url = required["STOCHAN_QDRANT_URL"]
        self.services.vector.batch_size = int(environ.get("INDEX_BATCH_SIZE", "8"))
        self.services.vector.max_chars = int(environ.get("STOCHAN_INDEX_MAX_CHARS", "2000"))
