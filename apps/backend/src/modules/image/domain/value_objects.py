"""Image module domain value objects."""

from enum import StrEnum


class StorageStatus(StrEnum):
    """Processing lifecycle of a storage object."""

    PENDING_UPLOAD = "PENDING_UPLOAD"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    @property
    def is_terminal(self) -> bool:
        return self in (StorageStatus.COMPLETED, StorageStatus.FAILED)


class DerivationKind(StrEnum):
    """Kind of transformation applied to a parent storage object.

    A *derivation* is a new ``StorageFile`` produced by running an
    ML / DSP pipeline against an existing one (the parent). It carries
    its own ``id``, S3 keys, and ``image_variants`` so it can be
    attached to a product like any other media — but the
    ``parent_storage_object_id`` link lets the admin UI offer
    "revert to original" without a fresh upload.
    """

    BG_REMOVED = "BG_REMOVED"
    # Future: UPSCALED, WATERMARKED, COLOR_CORRECTED — same lifecycle,
    # different ML adapter behind the IBackgroundRemover-style port.
