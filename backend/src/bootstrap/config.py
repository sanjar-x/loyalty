"""Application settings loaded from environment variables.

All configuration values are validated at startup via Pydantic Settings.
A cached singleton is exposed as ``settings`` for convenient import
throughout the codebase.
"""

import uuid
from functools import lru_cache
from typing import Annotated, Any, Literal, Self

from pydantic import BeforeValidator, Field, computed_field, model_validator
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

    # CFG-001 — ``API_V2_STR`` removed (0 readers; ``API_V1_STR`` is the
    # only mounted prefix today, see ``bootstrap/web.py``). Add back when
    # /api/v2 lands; keeping unused config keys hides intent.
    API_V1_STR: str = "/api/v1"
    ALGORITHM: str = "HS256"

    SECRET_KEY: SecretStr
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, gt=0)

    # IAM RBAC settings
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30, gt=0)
    SESSION_PERMISSIONS_CACHE_TTL: int = Field(default=300, ge=0)
    MAX_ACTIVE_SESSIONS_PER_IDENTITY: int = Field(default=5, ge=1)
    SESSION_IDLE_TIMEOUT_MINUTES: int = Field(default=30, gt=0)
    # CFG-001 — ``SESSION_ABSOLUTE_LIFETIME_HOURS`` and
    # ``TELEGRAM_SESSION_ABSOLUTE_LIFETIME_HOURS`` removed (0 readers).
    # Restore when an absolute-cap policy lands in identity.
    TELEGRAM_SESSION_IDLE_TIMEOUT_MINUTES: int = Field(default=1440, gt=0)

    CORS_ORIGINS: Annotated[list[str] | str, BeforeValidator(parse_cors)] = []

    SYSTEM_USER_ID: uuid.UUID = uuid.UUID(int=0)

    PGHOST: str
    PGPORT: int = Field(ge=1, le=65535)
    PGUSER: str
    PGPASSWORD: SecretStr
    PGDATABASE: str

    # Connection pool sizing — INFRA-001.
    # Conservative defaults so 4 uvicorn workers × N processes (api +
    # outbox relay + scheduler + bot) stay under typical Postgres
    # ``max_connections=100`` ceiling without PgBouncer. With pool=8 +
    # overflow=4 = 12 max per process × 6 processes = 72 conns peak.
    # Bump these when fronting Postgres with PgBouncer (transaction
    # mode), where the engine pool becomes a soft semaphore against the
    # bouncer rather than a hard PG limit.
    DB_POOL_SIZE: int = Field(default=8, gt=0)
    DB_POOL_MAX_OVERFLOW: int = Field(default=4, ge=0)
    DB_POOL_TIMEOUT_SECONDS: float = Field(default=30.0, gt=0)
    DB_POOL_RECYCLE_SECONDS: int = Field(default=3600, gt=0)

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
    REDISPORT: int = Field(ge=1, le=65535)
    REDISUSER: str = "default"
    REDISPASSWORD: SecretStr | None = None
    REDISDATABASE: int = Field(default=0, ge=0)

    # CFG-001 — ``INTERNAL_WEBHOOK_SECRET`` removed (0 readers).
    # Restore via ``Field(min_length=32)`` when the s2s webhook signing
    # path is wired up.

    RABBITMQ_PRIVATE_URL: str

    # -- Telegram Bot --------------------------------------------------------
    BOT_TOKEN: SecretStr
    # CFG-001 — ``BOT_ADMIN_IDS`` / ``BOT_WEBHOOK_URL`` /
    # ``BOT_WEBHOOK_SECRET`` removed (0 readers). Bot uses long-polling
    # in current deploy; restore when webhook mode lands.
    THROTTLE_RATE: float = Field(default=0.5, gt=0)
    FSM_STATE_TTL: int | None = Field(default=None, ge=0)
    FSM_DATA_TTL: int | None = Field(default=None, ge=0)

    TELEGRAM_INIT_DATA_MAX_AGE: int = Field(default=300, gt=0)
    TELEGRAM_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, gt=0)

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
    MEDIA_MAX_FILE_SIZE: int = Field(default=50 * 1024 * 1024, gt=0)
    MEDIA_PRESIGNED_URL_TTL: int = Field(default=300, gt=0)
    # CFG-001 — ``MEDIA_SSE_TIMEOUT`` removed (0 readers).

    # -- Background removal (IMG-007) ---------------------------------------
    # Toggleable feature: the admin endpoint returns 503 with a clear
    # error when ``BG_REMOVAL_ENABLED=False`` so the contract stays
    # observable even on environments where the heavy ML deps
    # (``torch`` / ``transformers``) aren't installed. Production
    # ``image_ml`` worker installs the optional ``[bg-removal]`` extra
    # and flips this to True; the web service stays lean.
    BG_REMOVAL_ENABLED: bool = False
    # ``auto`` picks ``cuda`` when ``torch.cuda.is_available()``,
    # else ``cpu``. Override to a specific value when running on a
    # known device (avoids the import-time ``torch`` probe in tests).
    BG_REMOVAL_DEVICE: Literal["auto", "cpu", "cuda"] = "auto"
    # HF_HOME / cache directory for the briaai/RMBG-2.0 weights
    # (~1.6 GB). Persistent volume on Railway so worker restarts
    # don't re-download. Falls back to a tmp path locally.
    BG_REMOVAL_MODEL_CACHE_DIR: str = "/tmp/hf_cache"
    # Output WebP quality for the alpha-channel result. Lower than
    # the regular gallery main (q=90) is fine — the cutout is the
    # foreground only and visual artefacts in fully-transparent
    # regions are invisible.
    BG_REMOVAL_WEBP_QUALITY: int = Field(default=92, ge=0, le=100)

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
    PAYMENT_AUTH_TTL_DAYS: int = Field(default=7, gt=0)  # Visa-стандарт hold

    # -- DobroPost (cross-border) ------------------------------------------
    DOBROPOST_BASE_URL: str = "https://api.dobropost.com"
    DOBROPOST_EMAIL: SecretStr = SecretStr("")
    DOBROPOST_PASSWORD: SecretStr = SecretStr("")
    DOBROPOST_DEFAULT_TARIFF_ID: int = Field(default=1, gt=0)
    DOBROPOST_TIMEOUT_SECONDS: float = Field(default=30.0, gt=0)
    DOBROPOST_TOKEN_REFRESH_BEFORE_SECONDS: int = Field(default=3600, gt=0)
    # Webhook authentication: random secret embedded in URL path
    # ``/api/v1/orders/webhooks/dobropost/{token}``.
    DOBROPOST_WEBHOOK_TOKEN: SecretStr = SecretStr("")
    DOBROPOST_ALLOWED_IPS: list[str] = []
    DOBROPOST_USE_STUB: bool = True  # Flip to false in prod once creds wired
    # HTTP resiliency. ``RETRY_MAX_ATTEMPTS`` includes the first try, so
    # ``ge=1`` means "at least try once". ``BACKOFF_BASE <= MAX`` is
    # checked in :meth:`_validate_dobropost_invariants`.
    DOBROPOST_RETRY_MAX_ATTEMPTS: int = Field(default=4, ge=1)
    DOBROPOST_RETRY_BACKOFF_BASE_SECONDS: float = Field(default=0.5, gt=0)
    DOBROPOST_RETRY_BACKOFF_MAX_SECONDS: float = Field(default=8.0, gt=0)
    DOBROPOST_CIRCUIT_FAILURE_THRESHOLD: int = Field(default=5, ge=1)
    DOBROPOST_CIRCUIT_RESET_TIMEOUT_SECONDS: float = Field(default=30.0, gt=0)

    @computed_field
    @property
    def redis_url(self) -> str:
        """Build a Redis connection URL from individual settings."""
        credentials = ""
        if self.REDISPASSWORD:
            credentials = f"{self.REDISUSER}:{self.REDISPASSWORD.get_secret_value()}@"

        return f"redis://{credentials}{self.REDISHOST}:{self.REDISPORT}/{self.REDISDATABASE}"

    # ------------------------------------------------------------------ #
    # Cross-field invariants (CFG-001)
    # ------------------------------------------------------------------ #

    @model_validator(mode="after")
    def _validate_dobropost_invariants(self) -> Self:
        """Fail startup if DobroPost real-mode is on without credentials.

        Pre-CFG-001 the missing credential surfaced as a 401 from
        ``/api/shipment/sign-in`` on the first webhook (or order
        booking) hitting prod. Now we fail boot, which is observable
        on the deploy-readiness probe and rolls back the bad release
        before it serves any traffic.

        Also enforces ``BACKOFF_BASE <= BACKOFF_MAX`` — without it the
        retry loop would compute a max-clamp below the base, which
        :func:`min` silently swallows but defeats the whole point of
        capping backoff growth.
        """
        if not self.DOBROPOST_USE_STUB:
            missing: list[str] = []
            if not self.DOBROPOST_EMAIL.get_secret_value():
                missing.append("DOBROPOST_EMAIL")
            if not self.DOBROPOST_PASSWORD.get_secret_value():
                missing.append("DOBROPOST_PASSWORD")
            if not self.DOBROPOST_WEBHOOK_TOKEN.get_secret_value():
                missing.append("DOBROPOST_WEBHOOK_TOKEN")
            if missing:
                raise ValueError(
                    "DOBROPOST_USE_STUB=false requires non-empty credentials: "
                    f"{', '.join(missing)}. Either flip USE_STUB=true or "
                    "fill the missing env vars."
                )

        if self.DOBROPOST_RETRY_BACKOFF_BASE_SECONDS > (
            self.DOBROPOST_RETRY_BACKOFF_MAX_SECONDS
        ):
            raise ValueError(
                "DOBROPOST_RETRY_BACKOFF_BASE_SECONDS "
                f"({self.DOBROPOST_RETRY_BACKOFF_BASE_SECONDS}) must be "
                "<= DOBROPOST_RETRY_BACKOFF_MAX_SECONDS "
                f"({self.DOBROPOST_RETRY_BACKOFF_MAX_SECONDS})."
            )

        return self

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
