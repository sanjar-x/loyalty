"""Local configuration — image-rmbg worker.

Same env-var contract as backend (PG_*, REDIS_*, S3_*,
RABBITMQ_PRIVATE_URL) plus the bg-removal knobs (HF_TOKEN,
BG_REMOVAL_*). No import from backend.
"""

from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PGHOST: str
    PGPORT: int = 5432
    PGUSER: str
    PGPASSWORD: SecretStr
    PGDATABASE: str

    REDISHOST: str
    REDISPORT: int = 6379
    REDISUSER: str = "default"
    REDISPASSWORD: SecretStr
    REDISDATABASE: int = 0

    S3_ENDPOINT_URL: str
    S3_REGION: str = "auto"
    S3_ACCESS_KEY: SecretStr
    S3_SECRET_KEY: SecretStr
    S3_BUCKET_NAME: str
    S3_PUBLIC_BASE_URL: str

    RABBITMQ_PRIVATE_URL: str

    # Background-removal-specific knobs.
    HF_TOKEN: SecretStr | None = None
    BG_REMOVAL_DEVICE: str = "auto"  # "auto" | "cpu" | "cuda"
    BG_REMOVAL_MODEL_CACHE_DIR: str = "/data/hf_cache"
    BG_REMOVAL_WEBP_QUALITY: int = 90

    @property
    def database_url(self) -> str:
        return (
            "postgresql+asyncpg://"
            f"{self.PGUSER}:{self.PGPASSWORD.get_secret_value()}"
            f"@{self.PGHOST}:{self.PGPORT}/{self.PGDATABASE}"
        )

    @property
    def redis_url(self) -> str:
        return (
            "redis://"
            f"{self.REDISUSER}:{self.REDISPASSWORD.get_secret_value()}"
            f"@{self.REDISHOST}:{self.REDISPORT}/{self.REDISDATABASE}"
        )


settings = Settings()  # ty:ignore[missing-argument]
