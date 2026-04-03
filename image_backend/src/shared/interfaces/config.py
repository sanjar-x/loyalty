"""
Storage configuration port.

Defines the minimal configuration contract that the storage module
needs from the application settings. Decouples infrastructure code
from the concrete ``Settings`` class.

Typical usage:
    class StorageService:
        def __init__(self, config: IStorageConfig) -> None:
            bucket = config.S3_BUCKET_NAME
"""

from typing import Protocol


class IStorageConfig(Protocol):
    """Contract for object storage configuration values.

    Attributes:
        S3_BUCKET_NAME: Name of the S3-compatible bucket.
        S3_PUBLIC_BASE_URL: Public base URL for constructing
            downloadable object links.
    """

    S3_BUCKET_NAME: str
    S3_PUBLIC_BASE_URL: str
    MAX_FILE_SIZE: int
