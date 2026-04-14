"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from os import environ
import argparse

from dmis_logger import dms_error


class LanguageConfig:
    """Language detection tuning parameters for Swedish heuristic."""

    min_doc_length: int
    sample_size: int
    swedish_char_threshold: int
    swedish_stopword_threshold: int


class MinistralConfig:
    """Ministral LLM connection and generation configuration.

    Attributes:
        url: URL for the Ministral LLM container.
        model: model identifier for Ministral.
        max_tokens: max tokens for Ministral LLM response.
        temperature: sampling temperature for Ministral LLM.
        timeout: HTTP timeout in seconds for Ministral requests.
    """

    url: str
    model: str
    max_tokens: int
    temperature: float
    timeout: int


class ServiceConfig:
    """External service connection configuration.

    Attributes:
        tei_url: URL for the TEI reranker container.
        classifier_url: URL for the TEI classifier container.
        connector_url: connector url.
        escalation_threshold: score gap threshold for security-first classification escalation.
        ministral: Ministral LLM configuration.
        language: language detection configuration.
    """

    tei_url: str
    classifier_url: str
    connector_url: str
    escalation_threshold: float
    ministral: MinistralConfig
    language: LanguageConfig


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
        self.log_level = "debug" if args.dev else "info"

    def _load_bind(self) -> None:
        """Load bind configuration."""
        bind: str | None = environ.get("BIND")
        if bind is None:
            dms_error("BIND is not defined.")
            return
        self.bind = bind

    def _load_port(self) -> None:
        """Load and verify port environment variable."""
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
        if not self._load_urls():
            return
        if not self._load_llm_config():
            return
        self._load_language_config()

    def _load_urls(self) -> bool:
        """Validate and assign URL and string service config. Returns False on failure."""
        tei_url = environ.get("TEI_URL")
        classifier_url = environ.get("CLASSIFIER_URL")
        ministral_url = environ.get("MINISTRAL_URL")
        ministral_model = environ.get("MINISTRAL_MODEL")
        address = environ.get("CONNECTOR_ADDRESS")

        if tei_url is None:
            dms_error("TEI_URL is not defined.")
            return False
        if classifier_url is None:
            dms_error("CLASSIFIER_URL is not defined.")
            return False
        if ministral_url is None:
            dms_error("MINISTRAL_URL is not defined.")
            return False
        if ministral_model is None:
            dms_error("MINISTRAL_MODEL is not defined.")
            return False
        if address is None:
            dms_error("CONNECTOR_ADDRESS is not defined.")
            return False

        self.services.tei_url = tei_url
        self.services.classifier_url = classifier_url
        self.services.connector_url = address
        self.services.ministral = MinistralConfig()
        self.services.ministral.url = ministral_url
        self.services.ministral.model = ministral_model
        return True

    def _load_llm_config(self) -> bool:
        """Validate and assign numeric LLM config. Returns False on failure."""
        escalation_threshold = environ.get("ESCALATION_THRESHOLD", "0.02")
        ministral_max_tokens = environ.get("MINISTRAL_MAX_TOKENS", "400")
        ministral_temperature = environ.get("MINISTRAL_TEMPERATURE", "0.3")
        ministral_timeout = environ.get("MINISTRAL_TIMEOUT", "120")

        try:
            escalation_threshold_f = float(escalation_threshold)
        except ValueError:
            dms_error("ESCALATION_THRESHOLD must be a valid float.")
            return False

        if not 0.0 <= escalation_threshold_f <= 1.0:
            dms_error("ESCALATION_THRESHOLD must be between 0.0 and 1.0.")
            return False

        try:
            ministral_temperature_f = float(ministral_temperature)
        except ValueError:
            dms_error("MINISTRAL_TEMPERATURE must be a valid float.")
            return False

        if not ministral_max_tokens.isdigit():
            dms_error("MINISTRAL_MAX_TOKENS must be a valid positive integer.")
            return False

        if not ministral_timeout.isdigit():
            dms_error("MINISTRAL_TIMEOUT must be a valid positive integer.")
            return False

        self.services.escalation_threshold = escalation_threshold_f
        self.services.ministral.max_tokens = int(ministral_max_tokens)
        self.services.ministral.temperature = ministral_temperature_f
        self.services.ministral.timeout = int(ministral_timeout)
        return True

    def _load_language_config(self) -> None:
        """Validate and assign language detection config."""
        min_doc_length = environ.get("MIN_DOC_LENGTH", "50")
        sample_size = environ.get("SAMPLE_SIZE", "5000")
        swedish_char_threshold = environ.get("SWEDISH_CHAR_THRESHOLD", "2")
        swedish_stopword_threshold = environ.get("SWEDISH_STOPWORD_THRESHOLD", "3")

        if not min_doc_length.isdigit():
            dms_error("MIN_DOC_LENGTH must be a valid positive integer.")
            return
        if not sample_size.isdigit():
            dms_error("SAMPLE_SIZE must be a valid positive integer.")
            return
        if not swedish_char_threshold.isdigit():
            dms_error("SWEDISH_CHAR_THRESHOLD must be a valid positive integer.")
            return
        if not swedish_stopword_threshold.isdigit():
            dms_error("SWEDISH_STOPWORD_THRESHOLD must be a valid positive integer.")
            return

        self.services.language = LanguageConfig()
        self.services.language.min_doc_length = int(min_doc_length)
        self.services.language.sample_size = int(sample_size)
        self.services.language.swedish_char_threshold = int(swedish_char_threshold)
        self.services.language.swedish_stopword_threshold = int(swedish_stopword_threshold)