"""Application settings loaded from environment variables.

All configuration values are validated at startup via Pydantic Settings.
A cached singleton is exposed as ``settings`` for convenient import
throughout the codebase.
"""

from functools import lru_cache
from typing import Annotated, Any, Literal

from pydantic import BeforeValidator, computed_field
from pydantic.types import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


def parse_cors(v: Any) -> list[str] | str:
    """Parse the CORS_ORIGINS value from the environment."""
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    """Central configuration object for the Image Backend microservice."""

    PROJECT_NAME: str = "Image Backend"
    VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["dev", "test", "prod"] = "dev"
    DEBUG: bool = False

    API_V1_STR: str = "/api/v1"

    CORS_ORIGINS: Annotated[list[str] | str, BeforeValidator(parse_cors)] = []

    # -- Database ------------------------------------------------------------
    PGHOST: str
    PGPORT: int
    PGUSER: str
    PGPASSWORD: SecretStr
    PGDATABASE: str

    @computed_field
    @property
    def database_url(self) -> URL:
        """Build an async PostgreSQL connection URL from individual settings."""
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.PGUSER,
            password=self.PGPASSWORD.get_secret_value(),
            host=self.PGHOST,
            port=self.PGPORT,
            database=self.PGDATABASE,
        )

    # -- Redis ---------------------------------------------------------------
    REDISHOST: str
    REDISPORT: int
    REDISUSER: str = "default"
    REDISPASSWORD: SecretStr | None = None
    REDISDATABASE: int = 0

    # -- S3 Storage ----------------------------------------------------------
    S3_ENDPOINT_URL: str
    S3_ACCESS_KEY: SecretStr
    S3_SECRET_KEY: SecretStr
    S3_REGION: str
    S3_BUCKET_NAME: str
    S3_PUBLIC_BASE_URL: str

    # -- RabbitMQ ------------------------------------------------------------
    RABBITMQ_PRIVATE_URL: str

    # -- Service Auth --------------------------------------------------------
    INTERNAL_API_KEY: SecretStr = SecretStr("")

    # -- Processing ----------------------------------------------------------
    SSE_TIMEOUT: int = 120
    SSE_HEARTBEAT: int = 15
    PROCESSING_TIMEOUT: int = 300
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50 MB
    PRESIGNED_URL_TTL: int = 300

    @computed_field
    @property
    def redis_url(self) -> str:
        """Build a Redis connection URL from individual settings."""
        credentials = ""
        if self.REDISPASSWORD:
            credentials = f"{self.REDISUSER}:{self.REDISPASSWORD.get_secret_value()}@"

        return f"redis://{credentials}{self.REDISHOST}:{self.REDISPORT}/{self.REDISDATABASE}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()  # ty:ignore[missing-argument]


settings: Settings = get_settings()
