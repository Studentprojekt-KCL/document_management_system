"""Base configs for the model."""

from os import environ
import argparse

from dmis_logger import dms_error

class APIConfiguration:
    """API Configuration.
 
    Attributes:
        host: which address to bind to.
        port: port to host on.
        log_level: log level.
        device: compute device identifier.
        tei_url: URL for the TEI reranker container.
        classifier_url: URL for the TEI classifier container.
        ministral_url: URL for the Ministral LLM container.
        ministral_model: model identifier for Ministral.
    """

    host: str
    port: int
    log_level: str
    device: str
    tei_url: str
    classifier_url: str
    ministral_url: str
    ministral_model: str

    def __init__(self) -> None:
        self._load_log_level()
        self._load_host()
        self._load_port()
        self._load_service_urls()
 
    def _load_log_level(self) -> None:
        """Load log level from arguments."""
        parser = argparse.ArgumentParser()
        _ = parser.add_argument("--dev", action="store_true")
        args = parser.parse_args()
 
        if args.dev:
            self.log_level = "debug"
        else:
            self.log_level = "info"
 
    def _load_host(self) -> None:
        """Load host configuration."""
        host: str | None = environ.get("HOST")
 
        if host is None:
            dms_error("HOST is not defined.")
            return
 
        self.host = host
 
    def _load_port(self) -> None:
        """Load and verify port environment variable."""
        port: str | None = environ.get("PORT")
 
        if port is None:
            dms_error("PORT is not defined.")
            return
 
        if not port.isdigit():
            dms_error("PORT is expected to be an integer.")
            return
 
        if int(port) < 0 or int(port) >= 65536:
            dms_error("PORT should be between 0 and 65536.")
            return
 
        self.port = int(port)
 
    def _load_service_urls(self) -> None:
        """Load external service configuration."""
        self.device = environ.get("DEVICE", "external")
 
        tei_url: str | None = environ.get("TEI_URL")
        classifier_url: str | None = environ.get("CLASSIFIER_URL")
        ministral_url: str | None = environ.get("MINISTRAL_URL")
        ministral_model: str | None = environ.get("MINISTRAL_MODEL")
 
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
 
        self.tei_url = tei_url
        self.classifier_url = classifier_url
        self.ministral_url = ministral_url
        self.ministral_model = ministral_model
 