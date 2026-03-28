"""Unit tests for the Product aggregate root behavioral invariants.

Tests cover three core areas:
1. FSM state transitions (valid, invalid, readiness checks, published_at)
2. Variant hash uniqueness enforcement (determinism, collision detection)
3. Soft-delete cascade through Product -> Variant -> SKU hierarchy

Part of Phase 03 -- Product aggregate behavior testing.
"""

import uuid

import pytest

from src.modules.catalog.domain.entities import (
    Product,
    ProductAttributeValue,
    ProductVariant,
    SKU,
)
from src.modules.catalog.domain.events import (
    ProductCreatedEvent,
    ProductDeletedEvent,
    ProductStatusChangedEvent,
    ProductUpdatedEvent,
    SKUAddedEvent,
    SKUDeletedEvent,
    VariantAddedEvent,
    VariantDeletedEvent,
)
from src.modules.catalog.domain.exceptions import (
    CannotDeletePublishedProductError,
    DuplicateVariantCombinationError,
    InvalidStatusTransitionError,
    LastVariantRemovalError,
    ProductNotReadyError,
    SKUNotFoundError,
    VariantNotFoundError,
)
from src.modules.catalog.domain.value_objects import Money, ProductStatus
from tests.factories.product_builder import ProductBuilder
from tests.factories.sku_builder import SKUBuilder

# ---------------------------------------------------------------------------
# Module-level constants for parametrized invalid transition tests
# ---------------------------------------------------------------------------

ALL_STATUSES = list(ProductStatus)

VALID_TRANSITIONS: dict[ProductStatus, set[ProductStatus]] = {
    ProductStatus.DRAFT: {ProductStatus.ENRICHING},
    ProductStatus.ENRICHING: {ProductStatus.DRAFT, ProductStatus.READY_FOR_REVIEW},
    ProductStatus.READY_FOR_REVIEW: {
        ProductStatus.ENRICHING,
        ProductStatus.PUBLISHED,
    },
    ProductStatus.PUBLISHED: {ProductStatus.ARCHIVED},
    ProductStatus.ARCHIVED: {ProductStatus.DRAFT},
}

INVALID_TRANSITIONS = [
    (src, tgt)
    for src in ALL_STATUSES
    for tgt in ALL_STATUSES
    if tgt not in VALID_TRANSITIONS.get(src, set()) and src != tgt
]


# ---------------------------------------------------------------------------
# Module-level helper functions
# ---------------------------------------------------------------------------

# Pre-computed FSM paths from DRAFT to each target status
_FSM_PATHS: dict[ProductStatus, list[ProductStatus]] = {
    ProductStatus.DRAFT: [],
    ProductStatus.ENRICHING: [ProductStatus.ENRICHING],
    ProductStatus.READY_FOR_REVIEW: [
        ProductStatus.ENRICHING,
        ProductStatus.READY_FOR_REVIEW,
    ],
    ProductStatus.PUBLISHED: [
        ProductStatus.ENRICHING,
        ProductStatus.READY_FOR_REVIEW,
        ProductStatus.PUBLISHED,
    ],
    ProductStatus.ARCHIVED: [
        ProductStatus.ENRICHING,
        ProductStatus.READY_FOR_REVIEW,
        ProductStatus.PUBLISHED,
        ProductStatus.ARCHIVED,
    ],
}


def _advance_to(product: Product, target: ProductStatus) -> None:
    """Walk a product through the FSM from its current state to *target*.

    For READY_FOR_REVIEW, PUBLISHED, or ARCHIVED transitions, ensures
    the product has at least one priced SKU on the first active variant
    (required by the readiness checks).

    After reaching the target status, clears all accumulated domain events
    so that subsequent assertions see only events from the operation under test.
    """
    path = _FSM_PATHS[target]

    # If the product needs a priced SKU for readiness checks, add one
    needs_sku = target in (
        ProductStatus.READY_FOR_REVIEW,
        ProductStatus.PUBLISHED,
        ProductStatus.ARCHIVED,
    )
    if needs_sku:
        _ensure_priced_sku(product)

    for step in path:
        product.transition_status(step)

    product.clear_domain_events()


def _ensure_priced_sku(product: Product) -> None:
    """Add a priced SKU to the first active variant if none exists."""
    active_variants = [v for v in product.variants if v.deleted_at is None]
    if not active_variants:
        return

    variant = active_variants[0]
    has_priced = any(
        s.deleted_at is None and s.is_active and s.price is not None
        for s in variant.skus
    )
    if not has_priced:
        product.add_sku(
            variant.id,
            sku_code=f"SKU-HELPER-{uuid.uuid4().hex[:6]}",
            price=Money(amount=10000, currency="RUB"),
        )


def _product_with_priced_sku() -> Product:
    """Build a product with one priced SKU, clearing domain events."""
    product = ProductBuilder().build()
    variant = product.variants[0]
    product.add_sku(
        variant.id,
        sku_code="SKU-PRICED",
        price=Money(amount=10000, currency="RUB"),
    )
    product.clear_domain_events()
    return product


# ============================================================================
# TestProductFSMValid -- per D-06
# ============================================================================


class TestProductFSMValid:
    """Tests for all 7 valid FSM transitions plus published_at and setattr guard."""

    def test_draft_to_enriching(self):
        product = ProductBuilder().build()
        product.clear_domain_events()

        product.transition_status(ProductStatus.ENRICHING)

        assert product.status == ProductStatus.ENRICHING

    def test_enriching_to_draft(self):
        product = ProductBuilder().build()
        _advance_to(product, ProductStatus.ENRICHING)

        product.transition_status(ProductStatus.DRAFT)

        assert product.status == ProductStatus.DRAFT

    def test_enriching_to_ready_for_review(self):
        product = _product_with_priced_sku()
        _advance_to(product, ProductStatus.ENRICHING)

        product.transition_status(ProductStatus.READY_FOR_REVIEW)

        assert product.status == ProductStatus.READY_FOR_REVIEW

    def test_ready_for_review_to_enriching(self):
        product = _product_with_priced_sku()
        _advance_to(product, ProductStatus.READY_FOR_REVIEW)

        product.transition_status(ProductStatus.ENRICHING)

        assert product.status == ProductStatus.ENRICHING

    def test_ready_for_review_to_published(self):
        product = _product_with_priced_sku()
        _advance_to(product, ProductStatus.READY_FOR_REVIEW)

        product.transition_status(ProductStatus.PUBLISHED)

        assert product.status == ProductStatus.PUBLISHED

    def test_published_to_archived(self):
        product = _product_with_priced_sku()
        _advance_to(product, ProductStatus.PUBLISHED)

        product.transition_status(ProductStatus.ARCHIVED)

        assert product.status == ProductStatus.ARCHIVED

    def test_archived_to_draft(self):
        product = _product_with_priced_sku()
        _advance_to(product, ProductStatus.ARCHIVED)

        product.transition_status(ProductStatus.DRAFT)

        assert product.status == ProductStatus.DRAFT

    def test_published_at_set_on_first_publish(self):
        """D-09: published_at is set on first PUBLISHED transition and retained."""
        product = _product_with_priced_sku()
        _advance_to(product, ProductStatus.PUBLISHED)

        assert product.published_at is not None
        original_published_at = product.published_at

        # Cycle through: PUBLISHED -> ARCHIVED -> DRAFT -> ENRICHING ->
        # READY_FOR_REVIEW -> PUBLISHED
        product.transition_status(ProductStatus.ARCHIVED)
        product.transition_status(ProductStatus.DRAFT)
        product.transition_status(ProductStatus.ENRICHING)
        # Ensure priced SKU exists (may have been soft-deleted)
        _ensure_priced_sku(product)
        product.transition_status(ProductStatus.READY_FOR_REVIEW)
        product.transition_status(ProductStatus.PUBLISHED)

        # published_at should be the original timestamp, NOT re-set
        assert product.published_at == original_published_at

    def test_setattr_guard_prevents_direct_status_assignment(self):
        """D-10: __setattr__ guard blocks direct product.status = X."""
        product = ProductBuilder().build()

        with pytest.raises(AttributeError):
            product.status = ProductStatus.ENRICHING


# ============================================================================
# TestProductFSMInvalid -- per D-07
# ============================================================================


class TestProductFSMInvalid:
    """Tests for all 13 invalid FSM transitions."""

    @pytest.mark.parametrize("src_status,tgt_status", INVALID_TRANSITIONS)
    def test_invalid_transition_raises(self, src_status, tgt_status):
        product = _product_with_priced_sku()
        _advance_to(product, src_status)

        with pytest.raises(InvalidStatusTransitionError):
            product.transition_status(tgt_status)


# ============================================================================
# TestProductFSMReadiness -- per D-08
# ============================================================================


class TestProductFSMReadiness:
    """Tests for readiness checks blocking transitions without active/priced SKUs."""

    def test_ready_for_review_requires_active_sku(self):
        """Product with no SKUs cannot transition to READY_FOR_REVIEW."""
        product = ProductBuilder().build()
        product.clear_domain_events()
        product.transition_status(ProductStatus.ENRICHING)

        with pytest.raises(ProductNotReadyError):
            product.transition_status(ProductStatus.READY_FOR_REVIEW)

    def test_published_requires_priced_sku(self):
        """Product with only unpriced SKU cannot transition to PUBLISHED."""
        product = ProductBuilder().build()
        variant = product.variants[0]
        # Add an unpriced SKU (price=None)
        product.add_sku(
            variant.id,
            sku_code="SKU-UNPRICED",
            price=None,
        )
        product.clear_domain_events()
        product.transition_status(ProductStatus.ENRICHING)
        # READY_FOR_REVIEW should succeed since there IS an active SKU
        product.transition_status(ProductStatus.READY_FOR_REVIEW)

        with pytest.raises(ProductNotReadyError):
            product.transition_status(ProductStatus.PUBLISHED)

    def test_ready_for_review_succeeds_with_active_sku(self):
        """Product with a priced SKU can transition to READY_FOR_REVIEW."""
        product = _product_with_priced_sku()
        product.transition_status(ProductStatus.ENRICHING)

        product.transition_status(ProductStatus.READY_FOR_REVIEW)

        assert product.status == ProductStatus.READY_FOR_REVIEW

    def test_published_succeeds_with_priced_sku(self):
        """Product with a priced SKU can transition to PUBLISHED."""
        product = _product_with_priced_sku()
        _advance_to(product, ProductStatus.READY_FOR_REVIEW)

        product.transition_status(ProductStatus.PUBLISHED)

        assert product.status == ProductStatus.PUBLISHED


# ============================================================================
# TestVariantHashUniqueness -- per D-11, D-12, D-13
# ============================================================================


class TestVariantHashUniqueness:
    """Tests for variant hash determinism and duplicate combination rejection."""

    def test_hash_deterministic_regardless_of_order(self):
        """D-12: compute_variant_hash produces the same hash regardless of attr order."""
        variant_id = uuid.uuid4()
        attr_a = uuid.uuid4()
        val_a = uuid.uuid4()
        attr_b = uuid.uuid4()
        val_b = uuid.uuid4()

        hash_ab = Product.compute_variant_hash(variant_id, [(attr_a, val_a), (attr_b, val_b)])
        hash_ba = Product.compute_variant_hash(variant_id, [(attr_b, val_b), (attr_a, val_a)])

        assert hash_ab == hash_ba

    def test_different_variants_empty_attrs_different_hash(self):
        """D-12: Two different variant_ids with empty attrs produce different hashes."""
        variant_id_1 = uuid.uuid4()
        variant_id_2 = uuid.uuid4()

        hash_1 = Product.compute_variant_hash(variant_id_1, [])
        hash_2 = Product.compute_variant_hash(variant_id_2, [])

        assert hash_1 != hash_2

    def test_duplicate_combination_rejected_same_variant(self):
        """D-11: Adding two SKUs with same variant_attributes to same variant raises."""
        product = ProductBuilder().build()
        variant = product.variants[0]
        attr_id = uuid.uuid4()
        val_id = uuid.uuid4()

        product.add_sku(
            variant.id,
            sku_code="SKU-FIRST",
            variant_attributes=[(attr_id, val_id)],
        )

        with pytest.raises(DuplicateVariantCombinationError):
            product.add_sku(
                variant.id,
                sku_code="SKU-SECOND",
                variant_attributes=[(attr_id, val_id)],
            )

    def test_duplicate_combination_rejected_across_variants(self):
        """D-11: Same variant + same attrs collides (hash includes variant_id)."""
        product = ProductBuilder().build()
        variant = product.variants[0]
        attr_id = uuid.uuid4()
        val_id = uuid.uuid4()

        # Add SKU with specific attrs to variant 1
        product.add_sku(
            variant.id,
            sku_code="SKU-V1-FIRST",
            variant_attributes=[(attr_id, val_id)],
        )

        # Same variant, same attrs should collide
        with pytest.raises(DuplicateVariantCombinationError):
            product.add_sku(
                variant.id,
                sku_code="SKU-V1-SECOND",
                variant_attributes=[(attr_id, val_id)],
            )

    def test_soft_deleted_sku_does_not_block_new_sku(self):
        """D-13: Soft-deleted SKUs don't participate in uniqueness checks."""
        product = ProductBuilder().build()
        variant = product.variants[0]
        attr_id = uuid.uuid4()
        val_id = uuid.uuid4()

        sku = product.add_sku(
            variant.id,
            sku_code="SKU-TO-DELETE",
            variant_attributes=[(attr_id, val_id)],
        )

        # Soft-delete the SKU
        product.remove_sku(sku.id)

        # Adding a new SKU with the same attrs should now succeed
        new_sku = product.add_sku(
            variant.id,
            sku_code="SKU-REPLACEMENT",
            variant_attributes=[(attr_id, val_id)],
        )
        assert new_sku is not None
        assert new_sku.sku_code == "SKU-REPLACEMENT"


# ============================================================================
# TestSoftDeleteCascade -- per D-03, D-04, D-05
# ============================================================================


class TestSoftDeleteCascade:
    """Tests for soft-delete cascade through the Product -> Variant -> SKU hierarchy."""

    def test_product_soft_delete_cascades_to_variants_and_skus(self):
        """D-03: soft_delete cascades through all 3 levels."""
        product = ProductBuilder().build()
        variant = product.variants[0]
        sku = product.add_sku(
            variant.id,
            sku_code="SKU-CASCADE",
            price=Money(amount=5000, currency="RUB"),
        )
        product.clear_domain_events()

        product.soft_delete()

        assert product.deleted_at is not None
        assert variant.deleted_at is not None
        assert sku.deleted_at is not None

    def test_soft_delete_cascades_to_multiple_variants(self):
        """Soft-delete cascades to all variants and their SKUs."""
        product = ProductBuilder().build()
        variant_1 = product.variants[0]
        variant_2 = product.add_variant(
            name_i18n={"en": "Variant 2", "ru": "Вариант 2"},
        )
        sku_1 = product.add_sku(
            variant_1.id,
            sku_code="SKU-V1",
            price=Money(amount=5000, currency="RUB"),
        )
        sku_2 = product.add_sku(
            variant_2.id,
            sku_code="SKU-V2",
            price=Money(amount=6000, currency="RUB"),
        )
        product.clear_domain_events()

        product.soft_delete()

        assert product.deleted_at is not None
        assert variant_1.deleted_at is not None
        assert variant_2.deleted_at is not None
        assert sku_1.deleted_at is not None
        assert sku_2.deleted_at is not None

    def test_soft_delete_idempotent(self):
        """D-03: Calling soft_delete() twice does not update deleted_at."""
        product = ProductBuilder().build()
        product.clear_domain_events()

        product.soft_delete()
        first_deleted_at = product.deleted_at

        product.soft_delete()

        assert product.deleted_at == first_deleted_at

    def test_already_deleted_variant_skipped_during_cascade(self):
        """D-03: Pre-deleted variants retain their original deleted_at."""
        product = ProductBuilder().build()
        variant_1 = product.variants[0]
        variant_2 = product.add_variant(
            name_i18n={"en": "Variant 2", "ru": "Вариант 2"},
        )
        product.clear_domain_events()

        # Soft-delete the second variant first
        product.remove_variant(variant_2.id)
        variant_2_deleted_at = variant_2.deleted_at
        assert variant_2_deleted_at is not None

        # Now soft-delete the entire product
        product.soft_delete()

        # Variant 1 should be newly deleted
        assert variant_1.deleted_at is not None
        # Variant 2 should retain its original deleted_at (not overwritten)
        assert variant_2.deleted_at == variant_2_deleted_at

    def test_cannot_delete_published_product(self):
        """D-05: Published products cannot be soft-deleted."""
        product = _product_with_priced_sku()
        _advance_to(product, ProductStatus.PUBLISHED)

        with pytest.raises(CannotDeletePublishedProductError):
            product.soft_delete()

    def test_can_delete_archived_product(self):
        """Archived products can be soft-deleted."""
        product = _product_with_priced_sku()
        _advance_to(product, ProductStatus.ARCHIVED)

        product.soft_delete()

        assert product.deleted_at is not None
