"""
MediaAsset entity for product media resources.

Simple data record for a product media asset. No AggregateRoot,
no FSM, no domain events. Physical files live in ImageBackend
(referenced by storage_object_id).
Part of the domain layer -- zero infrastructure imports.
"""

import uuid
from datetime import datetime

from attrs import define

from src.modules.catalog.domain.value_objects import MediaRole, MediaType

from ._common import _generate_id


@define
class MediaAsset:
    """Simple data record for a product media asset.

    No AggregateRoot, no FSM, no domain events.
    Physical files live in ImageBackend (referenced by storage_object_id).
    """

    id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID | None

    media_type: MediaType
    role: MediaRole
    sort_order: int
    is_external: bool = False

    storage_object_id: uuid.UUID | None = None
    url: str | None = None
    image_variants: list[dict] | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        product_id: uuid.UUID,
        variant_id: uuid.UUID | None = None,
        media_type: str | MediaType,
        role: str | MediaRole,
        sort_order: int = 0,
        is_external: bool = False,
        storage_object_id: uuid.UUID | None = None,
        url: str | None = None,
        image_variants: list[dict] | None = None,
    ) -> MediaAsset:
        """Factory method to construct a new MediaAsset.

        Args:
            product_id: UUID of the owning Product aggregate.
            variant_id: Optional UUID of the owning ProductVariant.
            media_type: Media type as string or MediaType enum.
            role: Media role as string or MediaRole enum.
            sort_order: Display ordering (must be >= 0).
            is_external: Whether the asset is externally hosted.
            storage_object_id: Optional reference to a StorageObject record.
            url: Optional public URL (required for external assets).
            image_variants: Optional list of image variant metadata dicts.

        Returns:
            A new MediaAsset instance.

        Raises:
            ValueError: If media_type/role is invalid, sort_order < 0,
                or an external asset has no URL.
        """
        if isinstance(media_type, str):
            try:
                media_type = MediaType(media_type.lower())
            except ValueError:
                raise ValueError(
                    f"Invalid media_type '{media_type}'. "
                    f"Must be one of: {', '.join(m.value for m in MediaType)}"
                )
        if isinstance(role, str):
            try:
                role = MediaRole(role.lower())
            except ValueError:
                raise ValueError(
                    f"Invalid role '{role}'. "
                    f"Must be one of: {', '.join(r.value for r in MediaRole)}"
                )
        if sort_order < 0:
            raise ValueError("MediaAsset sort_order must be non-negative")
        if is_external and not url:
            raise ValueError("External media assets must have a URL")
        return cls(
            id=_generate_id(),
            product_id=product_id,
            variant_id=variant_id,
            media_type=media_type,
            role=role,
            sort_order=sort_order,
            is_external=is_external,
            storage_object_id=storage_object_id,
            url=url,
            image_variants=image_variants,
        )
