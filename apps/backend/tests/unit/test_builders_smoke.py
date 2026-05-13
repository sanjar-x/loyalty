# tests/unit/test_builders_smoke.py
"""Smoke tests verifying all builders produce valid entities with sensible defaults.

Pure unit tests -- no database, no I/O. Each test method calls a builder
with zero arguments (defaults only) and asserts the entity is valid.
"""

import re
import uuid

import pytest

from src.modules.catalog.domain.value_objects import (
    AttributeDataType,
    AttributeLevel,
    AttributeUIType,
    MediaRole,
    MediaType,
)
from tests.factories.attribute_builder import (
    AttributeBuilder,
    AttributeValueBuilder,
    ProductAttributeValueBuilder,
)
from tests.factories.attribute_group_builder import AttributeGroupBuilder
from tests.factories.attribute_template_builder import (
    AttributeTemplateBuilder,
    TemplateAttributeBindingBuilder,
)
from tests.factories.brand_builder import BrandBuilder
from tests.factories.media_asset_builder import MediaAssetBuilder
from tests.factories.product_builder import ProductBuilder
from tests.factories.sku_builder import SKUBuilder
from tests.factories.variant_builder import ProductVariantBuilder

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@pytest.mark.unit
class TestBuilderSmoke:
    """Smoke tests for all catalog domain entity builders."""

    # ------------------------------------------------------------------
    # Brand
    # ------------------------------------------------------------------

    def test_brand_builder_defaults(self):
        """BrandBuilder with defaults produces a Brand with valid slug."""
        brand = BrandBuilder().build()
        assert brand.id is not None
        assert isinstance(brand.id, uuid.UUID)
        assert brand.name == "Test Brand"
        assert SLUG_RE.match(brand.slug), f"Invalid slug: {brand.slug}"

    def test_brand_builder_with_overrides(self):
        """BrandBuilder with explicit name and slug."""
        brand = BrandBuilder().with_name("Nike").with_slug("nike").build()
        assert brand.name == "Nike"
        assert brand.slug == "nike"

    # ------------------------------------------------------------------
    # Product
    # ------------------------------------------------------------------

    def test_product_builder_defaults(self):
        """ProductBuilder defaults produce a Product with >= 1 variant."""
        product = ProductBuilder().build()
        assert product.id is not None
        assert isinstance(product.id, uuid.UUID)
        assert SLUG_RE.match(product.slug), f"Invalid slug: {product.slug}"
        assert "en" in product.title_i18n
        assert "ru" in product.title_i18n
        assert len(product.variants) >= 1, (
            "Product.create() should auto-create one default variant"
        )

    def test_product_builder_with_overrides(self):
        """ProductBuilder with explicit brand_id, category_id, slug, etc."""
        brand_id = uuid.uuid4()
        cat_id = uuid.uuid4()
        supplier_id = uuid.uuid4()
        product = (
            ProductBuilder()
            .with_slug("nike-air-max")
            .with_brand_id(brand_id)
            .with_category_id(cat_id)
            .with_supplier_id(supplier_id)
            .with_source_url("https://poizon.com/item/12345")
            .with_country_of_origin("CN")
            .build()
        )
        assert product.slug == "nike-air-max"
        assert product.brand_id == brand_id
        assert product.primary_category_id == cat_id
        assert product.supplier_id == supplier_id
        assert product.source_url == "https://poizon.com/item/12345"
        assert product.country_of_origin == "CN"

    # ------------------------------------------------------------------
    # Attribute
    # ------------------------------------------------------------------

    def test_attribute_builder_defaults(self):
        """AttributeBuilder defaults to STRING / DROPDOWN / dictionary."""
        attr = AttributeBuilder().build()
        assert attr.id is not None
        assert isinstance(attr.id, uuid.UUID)
        assert attr.data_type == AttributeDataType.STRING
        assert attr.ui_type == AttributeUIType.DROPDOWN
        assert attr.is_dictionary is True
        assert attr.level == AttributeLevel.PRODUCT
        assert "en" in attr.name_i18n
        assert "ru" in attr.name_i18n

    def test_attribute_builder_variant_level(self):
        """AttributeBuilder.at_variant_level() sets VARIANT level."""
        attr = AttributeBuilder().at_variant_level().build()
        assert attr.level == AttributeLevel.VARIANT

    # ------------------------------------------------------------------
    # AttributeValue
    # ------------------------------------------------------------------

    def test_attribute_value_builder_defaults(self):
        """AttributeValueBuilder has valid i18n with both ru and en keys."""
        value = AttributeValueBuilder().build()
        assert value.id is not None
        assert isinstance(value.id, uuid.UUID)
        assert "en" in value.value_i18n
        assert "ru" in value.value_i18n
        assert value.is_active is True
        assert value.sort_order == 0

    # ------------------------------------------------------------------
    # ProductAttributeValue
    # ------------------------------------------------------------------

    def test_product_attribute_value_builder_defaults(self):
        """ProductAttributeValueBuilder produces valid PAV."""
        pav = ProductAttributeValueBuilder().build()
        assert pav.id is not None
        assert isinstance(pav.id, uuid.UUID)
        assert isinstance(pav.product_id, uuid.UUID)
        assert isinstance(pav.attribute_id, uuid.UUID)
        assert isinstance(pav.attribute_value_id, uuid.UUID)

    # ------------------------------------------------------------------
    # AttributeGroup
    # ------------------------------------------------------------------

    def test_attribute_group_builder_defaults(self):
        """AttributeGroupBuilder produces valid group."""
        group = AttributeGroupBuilder().build()
        assert group.id is not None
        assert isinstance(group.id, uuid.UUID)
        assert "en" in group.name_i18n
        assert "ru" in group.name_i18n
        assert group.sort_order == 0

    # ------------------------------------------------------------------
    # AttributeTemplate
    # ------------------------------------------------------------------

    def test_attribute_template_builder_defaults(self):
        """AttributeTemplateBuilder produces valid template."""
        template = AttributeTemplateBuilder().build()
        assert template.id is not None
        assert isinstance(template.id, uuid.UUID)
        assert "en" in template.name_i18n
        assert "ru" in template.name_i18n
        assert template.sort_order == 0

    # ------------------------------------------------------------------
    # TemplateAttributeBinding
    # ------------------------------------------------------------------

    def test_template_binding_builder_defaults(self):
        """TemplateAttributeBindingBuilder works with default UUIDs."""
        binding = TemplateAttributeBindingBuilder().build()
        assert binding.id is not None
        assert isinstance(binding.id, uuid.UUID)
        assert isinstance(binding.template_id, uuid.UUID)
        assert isinstance(binding.attribute_id, uuid.UUID)
        assert binding.sort_order == 0

    # ------------------------------------------------------------------
    # SKU (via Product.add_sku)
    # ------------------------------------------------------------------

    def test_sku_builder_defaults(self):
        """SKUBuilder produces valid SKU via product.add_sku()."""
        sku = SKUBuilder().build()
        assert sku.id is not None
        assert isinstance(sku.id, uuid.UUID)
        assert sku.sku_code.startswith("SKU-")
        assert sku.is_active is True
        # SKU was created via Product.add_sku(), so it has a variant_id
        assert isinstance(sku.variant_id, uuid.UUID)
        assert isinstance(sku.product_id, uuid.UUID)

    # ------------------------------------------------------------------
    # ProductVariant
    # ------------------------------------------------------------------

    def test_variant_builder_defaults(self):
        """ProductVariantBuilder produces valid variant via create()."""
        variant = ProductVariantBuilder().build()
        assert variant.id is not None
        assert isinstance(variant.id, uuid.UUID)
        assert "en" in variant.name_i18n
        assert "ru" in variant.name_i18n
        assert variant.sort_order == 0
        assert variant.default_currency == "RUB"

    # ------------------------------------------------------------------
    # MediaAsset
    # ------------------------------------------------------------------

    def test_media_asset_builder_defaults(self):
        """MediaAssetBuilder produces valid asset with IMAGE/GALLERY."""
        asset = MediaAssetBuilder().build()
        assert asset.id is not None
        assert isinstance(asset.id, uuid.UUID)
        assert asset.media_type == MediaType.IMAGE
        assert asset.role == MediaRole.GALLERY
        assert asset.is_external is False
        assert asset.sort_order == 0

    def test_media_asset_builder_external(self):
        """MediaAssetBuilder.as_external() produces asset with is_external=True."""
        url = "https://example.com/img.jpg"
        asset = MediaAssetBuilder().as_external(url).build()
        assert asset.is_external is True
        assert asset.url == url

    # ------------------------------------------------------------------
    # Fluent chaining
    # ------------------------------------------------------------------

    def test_builder_chaining(self):
        """Verify fluent chaining returns the builder for all builders."""
        brand = BrandBuilder().with_name("X").with_slug("x").build()
        assert brand.name == "X"
        assert brand.slug == "x"

        product = (
            ProductBuilder()
            .with_slug("chained-product")
            .with_tags(["tag1", "tag2"])
            .build()
        )
        assert product.slug == "chained-product"
        assert "tag1" in product.tags
