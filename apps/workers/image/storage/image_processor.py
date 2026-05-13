"""Pillow image processing — pure functions, no I/O.

Local copy of the build-variants logic — worker doesn't import the
backend's ``image_processor`` module. The pure-function shape (bytes
in, bytes + metadata out) keeps the file self-contained and easy to
test in isolation.
"""

from __future__ import annotations

import io
import uuid
from typing import Any

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

# Quality knobs. 90 = visually indistinguishable from the original for
# product photography at ~25-35% the file size of lossless. Variants
# stay at 85 because they are downscaled and tolerate slightly more
# aggressive compression.
_MAIN_QUALITY: int = 90
_VARIANT_QUALITY: int = 85


def _resize_to_fit(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    """Resize preserving aspect ratio to fit within (max_w, max_h)."""
    img.thumbnail((max_w, max_h), Resampling.LANCZOS)
    return img


def _convert_to_webp(
    raw_data: bytes,
    *,
    quality: int = 85,
    lossless: bool = False,
    max_size: tuple[int, int] | None = None,
) -> bytes:
    """Convert raw image bytes to WebP."""
    img = Image.open(io.BytesIO(raw_data))
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
    else:
        img = img.convert("RGB")
    if max_size:
        img = _resize_to_fit(img, *max_size)
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=quality, lossless=lossless)
    return buf.getvalue()


def build_variants(
    raw_data: bytes,
    storage_object_id: uuid.UUID,
    public_base_url: str,
) -> tuple[bytes, list[dict[str, Any]], dict[str, bytes]]:
    """Process raw image into main WebP + size variants.

    Returns ``(main_bytes, variant_meta, variant_data)``:
        - ``main_bytes`` — lossy WebP of the original.
        - ``variant_meta`` — list of ``{size, width, height, url}`` dicts.
        - ``variant_data`` — mapping ``s3_key`` → variant bytes.
    """
    main_bytes = _convert_to_webp(
        raw_data, quality=_MAIN_QUALITY, lossless=False
    )
    variants_meta: list[dict[str, Any]] = []
    variants_data: dict[str, bytes] = {}

    for size_name, (w, h) in VARIANT_SIZES.items():
        variant_bytes = _convert_to_webp(
            raw_data, quality=_VARIANT_QUALITY, max_size=(w, h)
        )
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
