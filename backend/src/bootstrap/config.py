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
    SESSION_IDLE_TIMEOUT_MINUTES: int = 30
    SESSION_ABSOLUTE_LIFETIME_HOURS: int = 24
    TELEGRAM_SESSION_IDLE_TIMEOUT_MINUTES: int = 1440
    TELEGRAM_SESSION_ABSOLUTE_LIFETIME_HOURS: int = 168

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

    # ImageBackend (server-to-server)
    IMAGE_BACKEND_URL: str = "http://localhost:8080"
    IMAGE_BACKEND_API_KEY: SecretStr = SecretStr("")

    INTERNAL_WEBHOOK_SECRET: SecretStr = SecretStr("")

    RABBITMQ_PRIVATE_URL: str

    # -- Telegram Bot --------------------------------------------------------
    BOT_TOKEN: SecretStr
    BOT_ADMIN_IDS: list[int] = []
    BOT_WEBHOOK_URL: str = ""
    BOT_WEBHOOK_SECRET: str = ""
    THROTTLE_RATE: float = 0.5
    FSM_STATE_TTL: int | None = None
    FSM_DATA_TTL: int | None = None

    TELEGRAM_INIT_DATA_MAX_AGE: int = 300
    TELEGRAM_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # -- S3 / MinIO (image module — formerly image_backend microservice) -----
    # Empty defaults so local dev / tests boot without S3 credentials. The
    # image module providers raise at request time only if endpoints are
    # actually invoked without proper config (REC-020 + image-backend
    # consolidation per CEO directive 2026-05-08).
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY: SecretStr = SecretStr("")
    S3_SECRET_KEY: SecretStr = SecretStr("")
    S3_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = ""
    S3_PUBLIC_BASE_URL: str = ""
    # Media processing knobs (image module)
    MEDIA_MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50 MB
    MEDIA_PRESIGNED_URL_TTL: int = 300
    MEDIA_SSE_TIMEOUT: int = 120

    # -- CDEK (logistics provider) -------------------------------------------
    # Credentials are seeded into ``provider_accounts`` by ``seed/logistics``;
    # at runtime the factory reads them from the DB row, not from env.
    # Empty defaults let the seed step skip CDEK on environments where
    # the keys aren't configured yet.
    CDEK_ACCOUNT: SecretStr = SecretStr("")
    CDEK_SECURE_PASSWORD: SecretStr = SecretStr("")
    CDEK_TEST_ACCOUNT: SecretStr = SecretStr("")
    CDEK_TEST_SECURE_PASSWORD: SecretStr = SecretStr("")

    # -- Yandex Delivery (logistics provider) --------------------------------
    # Same pattern as CDEK: seeded into ``provider_accounts`` by
    # ``seed/logistics``; at runtime the factory reads them from the DB.
    # ``PLATFORM_STATION_ID`` is the default source warehouse — used as a
    # fallback when the request's ``origin.metadata`` does not carry one.
    YANDEX_DELIVERY_OAUTH_TOKEN: SecretStr = SecretStr("")
    YANDEX_DELIVERY_PLATFORM_STATION_ID: str = ""
    YANDEX_DELIVERY_TEST_OAUTH_TOKEN: SecretStr = SecretStr("")
    YANDEX_DELIVERY_TEST_PLATFORM_STATION_ID: str = ""

    # -- Payment ------------------------------------------------------------
    # ``fake`` is a deterministic in-process stub used outside ``prod``.
    # Real PSP adapters (yookassa/sbp/tinkoff) are added behind the same
    # ``IPaymentProvider`` port without touching application code.
    PAYMENT_PROVIDER: Literal["fake", "yookassa", "sbp", "tinkoff"] = "fake"
    PAYMENT_SIMULATION_ENABLED: bool = True
    PAYMENT_AUTH_TTL_DAYS: int = 7  # Visa-стандарт hold

    # -- DobroPost (cross-border) ------------------------------------------
    DOBROPOST_BASE_URL: str = "https://api.dobropost.com"
    DOBROPOST_EMAIL: SecretStr = SecretStr("")
    DOBROPOST_PASSWORD: SecretStr = SecretStr("")
    DOBROPOST_DEFAULT_TARIFF_ID: int = 1
    DOBROPOST_TIMEOUT_SECONDS: float = 30.0
    DOBROPOST_TOKEN_REFRESH_BEFORE_SECONDS: int = 3600  # refresh 1h before exp
    # Webhook authentication: random secret embedded in URL path
    # ``/api/v1/orders/webhooks/dobropost/{token}``.
    DOBROPOST_WEBHOOK_TOKEN: SecretStr = SecretStr("")
    DOBROPOST_ALLOWED_IPS: list[str] = []
    DOBROPOST_USE_STUB: bool = True  # Flip to false in prod once creds wired
    # HTTP resiliency
    DOBROPOST_RETRY_MAX_ATTEMPTS: int = 4  # incl. first try
    DOBROPOST_RETRY_BACKOFF_BASE_SECONDS: float = 0.5
    DOBROPOST_RETRY_BACKOFF_MAX_SECONDS: float = 8.0
    DOBROPOST_CIRCUIT_FAILURE_THRESHOLD: int = 5
    DOBROPOST_CIRCUIT_RESET_TIMEOUT_SECONDS: float = 30.0

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
