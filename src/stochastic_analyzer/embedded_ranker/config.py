"""Base configs for the model."""

import torch
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Set up desired model."""

    MODEL_NAME: str

    DEVICE: str = "cuda" if torch.cuda.is_available() else "cpu"
    API_TITLE: str = "DMS Re-Ranker"
    API_VERSION: str = "1.0.0"

    HOST: str
    PORT: int

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
