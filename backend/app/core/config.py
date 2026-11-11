from pathlib import Path
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # General
    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "DASMO Office - YouTube Shorts Factory"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "temporary_secret_key_change_in_production"

    # CORS
    BACKEND_CORS_ORIGINS: List[Union[str, AnyHttpUrl]] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    # Database: PostgreSQL
    POSTGRES_USER: str = "dasmo_user"
    POSTGRES_PASSWORD: str = "dasmo_secure_password"
    POSTGRES_HOST: str = "dasmo-db"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "dasmo_db"
    DATABASE_URL: str = "postgresql+asyncpg://dasmo_user:dasmo_secure_password@dasmo-db:5432/dasmo_db"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://dasmo_user:dasmo_secure_password@dasmo-db:5432/dasmo_db"

    # Redis & Celery
    REDIS_HOST: str = "dasmo-redis"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://dasmo-redis:6379/0"
    CELERY_BROKER_URL: str = "redis://dasmo-redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://dasmo-redis:6379/0"

    # Media Storage
    MEDIA_DIR: Path = Path("/media")

    # Voice TTS Configuration
    DEFAULT_TTS_VOICE: str = "es-MX-JorgeNeural"
    DEFAULT_TTS_RATE: str = "+10%"

    # AI Services Keys
    GEMINI_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = "21m00Tcm4TlvDq8ikWAM"
    OPENAI_API_KEY: str = ""
    REPLICATE_API_TOKEN: str = ""

    # YouTube API
    YOUTUBE_CLIENT_ID: str = ""
    YOUTUBE_CLIENT_SECRET: str = ""
    YOUTUBE_REFRESH_TOKEN: str = ""

    # Pixabay API
    PIXABAY_API_KEY: str = ""

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)


settings = Settings()
