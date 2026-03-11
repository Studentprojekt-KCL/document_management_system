"""Base configs for the model."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Set up desired model."""

    MODEL_NAME: str
    DEVICE: str = "external"
    TEI_URL : str
    MINISTRAL_URL: str
    MINISTRAL_MODEL: str
    QWEN_URL: str
    QWEN_MODEL: str
    API_TITLE: str = "stochastic analyzer gateway"
    API_VERSION: str = "1.0.0"
    HOST: str
    PORT: int

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()