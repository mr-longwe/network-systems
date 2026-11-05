"""Application configuration management using Pydantic Settings."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the Edge Video Monitoring System."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Server Settings
    EDGE_HOST: str = "0.0.0.0"
    EDGE_PORT: int = 8000
    EDGE_DEBUG: bool = False
    APP_NAME: str = "Local Edge Video Monitoring System"
    APP_VERSION: str = "1.0.0"

    # Application Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = Path("data")
    RECORDINGS_DIR: Path = Path("data/recordings")
    DATABASE_PATH: Path = Path("data/edge_system.db")

    # Video Ingestion & Processing Defaults
    DEFAULT_FPS: int = 10
    DEFAULT_FRAME_WIDTH: int = 640
    DEFAULT_FRAME_HEIGHT: int = 480
    MOTION_THRESHOLD: int = 25
    MOTION_MIN_AREA: int = 500
    POST_MOTION_RECORD_SECONDS: int = 5

    # Security Settings
    AUTH_ENABLED: bool = False
    SECRET_KEY: str = "development-secret-key-change-in-production"
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"

    def ensure_directories(self) -> None:
        """Create required runtime directories if they do not exist."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()

