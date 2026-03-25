import io
import uuid
import pytest
from PIL import Image

from src.modules.storage.application.commands.process_image import (
    resize_to_fit,
    convert_to_webp,
    build_variants,
    VARIANT_SIZES,
)


def _make_test_image(w: int, h: int, fmt: str = "JPEG") -> bytes:
    img = Image.new("RGB", (w, h), color="red")
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def test_variant_sizes_defined():
    assert VARIANT_SIZES["thumbnail"] == (150, 150)
    assert VARIANT_SIZES["medium"] == (600, 600)
    assert VARIANT_SIZES["large"] == (1200, 1200)


def test_resize_to_fit_preserves_aspect_ratio():
    img = Image.new("RGB", (2000, 1000))
    resized = resize_to_fit(img, 600, 600)
    assert resized.width == 600
    assert resized.height == 300


def test_resize_to_fit_no_upscale():
    img = Image.new("RGB", (100, 50))
    resized = resize_to_fit(img, 600, 600)
    assert resized.width == 100
    assert resized.height == 50


def test_convert_to_webp_returns_valid_webp():
    raw = _make_test_image(100, 100)
    result = convert_to_webp(raw, quality=85)
    img = Image.open(io.BytesIO(result))
    assert img.format == "WEBP"


def test_convert_to_webp_lossless():
    raw = _make_test_image(100, 100)
    result = convert_to_webp(raw, lossless=True)
    img = Image.open(io.BytesIO(result))
    assert img.format == "WEBP"


def test_convert_to_webp_with_resize():
    raw = _make_test_image(2000, 1000)
    result = convert_to_webp(raw, max_size=(600, 600))
    img = Image.open(io.BytesIO(result))
    assert img.width == 600
    assert img.height == 300


def test_convert_to_webp_handles_rgba():
    img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    result = convert_to_webp(buf.getvalue())
    assert isinstance(result, bytes)


def test_build_variants_produces_three_sizes():
    raw = _make_test_image(2000, 1500)
    sid = uuid.uuid4()
    main_bytes, variants_meta, variants_data = build_variants(
        raw, sid, "https://cdn.example.com"
    )
    assert isinstance(main_bytes, bytes)
    assert len(variants_meta) == 3
    assert len(variants_data) == 3
    sizes = {v["size"] for v in variants_meta}
    assert sizes == {"thumbnail", "medium", "large"}
    thumb = next(v for v in variants_meta if v["size"] == "thumbnail")
    assert thumb["width"] <= 150
    assert thumb["height"] <= 150
    assert "cdn.example.com" in thumb["url"]
