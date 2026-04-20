"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from os import environ
import argparse
from dataclasses import dataclass

from dmis_logger import dms_error
from initialisation_tools import read_env_variable


@dataclass
class LanguageConfig:
    """Language detection configuration.

    Attributes:
        sample_size: number of characters to sample from the document for language detection.
        swedish_char_threshold: number of Swedish characters to trigger Swedish detection.
    """

    sample_size: int
    swedish_char_threshold: int


@dataclass
class MinistralConfig:
    """Ministral LLM connection configuration.

    Attributes:
        url: URL for the Ministral LLM container.
        model: model identifier for Ministral.
        timeout: request timeout in seconds.
    """

    url: str
    model: str
    timeout: int


class ServiceConfig:
    """External service connection configuration.

    Attributes:
        tei_url: URL for the TEI reranker container.
        classifier_url: URL for the TEI classifier container.
        ministral: Ministral LLM configuration.
        connector_url: connector url.
        escalation_threshold: score gap threshold for security-first classification escalation.
        language: language detection configuration.
    """

    tei_url: str
    classifier_url: str
    ministral: MinistralConfig
    connector_url: str
    escalation_threshold: float
    language: LanguageConfig


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

    def _validate_required_env_vars(self, required_vars: dict) -> bool:
        """Validate required environment variables.

        Args:
            required_vars: Dictionary mapping variable names to their values

        Returns:
            True if all required variables are present, False otherwise
        """
        for var_name, var_value in required_vars.items():
            if var_value is None:
                dms_error(f"{var_name} is not defined.")
                return False
        return True

    def _load_service_config(self) -> None:
        """Load external service configuration."""
        self.device = environ.get("DEVICE", "external")
        self.services = ServiceConfig()

        # Load all environment variables
        tei_url: str = read_env_variable("TEI_URL")
        classifier_url: str = read_env_variable("CLASSIFIER_URL")
        ministral_url: str = read_env_variable("MINISTRAL_URL")
        ministral_model: str = read_env_variable("MINISTRAL_MODEL")
        ministral_timeout: str = read_env_variable("MINISTRAL_TIMEOUT")
        address: str = read_env_variable("CONNECTOR_ADDRESS")
        escalation_threshold: str = read_env_variable("ESCALATION_THRESHOLD")
        sample_size: str = read_env_variable("SAMPLE_SIZE")
        swedish_char_threshold: str = read_env_variable("SWEDISH_CHAR_THRESHOLD")

        # Validate required variables
        required_vars = {
            "TEI_URL": tei_url,
            "CLASSIFIER_URL": classifier_url,
            "MINISTRAL_URL": ministral_url,
            "MINISTRAL_MODEL": ministral_model,
            "CONNECTOR_ADDRESS": address,
            "ESCALATION_THRESHOLD": escalation_threshold,
            "SAMPLE_SIZE": sample_size,
            "SWEDISH_CHAR_THRESHOLD": swedish_char_threshold,
        }

        if not self._validate_required_env_vars(required_vars):
            return

        # Assign service configurations
        self.services.tei_url = tei_url
        self.services.classifier_url = classifier_url
        self.services.ministral = MinistralConfig(
            url=ministral_url,
            model=ministral_model,
            timeout=int(ministral_timeout),
        )
        self.services.connector_url = address
        self.services.escalation_threshold = float(escalation_threshold)
        self.services.language = LanguageConfig(
            sample_size=int(sample_size),
            swedish_char_threshold=int(swedish_char_threshold),
        )
