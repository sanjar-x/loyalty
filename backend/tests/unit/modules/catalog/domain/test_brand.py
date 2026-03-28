"""Unit tests for the Brand aggregate root.

Covers Brand.create() factory, update() method, __setattr__ guard,
and validate_deletable() deletion guard. Uses BrandBuilder from Phase 1.
Part of the unit test layer -- no I/O or infrastructure dependencies.
"""

import uuid

import pytest

from src.modules.catalog.domain.entities import Brand
from src.modules.catalog.domain.exceptions import BrandHasProductsError
from tests.factories.brand_builder import BrandBuilder


class TestBrand:
    """Factory method tests for Brand.create() per D-03."""

    def test_create_with_valid_inputs(self):
        brand = BrandBuilder().with_name("Nike").with_slug("nike").build()
        assert brand.name == "Nike"
        assert brand.slug == "nike"
        assert isinstance(brand.id, uuid.UUID)

    def test_create_strips_name_whitespace(self):
        brand = Brand.create(name="  Nike  ", slug="nike")
        assert brand.name == "Nike"

    def test_create_with_logo(self):
        obj_id = uuid.uuid4()
        brand = (
            BrandBuilder()
            .with_logo("https://img.co/logo.png", obj_id)
            .build()
        )
        assert brand.logo_url == "https://img.co/logo.png"
        assert brand.logo_storage_object_id == obj_id

    def test_create_without_logo(self):
        brand = BrandBuilder().build()
        assert brand.logo_url is None
        assert brand.logo_storage_object_id is None

    def test_create_rejects_empty_name(self):
        with pytest.raises(ValueError, match="Brand name must be non-empty"):
            Brand.create(name="", slug="valid")

    def test_create_rejects_blank_name(self):
        with pytest.raises(ValueError, match="Brand name must be non-empty"):
            Brand.create(name="   ", slug="valid")

    def test_create_rejects_invalid_slug(self):
        with pytest.raises(ValueError, match="slug must be non-empty"):
            Brand.create(name="Nike", slug="Bad Slug!")

    def test_create_rejects_empty_slug(self):
        with pytest.raises(ValueError, match="slug must be non-empty"):
            Brand.create(name="Nike", slug="")


class TestBrandUpdate:
    """Update method tests for Brand.update()."""

    def test_update_name(self):
        brand = BrandBuilder().with_name("Nike").with_slug("nike").build()
        brand.update(name="Updated")
        assert brand.name == "Updated"

    def test_update_slug_via_update_method(self):
        brand = BrandBuilder().with_name("Nike").with_slug("nike").build()
        brand.update(slug="new-slug")
        assert brand.slug == "new-slug"

    def test_update_rejects_empty_name(self):
        brand = BrandBuilder().build()
        with pytest.raises(ValueError, match="Brand name must be non-empty"):
            brand.update(name="")

    def test_update_logo_url_to_none_clears_it(self):
        brand = (
            BrandBuilder()
            .with_logo("https://img.co/logo.png", uuid.uuid4())
            .build()
        )
        assert brand.logo_url is not None
        brand.update(logo_url=None)
        assert brand.logo_url is None

    def test_update_logo_url_omitted_keeps_current(self):
        original_url = "https://img.co/logo.png"
        brand = (
            BrandBuilder()
            .with_logo(original_url, uuid.uuid4())
            .build()
        )
        brand.update(name="New Name")
        assert brand.logo_url == original_url


class TestBrandGuard:
    """DDD-01 guard: __setattr__ prevents direct slug mutation."""

    def test_direct_slug_assignment_raises(self):
        brand = BrandBuilder().with_name("Nike").with_slug("nike").build()
        with pytest.raises(
            AttributeError, match="Cannot set 'slug' directly"
        ):
            brand.slug = "hacked"


class TestBrandDeletion:
    """validate_deletable() deletion guard tests."""

    def test_deletable_when_no_products(self):
        brand = BrandBuilder().build()
        brand.validate_deletable(has_products=False)  # no exception

    def test_not_deletable_when_has_products(self):
        brand = BrandBuilder().build()
        with pytest.raises(BrandHasProductsError):
            brand.validate_deletable(has_products=True)
