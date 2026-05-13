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

    # rmbg recipe tuning (see rmbg/README.md for the rationale).
    # Letterbox to 1024×1024 instead of stretching — preserves aspect
    # ratio so fine structures (hair, fur, transparent edges) survive.
    BG_REMOVAL_KEEP_ASPECT: bool = True
    # Gaussian blur radius (px) softening the alpha mask edge. 1.0 hides
    # the hard 1-pixel transition where the mask meets the keep region.
    BG_REMOVAL_FEATHER: float = 1.0
    # NHWC layout — oneDNN picks faster Conv2d kernels on CPU. Also
    # benefits Ampere+ GPUs. Free win, leave on.
    BG_REMOVAL_CHANNELS_LAST: bool = True
    # CPU intra-op thread count. ``None`` lets PyTorch auto-pick.
    # Pin to physical core count to dodge hyper-threading contention.
    # Only applied when device resolves to ``cpu``.
    BG_REMOVAL_NUM_THREADS: int | None = None

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
