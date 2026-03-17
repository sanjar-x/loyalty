"""Application settings loaded from environment variables.

All configuration values are validated at startup via Pydantic Settings.
A cached singleton is exposed as ``settings`` for convenient import
throughout the codebase.
"""

import uuid
from functools import lru_cache
from typing import Annotated, Any, Literal

from pydantic import BeforeValidator, computed_field
from pydantic.types import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


def parse_cors(v: Any) -> list[str] | str:
    """Parse the CORS_ORIGINS value from the environment.

    Accepts either a comma-separated string or a JSON list.

    Args:
        v: The raw value from the environment variable.

    Returns:
        A list of allowed origin strings, or the original list if
        already provided as one.

    Raises:
        ValueError: If the value is neither a string nor a list.
    """
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    """Central configuration object for the application.

    Values are populated from environment variables (or an ``.env`` file)
    and validated by Pydantic on construction.  Computed fields derive
    connection URLs from individual host/port/credentials settings.
    """

    PROJECT_NAME: str = "Enterprise API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["dev", "test", "prod"] = "dev"
    DEBUG: bool = False

    API_V1_STR: str = "/api/v1"
    API_V2_STR: str = "/api/v2"
    ALGORITHM: str = "HS256"

    SECRET_KEY: SecretStr
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15

    # IAM RBAC settings
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    SESSION_PERMISSIONS_CACHE_TTL: int = 300
    MAX_ACTIVE_SESSIONS_PER_IDENTITY: int = 5

    CORS_ORIGINS: Annotated[list[str] | str, BeforeValidator(parse_cors)] = []

    SYSTEM_USER_ID: uuid.UUID = uuid.UUID(int=0)

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

    REDISHOST: str
    REDISPORT: int
    REDISUSER: str = "default"
    REDISPASSWORD: SecretStr | None = None
    REDISDATABASE: int = 0

    S3_ENDPOINT_URL: str
    S3_ACCESS_KEY: SecretStr
    S3_SECRET_KEY: SecretStr
    S3_REGION: str
    S3_BUCKET_NAME: str
    S3_PUBLIC_BASE_URL: str

    RABBITMQ_URL: str

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
    """Return the cached application settings singleton.

    Returns:
        The validated ``Settings`` instance.
    """
    return Settings()  # ty:ignore[missing-argument]


settings: Settings = get_settings()
