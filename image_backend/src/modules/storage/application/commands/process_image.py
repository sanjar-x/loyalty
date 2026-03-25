"""Image processing pipeline — Pillow-based resize/convert to WebP."""
from __future__ import annotations

import io
import uuid

from PIL import Image

VARIANT_SIZES: dict[str, tuple[int, int]] = {
    "thumbnail": (150, 150),
    "medium": (600, 600),
    "large": (1200, 1200),
}


def resize_to_fit(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    """Resize preserving aspect ratio to fit within (max_w, max_h)."""
    img.thumbnail((max_w, max_h), Image.LANCZOS)
    return img


def convert_to_webp(
    raw_data: bytes,
    *,
    quality: int = 85,
    lossless: bool = False,
    max_size: tuple[int, int] | None = None,
) -> bytes:
    """Convert raw image bytes to WebP format."""
    img = Image.open(io.BytesIO(raw_data))
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
    else:
        img = img.convert("RGB")
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
    """Process raw image into main + size variants.

    Returns:
        (main_webp_bytes, variant_metadata_list, variant_name_to_bytes)
    """
    main_bytes = convert_to_webp(raw_data, lossless=True)
    variants_meta: list[dict] = []
    variants_data: dict[str, bytes] = {}

    for size_name, (w, h) in VARIANT_SIZES.items():
        variant_bytes = convert_to_webp(raw_data, quality=85, max_size=(w, h))
        img = Image.open(io.BytesIO(variant_bytes))
        suffix = {"thumbnail": "thumb", "medium": "md", "large": "lg"}[size_name]
        s3_key = f"public/{storage_object_id}_{suffix}.webp"
        url = f"{public_base_url.rstrip('/')}/{s3_key}"

        variants_meta.append({
            "size": size_name,
            "width": img.width,
            "height": img.height,
            "url": url,
        })
        variants_data[s3_key] = variant_bytes

    return main_bytes, variants_meta, variants_data
