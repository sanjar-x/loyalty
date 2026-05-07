"""Image processing pipeline — Pillow-based resize/convert to WebP.

Pure functions: take raw bytes in, produce WebP bytes + variant metadata
out. No I/O, no DB. Used by the worker that consumes
``StorageObjectModel`` rows in PROCESSING status.
"""

from __future__ import annotations

import io
import uuid

from PIL import Image
from PIL.Image import Resampling

VARIANT_SIZES: dict[str, tuple[int, int]] = {
    "thumbnail": (150, 150),
    "medium": (600, 600),
    "large": (1200, 1200),
}

_VARIANT_SUFFIX: dict[str, str] = {
    "thumbnail": "thumb",
    "medium": "md",
    "large": "lg",
}


def resize_to_fit(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    """Resize preserving aspect ratio to fit within (max_w, max_h)."""
    img.thumbnail((max_w, max_h), Resampling.LANCZOS)
    return img


def convert_to_webp(
    raw_data: bytes,
    *,
    quality: int = 85,
    lossless: bool = False,
    max_size: tuple[int, int] | None = None,
) -> bytes:
    """Convert raw image bytes to WebP format.

    Args:
        raw_data: Original image bytes (any format Pillow supports).
        quality: WebP quality 0-100 (ignored if ``lossless=True``).
        lossless: Use lossless WebP encoding for the main file.
        max_size: Optional ``(max_w, max_h)`` to fit-resize before encoding.

    Returns:
        WebP-encoded bytes ready for S3 upload.
    """
    img = Image.open(io.BytesIO(raw_data))
    img = img.convert("RGBA") if img.mode in ("RGBA", "LA", "P") else img.convert("RGB")
    if max_size:
        img = resize_to_fit(img, *max_size)
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=quality, lossless=lossless)
    return buf.getvalue()


def build_variants(
    raw_data: bytes,
    storage_object_id: uuid.UUID,
    public_base_url: str,
) -> tuple[bytes, list[dict], dict[str, bytes]]:
    """Process raw image into a main WebP + size variants.

    Args:
        raw_data: Original uploaded image bytes.
        storage_object_id: UUID used to build variant S3 keys.
        public_base_url: CDN/public origin used to build variant URLs.

    Returns:
        Tuple of:
            - ``main_webp_bytes`` — lossless WebP of the original.
            - ``variant_meta`` — list of dicts ``{size, width, height, url}``.
            - ``variant_data`` — mapping ``s3_key`` → variant bytes.
    """
    main_bytes = convert_to_webp(raw_data, lossless=True)
    variants_meta: list[dict] = []
    variants_data: dict[str, bytes] = {}

    for size_name, (w, h) in VARIANT_SIZES.items():
        variant_bytes = convert_to_webp(raw_data, quality=85, max_size=(w, h))
        img = Image.open(io.BytesIO(variant_bytes))
        suffix = _VARIANT_SUFFIX[size_name]
        s3_key = f"public/{storage_object_id}_{suffix}.webp"
        url = f"{public_base_url.rstrip('/')}/{s3_key}"

        variants_meta.append(
            {
                "size": size_name,
                "width": img.width,
                "height": img.height,
                "url": url,
            }
        )
        variants_data[s3_key] = variant_bytes

    return main_bytes, variants_meta, variants_data
