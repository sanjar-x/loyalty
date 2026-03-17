# tests/unit/modules/catalog/presentation/test_schemas.py
"""Tests for Catalog presentation schema validations."""

import pytest
from pydantic import ValidationError

from src.modules.catalog.presentation.schemas import (
    BrandCreateRequest,
    BrandUpdateRequest,
    CategoryCreateRequest,
    CategoryUpdateRequest,
    LogoMetadataRequest,
)


class TestLogoMetadataRequest:
    def test_valid_logo_metadata(self):
        m = LogoMetadataRequest(filename="logo.png", content_type="image/png")
        assert m.filename == "logo.png"
        assert m.content_type == "image/png"

    def test_filename_max_length_255(self):
        with pytest.raises(ValidationError, match="filename"):
            LogoMetadataRequest(filename="a" * 256, content_type="image/png")

    def test_filename_at_max_length_accepted(self):
        m = LogoMetadataRequest(filename="a" * 255, content_type="image/png")
        assert len(m.filename) == 255

    @pytest.mark.parametrize(
        "mime",
        ["image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml"],
    )
    def test_valid_content_types(self, mime: str):
        m = LogoMetadataRequest(filename="f.ext", content_type=mime)
        assert m.content_type == mime

    @pytest.mark.parametrize(
        "mime",
        ["image/bmp", "application/pdf", "text/plain", "video/mp4", "image/tiff"],
    )
    def test_invalid_content_types_rejected(self, mime: str):
        with pytest.raises(ValidationError, match="content_type"):
            LogoMetadataRequest(filename="f.ext", content_type=mime)


class TestCategoryCreateRequest:
    def test_valid_category(self):
        m = CategoryCreateRequest(name="Sneakers", slug="sneakers")
        assert m.name == "Sneakers"
        assert m.slug == "sneakers"

    def test_name_min_length_2(self):
        with pytest.raises(ValidationError, match="name"):
            CategoryCreateRequest(name="A", slug="valid-slug")

    def test_name_max_length_255(self):
        with pytest.raises(ValidationError, match="name"):
            CategoryCreateRequest(name="A" * 256, slug="valid-slug")

    def test_slug_min_length_3(self):
        with pytest.raises(ValidationError, match="slug"):
            CategoryCreateRequest(name="Valid", slug="ab")

    def test_slug_max_length_255(self):
        with pytest.raises(ValidationError, match="slug"):
            CategoryCreateRequest(name="Valid", slug="a" * 256)

    @pytest.mark.parametrize("slug", ["valid-slug", "abc123", "a-b-c", "test"])
    def test_slug_valid_patterns(self, slug: str):
        m = CategoryCreateRequest(name="Test", slug=slug)
        assert m.slug == slug

    @pytest.mark.parametrize(
        "slug", ["UPPERCASE", "has spaces", "special!char", "under_score", "кириллица"]
    )
    def test_slug_invalid_patterns_rejected(self, slug: str):
        with pytest.raises(ValidationError, match="slug"):
            CategoryCreateRequest(name="Test", slug=slug)


class TestCategoryUpdateRequest:
    def test_at_least_one_field_required(self):
        with pytest.raises(ValidationError, match="At least one field"):
            CategoryUpdateRequest()

    def test_accepts_name_only(self):
        m = CategoryUpdateRequest(name="New Name")
        assert m.name == "New Name"
        assert m.slug is None

    def test_accepts_slug_only(self):
        m = CategoryUpdateRequest(slug="new-slug")
        assert m.slug == "new-slug"


class TestBrandCreateRequest:
    def test_valid_brand(self):
        m = BrandCreateRequest(name="Nike", slug="nike")
        assert m.name == "Nike"

    def test_name_min_length_1(self):
        with pytest.raises(ValidationError, match="name"):
            BrandCreateRequest(name="", slug="valid")

    def test_slug_pattern_rejects_uppercase(self):
        with pytest.raises(ValidationError, match="slug"):
            BrandCreateRequest(name="Nike", slug="Nike")


class TestBrandUpdateRequest:
    def test_at_least_one_field_required(self):
        with pytest.raises(ValidationError, match="At least one field"):
            BrandUpdateRequest()

    def test_accepts_name_only(self):
        m = BrandUpdateRequest(name="Updated")
        assert m.name == "Updated"
