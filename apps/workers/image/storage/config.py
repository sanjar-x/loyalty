"""Local configuration — image-storage worker.

Reads the same environment variables as backend (PG_*, REDIS_*, S3_*,
RABBITMQ_PRIVATE_URL) but does NOT inherit ``backend.bootstrap.config``.
This worker is a standalone deployable artefact — its Settings live
here.
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

    # PostgreSQL — same row format as backend writes; worker only updates
    # storage_objects status / url / image_variants / size_bytes and
    # appends outbox rows.
    PGHOST: str
    PGPORT: int = 5432
    PGUSER: str
    PGPASSWORD: SecretStr
    PGDATABASE: str

    # Redis — used for status streaming via Redis Streams.
    REDISHOST: str
    REDISPORT: int = 6379
    REDISUSER: str = "default"
    REDISPASSWORD: SecretStr
    REDISDATABASE: int = 0

    # S3 / object storage — worker downloads raw uploads, uploads main
    # WebP + variants, deletes the raw upload on success.
    S3_ENDPOINT_URL: str
    S3_REGION: str = "auto"
    S3_ACCESS_KEY: SecretStr
    S3_SECRET_KEY: SecretStr
    S3_BUCKET_NAME: str
    S3_PUBLIC_BASE_URL: str

    # RabbitMQ — worker consumes from image.processing /
    # image.maintenance queues on this broker.
    RABBITMQ_PRIVATE_URL: str

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
