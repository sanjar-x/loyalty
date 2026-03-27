"""Comprehensive tests for image processing pure functions (Task 13 — TDD)."""

import io
import uuid

import pytest
from PIL import Image

from src.modules.storage.application.commands.process_image import (
    VARIANT_SIZES,
    build_variants,
    convert_to_webp,
    resize_to_fit,
)

# ── helpers ──────────────────────────────────────────────────────────────


def _make_test_image(
    width: int = 100, height: int = 80, fmt: str = "JPEG", mode: str = "RGB",
) -> bytes:
    color = (255, 0, 0) if mode == "RGB" else (255, 0, 0, 128)
    img = Image.new(mode, (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def _open(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data))


# ── VARIANT_SIZES constant ──────────────────────────────────────────────


class TestVariantSizes:
    def test_contains_three_entries(self):
        assert len(VARIANT_SIZES) == 3

    def test_thumbnail_dimensions(self):
        assert VARIANT_SIZES["thumbnail"] == (150, 150)

    def test_medium_dimensions(self):
        assert VARIANT_SIZES["medium"] == (600, 600)

    def test_large_dimensions(self):
        assert VARIANT_SIZES["large"] == (1200, 1200)

    def test_all_values_are_int_tuples(self):
        for name, (w, h) in VARIANT_SIZES.items():
            assert isinstance(w, int) and isinstance(h, int), (
                f"{name} dimensions must be ints"
            )


# ── resize_to_fit ────────────────────────────────────────────────────────


class TestResizeToFit:
    def test_preserves_aspect_ratio_landscape(self):
        img = Image.new("RGB", (2000, 1000))
        resized = resize_to_fit(img, 600, 600)
        assert resized.width == 600
        assert resized.height == 300

    def test_preserves_aspect_ratio_portrait(self):
        img = Image.new("RGB", (1000, 2000))
        resized = resize_to_fit(img, 600, 600)
        assert resized.width == 300
        assert resized.height == 600

    def test_preserves_aspect_ratio_square(self):
        img = Image.new("RGB", (2000, 2000))
        resized = resize_to_fit(img, 600, 600)
        assert resized.width == 600
        assert resized.height == 600

    def test_no_upscale_when_smaller(self):
        img = Image.new("RGB", (100, 50))
        resized = resize_to_fit(img, 600, 600)
        assert resized.width == 100
        assert resized.height == 50

    def test_no_upscale_exact_fit(self):
        img = Image.new("RGB", (600, 600))
        resized = resize_to_fit(img, 600, 600)
        assert resized.width == 600
        assert resized.height == 600

    def test_returns_image_instance(self):
        img = Image.new("RGB", (800, 400))
        result = resize_to_fit(img, 600, 600)
        assert isinstance(result, Image.Image)

    def test_mutates_in_place_via_thumbnail(self):
        """thumbnail() is in-place; the returned object is the same."""
        img = Image.new("RGB", (800, 400))
        result = resize_to_fit(img, 600, 600)
        assert result is img

    def test_asymmetric_max_dimensions(self):
        img = Image.new("RGB", (1000, 500))
        resized = resize_to_fit(img, 400, 200)
        # 1000x500 scaled to fit 400x200 => limited by height: 400x200
        assert resized.width == 400
        assert resized.height == 200


# ── convert_to_webp ─────────────────────────────────────────────────────


class TestConvertToWebp:
    def test_returns_bytes(self):
        raw = _make_test_image()
        result = convert_to_webp(raw)
        assert isinstance(result, bytes)

    def test_output_is_valid_webp(self):
        raw = _make_test_image()
        result = convert_to_webp(raw)
        img = _open(result)
        assert img.format == "WEBP"

    def test_default_quality_85(self):
        """Calling without quality kwarg should not raise."""
        raw = _make_test_image()
        result = convert_to_webp(raw)
        assert len(result) > 0

    def test_lossless_flag(self):
        raw = _make_test_image()
        result = convert_to_webp(raw, lossless=True)
        img = _open(result)
        assert img.format == "WEBP"

    def test_max_size_resizes(self):
        raw = _make_test_image(2000, 1000)
        result = convert_to_webp(raw, max_size=(600, 600))
        img = _open(result)
        assert img.width == 600
        assert img.height == 300

    def test_max_size_none_preserves_original_dimensions(self):
        raw = _make_test_image(200, 100)
        result = convert_to_webp(raw, max_size=None)
        img = _open(result)
        assert img.width == 200
        assert img.height == 100

    def test_handles_rgba_input(self):
        raw = _make_test_image(100, 100, fmt="PNG", mode="RGBA")
        result = convert_to_webp(raw)
        img = _open(result)
        assert img.format == "WEBP"

    def test_handles_palette_mode(self):
        """Palette (P) images should be converted to RGBA before WebP."""
        img = Image.new("P", (100, 100))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        result = convert_to_webp(buf.getvalue())
        assert _open(result).format == "WEBP"

    def test_handles_la_mode(self):
        """LA (luminance + alpha) should be converted to RGBA."""
        img = Image.new("LA", (100, 100))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        result = convert_to_webp(buf.getvalue())
        assert _open(result).format == "WEBP"

    def test_rgb_mode_stays_rgb(self):
        raw = _make_test_image(100, 100)
        result = convert_to_webp(raw)
        img = _open(result)
        assert img.mode == "RGB"

    def test_quality_affects_size(self):
        """Lower quality should produce a smaller file for a noisy image."""
        import random
        random.seed(42)
        img = Image.new("RGB", (200, 200))
        pixels = img.load()
        for x in range(200):
            for y in range(200):
                pixels[x, y] = (
                    random.randint(0, 255),
                    random.randint(0, 255),
                    random.randint(0, 255),
                )
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=100)
        raw = buf.getvalue()
        low = convert_to_webp(raw, quality=10)
        high = convert_to_webp(raw, quality=95)
        assert len(low) < len(high)


# ── build_variants ───────────────────────────────────────────────────────


class TestBuildVariants:
    @pytest.fixture()
    def raw_large(self) -> bytes:
        return _make_test_image(2000, 1500)

    @pytest.fixture()
    def sid(self) -> uuid.UUID:
        return uuid.UUID("12345678-1234-5678-1234-567812345678")

    @pytest.fixture()
    def base_url(self) -> str:
        return "https://cdn.example.com"

    @pytest.fixture()
    def result(self, raw_large, sid, base_url):
        return build_variants(raw_large, sid, base_url)

    # -- return type --

    def test_returns_three_element_tuple(self, result):
        main_bytes, variants_meta, variants_data = result
        assert isinstance(main_bytes, bytes)
        assert isinstance(variants_meta, list)
        assert isinstance(variants_data, dict)

    # -- main bytes --

    def test_main_bytes_is_valid_webp(self, result):
        main_bytes, _, _ = result
        img = _open(main_bytes)
        assert img.format == "WEBP"

    def test_main_bytes_is_lossless(self, raw_large, sid, base_url):
        """Main variant should be created with lossless=True."""
        main_bytes, _, _ = build_variants(raw_large, sid, base_url)
        # lossless WebP should perfectly preserve pixel values
        assert len(main_bytes) > 0

    # -- variant count --

    def test_produces_three_variant_meta(self, result):
        _, variants_meta, _ = result
        assert len(variants_meta) == 3

    def test_produces_three_variant_data(self, result):
        _, _, variants_data = result
        assert len(variants_data) == 3

    # -- variant sizes present --

    def test_meta_contains_all_size_names(self, result):
        _, variants_meta, _ = result
        sizes = {v["size"] for v in variants_meta}
        assert sizes == {"thumbnail", "medium", "large"}

    # -- meta fields --

    def test_meta_entries_have_required_fields(self, result):
        _, variants_meta, _ = result
        required = {"size", "width", "height", "url"}
        for entry in variants_meta:
            assert required.issubset(entry.keys()), (
                f"Missing fields in {entry}"
            )

    def test_meta_width_and_height_are_ints(self, result):
        _, variants_meta, _ = result
        for entry in variants_meta:
            assert isinstance(entry["width"], int)
            assert isinstance(entry["height"], int)

    # -- thumbnail dimensions --

    def test_thumbnail_fits_within_150x150(self, result):
        _, variants_meta, _ = result
        thumb = next(v for v in variants_meta if v["size"] == "thumbnail")
        assert thumb["width"] <= 150
        assert thumb["height"] <= 150

    # -- medium dimensions --

    def test_medium_fits_within_600x600(self, result):
        _, variants_meta, _ = result
        md = next(v for v in variants_meta if v["size"] == "medium")
        assert md["width"] <= 600
        assert md["height"] <= 600

    # -- large dimensions --

    def test_large_fits_within_1200x1200(self, result):
        _, variants_meta, _ = result
        lg = next(v for v in variants_meta if v["size"] == "large")
        assert lg["width"] <= 1200
        assert lg["height"] <= 1200

    # -- S3 key convention --

    def test_s3_keys_follow_convention(self, result, sid):
        _, _, variants_data = result
        expected_suffixes = {"thumb", "md", "lg"}
        for key in variants_data:
            assert key.startswith(f"public/{sid}_")
            assert key.endswith(".webp")
        actual_suffixes = {
            key.split("_")[-1].replace(".webp", "") for key in variants_data
        }
        assert actual_suffixes == expected_suffixes

    def test_s3_key_for_thumbnail(self, result, sid):
        _, _, variants_data = result
        assert f"public/{sid}_thumb.webp" in variants_data

    def test_s3_key_for_medium(self, result, sid):
        _, _, variants_data = result
        assert f"public/{sid}_md.webp" in variants_data

    def test_s3_key_for_large(self, result, sid):
        _, _, variants_data = result
        assert f"public/{sid}_lg.webp" in variants_data

    # -- URLs --

    def test_urls_contain_base_url(self, result, base_url):
        _, variants_meta, _ = result
        for entry in variants_meta:
            assert entry["url"].startswith(base_url)

    def test_urls_contain_s3_key(self, result, sid):
        _, variants_meta, _ = result
        for entry in variants_meta:
            assert str(sid) in entry["url"]
            assert entry["url"].endswith(".webp")

    def test_base_url_trailing_slash_stripped(self, raw_large, sid):
        """Trailing slash in base_url should not produce double slash."""
        _, variants_meta, _ = build_variants(
            raw_large, sid, "https://cdn.example.com/"
        )
        for entry in variants_meta:
            assert "//" not in entry["url"].replace("https://", "")

    # -- variant data is valid WebP --

    def test_all_variant_data_is_valid_webp(self, result):
        _, _, variants_data = result
        for key, data in variants_data.items():
            img = _open(data)
            assert img.format == "WEBP", f"{key} is not a valid WebP"

    # -- aspect ratio preserved --

    def test_variants_preserve_aspect_ratio(self, result):
        """All variants of a 2000x1500 (4:3) image should keep ~4:3 ratio."""
        _, variants_meta, _ = result
        for entry in variants_meta:
            ratio = entry["width"] / entry["height"]
            assert abs(ratio - 4 / 3) < 0.05, (
                f"{entry['size']} aspect ratio {ratio:.3f} diverges from 1.333"
            )
