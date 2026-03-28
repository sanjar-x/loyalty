"""
Brand aggregate root entity.

Represents a product brand with name, slug, and optional logo.
Part of the domain layer -- zero infrastructure imports.
"""

import uuid

from attr import dataclass

from src.modules.catalog.domain.exceptions import BrandHasProductsError
from src.shared.interfaces.entities import AggregateRoot

from ._common import _generate_id, _validate_slug

# ---------------------------------------------------------------------------
# DDD-01: Guarded fields set -- fields that may only be changed through
# explicit domain methods, never by direct attribute assignment.
# ---------------------------------------------------------------------------

_BRAND_GUARDED_FIELDS: frozenset[str] = frozenset({"slug"})


@dataclass
class Brand(AggregateRoot):
    """Brand aggregate root.

    Attributes:
        id: Unique brand identifier.
        name: Display name of the brand.
        slug: URL-safe identifier, unique across all brands.
        logo_url: Public URL of the brand logo, or None.
        logo_storage_object_id: Reference to the StorageObject record, or None.
    """

    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None = None
    logo_storage_object_id: uuid.UUID | None = None

    # DDD-01: guard slug against direct mutation
    def __setattr__(self, name: str, value: object) -> None:
        if name in _BRAND_GUARDED_FIELDS and getattr(
            self, "_Brand__initialized", False
        ):
            raise AttributeError(
                f"Cannot set '{name}' directly on Brand. Use the update() method instead."
            )
        super().__setattr__(name, value)

    def __attrs_post_init__(self) -> None:
        super().__attrs_post_init__()
        object.__setattr__(self, "_Brand__initialized", True)

    @classmethod
    def create(
        cls,
        name: str,
        slug: str,
        brand_id: uuid.UUID | None = None,
        logo_url: str | None = None,
        logo_storage_object_id: uuid.UUID | None = None,
    ) -> Brand:
        """Factory method to construct a new Brand aggregate.

        Args:
            name: Display name.
            slug: URL-safe identifier.
            brand_id: Optional pre-generated UUID; generates uuid4 if omitted.
            logo_url: Optional public URL of the brand logo.
            logo_storage_object_id: Optional storage object reference.

        Returns:
            A new Brand instance.
        """
        _validate_slug(slug, "Brand")
        if not name or not name.strip():
            raise ValueError("Brand name must be non-empty")
        return cls(
            id=brand_id or _generate_id(),
            name=name.strip(),
            slug=slug,
            logo_url=logo_url,
            logo_storage_object_id=logo_storage_object_id,
        )

    def update(
        self,
        name: str | None = None,
        slug: str | None = None,
        logo_url: str | None = ...,  # type: ignore[assignment]
        logo_storage_object_id: uuid.UUID | None = ...,  # type: ignore[assignment]
    ) -> None:
        """Update brand details.

        Args:
            name: New display name, or None to keep current.
            slug: New URL-safe slug, or None to keep current.
            logo_url: New logo URL, None to clear, or ``...`` (default) to keep current.
            logo_storage_object_id: New storage object ID, None to clear, or ``...`` (default) to keep current.
        """
        if name is not None:
            if not name or not name.strip():
                raise ValueError("Brand name must be non-empty")
            self.name = name.strip()
        if slug is not None:
            _validate_slug(slug, "Brand")
            # Bypass the guard for controlled mutation via domain method
            object.__setattr__(self, "slug", slug)
        if logo_url is not ...:
            self.logo_url = logo_url
        if logo_storage_object_id is not ...:
            self.logo_storage_object_id = logo_storage_object_id

    # DDD-06: deletion guard
    def validate_deletable(self, *, has_products: bool) -> None:
        """Validate that this brand can be safely deleted.

        Args:
            has_products: Whether the brand still has associated products.

        Raises:
            BrandHasProductsError: If the brand has associated products.
        """
        if has_products:
            raise BrandHasProductsError(brand_id=self.id)
