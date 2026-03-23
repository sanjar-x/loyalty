"""
Deterministic S3 key builders for the Catalog module.

Keys are computed from the aggregate identifier, eliminating the need
for a synchronous call to the Storage module when creating entities.
Part of the application layer.

Typical usage:
    from src.modules.catalog.application.constants import raw_logo_key

    key = raw_logo_key(brand_id)  # "raw_uploads/catalog/brands/<uuid>/logo_raw"
"""

import uuid


def raw_logo_key(brand_id: uuid.UUID) -> str:
    """Build the S3 key for a brand's raw (unprocessed) logo upload.

    Args:
        brand_id: UUID of the brand aggregate.

    Returns:
        S3 object key string.
    """
    return f"raw_uploads/catalog/brands/{brand_id}/logo_raw"


def public_logo_key(brand_id: uuid.UUID) -> str:
    """Build the S3 key for a brand's processed (public) logo.

    Args:
        brand_id: UUID of the brand aggregate.

    Returns:
        S3 object key string pointing to the WebP-converted logo.
    """
    return f"public/brands/{brand_id}/logo.webp"


def raw_media_key(product_id: uuid.UUID, media_id: uuid.UUID) -> str:
    """Build the S3 key for a product media's raw (unprocessed) upload."""
    return f"raw_uploads/catalog/products/{product_id}/media/{media_id}"


def public_media_key(product_id: uuid.UUID, media_id: uuid.UUID, ext: str = "webp") -> str:
    """Build the S3 key for a product media's processed (public) file."""
    return f"public/products/{product_id}/media/{media_id}.{ext}"


CATEGORY_TREE_CACHE_KEY = "catalog:category_tree"
"""Redis cache key for the full category tree JSON payload."""

CATEGORY_TREE_CACHE_TTL_SECONDS = 300
"""TTL for the category tree Redis cache (5 minutes)."""

PRESIGNED_URL_EXPIRATION_SECONDS = 300
"""Expiration time in seconds for S3 presigned PUT URLs (5 minutes)."""


def storefront_cache_key(category_id: uuid.UUID) -> str:
    """Build the Redis cache key for storefront attribute data of a category.

    Args:
        category_id: UUID of the category.

    Returns:
        Redis cache key string.
    """
    return f"catalog:storefront:{category_id}"


STOREFRONT_CACHE_TTL_SECONDS = 300
"""TTL for storefront attribute cache entries (5 minutes)."""
