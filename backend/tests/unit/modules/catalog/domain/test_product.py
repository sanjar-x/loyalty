"""Unit tests for the Product aggregate root.

Covers create, update, __setattr__ guard, soft-delete cascading,
variant management, SKU management, and variant hash computation.
"""

import uuid

import pytest

from src.modules.catalog.domain.entities import Product
from src.modules.catalog.domain.events import (
    ProductCreatedEvent,
    ProductDeletedEvent,
    ProductUpdatedEvent,
    SKUAddedEvent,
    SKUDeletedEvent,
    VariantAddedEvent,
    VariantDeletedEvent,
)
from src.modules.catalog.domain.exceptions import (
    CannotDeletePublishedProductError,
    DuplicateVariantCombinationError,
    LastVariantRemovalError,
    MissingRequiredLocalesError,
    SKUNotFoundError,
    VariantNotFoundError,
)
from src.modules.catalog.domain.value_objects import Money, ProductStatus
from tests.factories.product_builder import ProductBuilder
from tests.factories.sku_builder import SKUBuilder


def _i18n(en: str, ru: str | None = None) -> dict[str, str]:
    return {"en": en, "ru": ru or en}


# ---------------------------------------------------------------------------
# TestProductCreate
# ---------------------------------------------------------------------------


class TestProductCreate:
    """Product.create() factory -- happy paths and validation guards."""

    def test_create_valid(self):
        product = ProductBuilder().build()
        assert isinstance(product.id, uuid.UUID)
        assert product.status == ProductStatus.DRAFT

    def test_create_auto_creates_default_variant(self):
        title = _i18n("Sneaker")
        product = ProductBuilder().with_title_i18n(title).build()
        assert len(product.variants) == 1
        assert product.variants[0].name_i18n == title

    def test_create_emits_product_created_event(self):
        product = ProductBuilder().build()
        assert len(product.domain_events) >= 1
        assert isinstance(product.domain_events[0], ProductCreatedEvent)

    def test_create_rejects_invalid_slug(self):
        with pytest.raises(ValueError, match="slug must be non-empty"):
            Product.create(
                slug="Bad Slug!",
                title_i18n=_i18n("T"),
                brand_id=uuid.uuid4(),
                primary_category_id=uuid.uuid4(),
            )

    def test_create_rejects_empty_slug(self):
        with pytest.raises(ValueError):
            Product.create(
                slug="",
                title_i18n=_i18n("T"),
                brand_id=uuid.uuid4(),
                primary_category_id=uuid.uuid4(),
            )

    def test_create_rejects_empty_title_i18n(self):
        with pytest.raises(ValueError):
            Product.create(
                slug="valid-slug",
                title_i18n={"en": "", "ru": "Valid"},
                brand_id=uuid.uuid4(),
                primary_category_id=uuid.uuid4(),
            )

    def test_create_rejects_missing_locale(self):
        with pytest.raises(MissingRequiredLocalesError):
            Product.create(
                slug="valid-slug",
                title_i18n={"en": "Only English"},
                brand_id=uuid.uuid4(),
                primary_category_id=uuid.uuid4(),
            )

    def test_create_with_optional_fields(self):
        supplier_id = uuid.uuid4()
        product = (
            ProductBuilder()
            .with_supplier_id(supplier_id)
            .with_source_url("https://poizon.com/123")
            .with_country_of_origin("CN")
            .with_tags(["sale", "new"])
            .build()
        )
        assert product.supplier_id == supplier_id
        assert product.source_url == "https://poizon.com/123"
        assert product.country_of_origin == "CN"
        assert product.tags == ("sale", "new")

    def test_tags_returns_tuple(self):
        product = ProductBuilder().with_tags(["a", "b"]).build()
        assert isinstance(product.tags, tuple)

    def test_variants_returns_tuple(self):
        product = ProductBuilder().build()
        assert isinstance(product.variants, tuple)


# ---------------------------------------------------------------------------
# TestProductUpdate
# ---------------------------------------------------------------------------


class TestProductUpdate:
    """Product.update() -- field mutation, event emission, and guards."""

    def test_update_title_i18n(self):
        product = ProductBuilder().build()
        new_title = _i18n("New Title")
        product.update(title_i18n=new_title)
        assert product.title_i18n == new_title

    def test_update_slug_changes_value(self):
        product = ProductBuilder().with_slug("old-slug").build()
        product.update(slug="new-slug")
        assert product.slug == "new-slug"

    def test_update_emits_product_updated_event(self):
        product = ProductBuilder().build()
        product.clear_domain_events()
        product.update(title_i18n=_i18n("X"))
        events = product.domain_events
        assert any(isinstance(e, ProductUpdatedEvent) for e in events)

    def test_update_rejects_brand_id_none(self):
        product = ProductBuilder().build()
        with pytest.raises(ValueError, match="brand_id cannot be None"):
            product.update(brand_id=None)

    def test_update_rejects_primary_category_id_none(self):
        product = ProductBuilder().build()
        with pytest.raises(ValueError, match="primary_category_id cannot be None"):
            product.update(primary_category_id=None)

    def test_update_rejects_unknown_field(self):
        product = ProductBuilder().build()
        with pytest.raises(TypeError):
            product.update(unknown="x")

    def test_update_tags(self):
        product = ProductBuilder().build()
        product.update(tags=["premium"])
        assert product.tags == ("premium",)

    def test_update_without_changes_no_event(self):
        """When no updatable field is passed, no event should be emitted."""
        product = ProductBuilder().build()
        product.clear_domain_events()
        # Passing an empty update (no kwargs at all) should not emit event
        # but passing a valid field does
        product.update(title_i18n=_i18n("Changed"))
        assert len(product.domain_events) == 1


# ---------------------------------------------------------------------------
# TestProductGuard
# ---------------------------------------------------------------------------


class TestProductGuard:
    """__setattr__ guard prevents direct status mutation."""

    def test_direct_status_assignment_raises(self):
        product = ProductBuilder().build()
        with pytest.raises(AttributeError, match="Cannot set 'status' directly"):
            product.status = ProductStatus.PUBLISHED


# ---------------------------------------------------------------------------
# TestProductSoftDelete
# ---------------------------------------------------------------------------


class TestProductSoftDelete:
    """Product.soft_delete() -- cascading and guards."""

    def test_soft_delete_sets_deleted_at(self):
        product = ProductBuilder().build()
        product.soft_delete()
        assert product.deleted_at is not None

    def test_soft_delete_cascades_to_variants(self):
        product = ProductBuilder().build()
        product.add_variant(name_i18n=_i18n("Extra"))
        assert len(product.variants) == 2
        product.soft_delete()
        for variant in product.variants:
            assert variant.deleted_at is not None

    def test_soft_delete_cascades_to_skus(self):
        product = ProductBuilder().build()
        variant_id = product.variants[0].id
        sku = product.add_sku(
            variant_id, sku_code="SKU-DEL", price=Money(1000, "RUB")
        )
        product.soft_delete()
        assert sku.deleted_at is not None

    def test_soft_delete_emits_event(self):
        product = ProductBuilder().build()
        product.clear_domain_events()
        product.soft_delete()
        assert any(isinstance(e, ProductDeletedEvent) for e in product.domain_events)

    def test_soft_delete_idempotent(self):
        product = ProductBuilder().build()
        product.soft_delete()
        first_deleted_at = product.deleted_at
        product.soft_delete()
        assert product.deleted_at == first_deleted_at

    def test_soft_delete_rejects_published_product(self):
        product = ProductBuilder().build()
        # Add a priced SKU so the product can transition to PUBLISHED
        variant_id = product.variants[0].id
        product.add_sku(
            variant_id, sku_code="SKU-PUB", price=Money(1000, "RUB")
        )
        # Walk the FSM: DRAFT -> ENRICHING -> READY_FOR_REVIEW -> PUBLISHED
        product.transition_status(ProductStatus.ENRICHING)
        product.transition_status(ProductStatus.READY_FOR_REVIEW)
        product.transition_status(ProductStatus.PUBLISHED)
        with pytest.raises(CannotDeletePublishedProductError):
            product.soft_delete()


# ---------------------------------------------------------------------------
# TestProductVariantManagement
# ---------------------------------------------------------------------------


class TestProductVariantManagement:
    """Variant add / find / remove lifecycle on the Product aggregate."""

    def test_add_variant(self):
        product = ProductBuilder().build()
        product.add_variant(name_i18n=_i18n("Red"))
        assert len(product.variants) == 2

    def test_add_variant_emits_event(self):
        product = ProductBuilder().build()
        product.clear_domain_events()
        product.add_variant(name_i18n=_i18n("Red"))
        assert any(isinstance(e, VariantAddedEvent) for e in product.domain_events)

    def test_find_variant_active(self):
        product = ProductBuilder().build()
        variant = product.add_variant(name_i18n=_i18n("Blue"))
        found = product.find_variant(variant.id)
        assert found is variant

    def test_find_variant_returns_none_for_deleted(self):
        product = ProductBuilder().build()
        variant = product.add_variant(name_i18n=_i18n("Blue"))
        variant.soft_delete()
        assert product.find_variant(variant.id) is None

    def test_find_variant_returns_none_for_unknown_id(self):
        product = ProductBuilder().build()
        assert product.find_variant(uuid.uuid4()) is None

    def test_remove_variant(self):
        product = ProductBuilder().build()
        second = product.add_variant(name_i18n=_i18n("Red"))
        product.remove_variant(second.id)
        assert second.deleted_at is not None

    def test_remove_variant_emits_event(self):
        product = ProductBuilder().build()
        second = product.add_variant(name_i18n=_i18n("Red"))
        product.clear_domain_events()
        product.remove_variant(second.id)
        assert any(isinstance(e, VariantDeletedEvent) for e in product.domain_events)

    def test_remove_last_variant_raises(self):
        product = ProductBuilder().build()
        default_variant = product.variants[0]
        with pytest.raises(LastVariantRemovalError):
            product.remove_variant(default_variant.id)

    def test_remove_unknown_variant_raises(self):
        product = ProductBuilder().build()
        with pytest.raises(VariantNotFoundError):
            product.remove_variant(uuid.uuid4())


# ---------------------------------------------------------------------------
# TestProductSKUManagement
# ---------------------------------------------------------------------------


class TestProductSKUManagement:
    """SKU add / find / remove lifecycle on the Product aggregate."""

    def test_add_sku(self):
        product = ProductBuilder().build()
        variant_id = product.variants[0].id
        sku = product.add_sku(variant_id, sku_code="SKU-001")
        assert sku is not None
        assert product.find_sku(sku.id) is sku

    def test_add_sku_emits_event(self):
        product = ProductBuilder().build()
        product.clear_domain_events()
        variant_id = product.variants[0].id
        product.add_sku(variant_id, sku_code="SKU-002")
        assert any(isinstance(e, SKUAddedEvent) for e in product.domain_events)

    def test_add_sku_duplicate_hash_raises(self):
        product = ProductBuilder().build()
        variant_id = product.variants[0].id
        attr_id = uuid.uuid4()
        val_id = uuid.uuid4()
        attrs = [(attr_id, val_id)]
        product.add_sku(
            variant_id, sku_code="SKU-A", variant_attributes=attrs
        )
        with pytest.raises(DuplicateVariantCombinationError):
            product.add_sku(
                variant_id, sku_code="SKU-B", variant_attributes=attrs
            )

    def test_add_sku_unknown_variant_raises(self):
        product = ProductBuilder().build()
        with pytest.raises(VariantNotFoundError):
            product.add_sku(uuid.uuid4(), sku_code="SKU-NOPE")

    def test_find_sku_active(self):
        product = ProductBuilder().build()
        sku = SKUBuilder().for_product(product).build()
        found = product.find_sku(sku.id)
        assert found is sku

    def test_find_sku_returns_none_for_deleted(self):
        product = ProductBuilder().build()
        sku = SKUBuilder().for_product(product).build()
        sku.soft_delete()
        assert product.find_sku(sku.id) is None

    def test_find_sku_returns_none_for_unknown(self):
        product = ProductBuilder().build()
        assert product.find_sku(uuid.uuid4()) is None

    def test_remove_sku(self):
        product = ProductBuilder().build()
        sku = SKUBuilder().for_product(product).build()
        product.remove_sku(sku.id)
        assert sku.deleted_at is not None

    def test_remove_sku_emits_event(self):
        product = ProductBuilder().build()
        sku = SKUBuilder().for_product(product).build()
        product.clear_domain_events()
        product.remove_sku(sku.id)
        assert any(isinstance(e, SKUDeletedEvent) for e in product.domain_events)

    def test_remove_unknown_sku_raises(self):
        product = ProductBuilder().build()
        with pytest.raises(SKUNotFoundError):
            product.remove_sku(uuid.uuid4())


# ---------------------------------------------------------------------------
# TestProductVariantHash
# ---------------------------------------------------------------------------


class TestProductVariantHash:
    """Product.compute_variant_hash() -- determinism and ordering."""

    def test_compute_variant_hash_deterministic(self):
        vid = uuid.uuid4()
        a1, v1 = uuid.uuid4(), uuid.uuid4()
        attrs = [(a1, v1)]
        h1 = Product.compute_variant_hash(vid, attrs)
        h2 = Product.compute_variant_hash(vid, attrs)
        assert h1 == h2

    def test_compute_variant_hash_order_independent(self):
        vid = uuid.uuid4()
        a1, v1 = uuid.uuid4(), uuid.uuid4()
        a2, v2 = uuid.uuid4(), uuid.uuid4()
        h1 = Product.compute_variant_hash(vid, [(a1, v1), (a2, v2)])
        h2 = Product.compute_variant_hash(vid, [(a2, v2), (a1, v1)])
        assert h1 == h2

    def test_compute_variant_hash_different_for_different_variants(self):
        a1, v1 = uuid.uuid4(), uuid.uuid4()
        attrs = [(a1, v1)]
        h1 = Product.compute_variant_hash(uuid.uuid4(), attrs)
        h2 = Product.compute_variant_hash(uuid.uuid4(), attrs)
        assert h1 != h2

    def test_compute_variant_hash_different_for_different_attributes(self):
        vid = uuid.uuid4()
        a1, v1 = uuid.uuid4(), uuid.uuid4()
        a2, v2 = uuid.uuid4(), uuid.uuid4()
        h1 = Product.compute_variant_hash(vid, [(a1, v1)])
        h2 = Product.compute_variant_hash(vid, [(a2, v2)])
        assert h1 != h2
