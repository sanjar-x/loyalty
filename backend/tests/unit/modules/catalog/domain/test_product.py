# tests/unit/modules/catalog/domain/test_product.py
"""Unit tests for the Product aggregate root domain entity (MT-2)."""

import hashlib
import uuid
from datetime import UTC, datetime

import pytest

from src.modules.catalog.domain.entities import SKU, Product
from src.modules.catalog.domain.exceptions import (
    DuplicateVariantCombinationError,
    InvalidStatusTransitionError,
    SKUNotFoundError,
)
from src.modules.catalog.domain.value_objects import Money, ProductStatus
from src.shared.interfaces.entities import AggregateRoot

# ---------------------------------------------------------------------------
# Helpers / Object Mothers
# ---------------------------------------------------------------------------


def make_money(amount: int = 10_000, currency: str = "RUB") -> Money:
    """Create a Money value object for testing."""
    return Money(amount=amount, currency=currency)


def make_product(
    slug: str | None = None,
    title_i18n: dict[str, str] | None = None,
    brand_id: uuid.UUID | None = None,
    primary_category_id: uuid.UUID | None = None,
    **kwargs,
) -> Product:
    """Create a minimal valid Product in DRAFT status."""
    return Product.create(
        slug=slug or f"test-product-{uuid.uuid4().hex[:6]}",
        title_i18n=title_i18n or {"en": "Test Product"},
        brand_id=brand_id or uuid.uuid4(),
        primary_category_id=primary_category_id or uuid.uuid4(),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Product.create() — factory method
# ---------------------------------------------------------------------------


class TestProductCreate:
    """Tests for Product.create() factory method."""

    def test_create_sets_all_required_fields(self) -> None:
        """Nominal case: factory creates a Product with all required fields set."""
        brand_id = uuid.uuid4()
        cat_id = uuid.uuid4()
        product = Product.create(
            slug="nike-air-max",
            title_i18n={"en": "Nike Air Max", "ru": "Найк Эйр Макс"},
            brand_id=brand_id,
            primary_category_id=cat_id,
        )
        assert product.slug == "nike-air-max"
        assert product.title_i18n == {"en": "Nike Air Max", "ru": "Найк Эйр Макс"}
        assert product.brand_id == brand_id
        assert product.primary_category_id == cat_id

    def test_create_sets_status_to_draft(self) -> None:
        """Factory always starts products in DRAFT status."""
        product = make_product()
        assert product.status == ProductStatus.DRAFT

    def test_create_sets_version_to_one(self) -> None:
        """Factory sets initial version to 1 for optimistic locking."""
        product = make_product()
        assert product.version == 1

    def test_create_sets_empty_skus_list(self) -> None:
        """Factory sets skus to empty list — no variants exist yet."""
        product = make_product()
        assert product.skus == []

    def test_create_generates_uuid_if_not_provided(self) -> None:
        """Factory auto-generates UUID when product_id is omitted."""
        product = make_product()
        assert isinstance(product.id, uuid.UUID)

    def test_create_uses_provided_product_id(self) -> None:
        """Factory uses pre-generated UUID when product_id is supplied."""
        custom_id = uuid.uuid4()
        product = make_product(product_id=custom_id)
        assert product.id == custom_id

    def test_create_defaults_description_i18n_to_empty_dict(self) -> None:
        """Factory sets description_i18n to {} when None is passed."""
        product = make_product()
        assert product.description_i18n == {}

    def test_create_uses_provided_description_i18n(self) -> None:
        """Factory stores supplied description_i18n."""
        product = make_product(description_i18n={"en": "A great product"})
        assert product.description_i18n == {"en": "A great product"}

    def test_create_defaults_optional_nullable_fields(self) -> None:
        """Factory sets supplier_id, country_of_origin to None by default."""
        product = make_product()
        assert product.supplier_id is None
        assert product.country_of_origin is None

    def test_create_sets_supplier_id_when_provided(self) -> None:
        """Factory stores supplied supplier_id."""
        supplier_id = uuid.uuid4()
        product = make_product(supplier_id=supplier_id)
        assert product.supplier_id == supplier_id

    def test_create_defaults_tags_to_empty_list(self) -> None:
        """Factory sets tags to [] when not provided."""
        product = make_product()
        assert product.tags == []

    def test_create_stores_provided_tags(self) -> None:
        """Factory stores supplied tags list."""
        product = make_product(tags=["electronics", "shoes"])
        assert product.tags == ["electronics", "shoes"]

    def test_create_sets_deleted_at_to_none(self) -> None:
        """Factory sets deleted_at to None (product is active)."""
        product = make_product()
        assert product.deleted_at is None

    def test_create_sets_published_at_to_none(self) -> None:
        """Factory sets published_at to None (not yet published)."""
        product = make_product()
        assert product.published_at is None

    def test_create_sets_created_at_to_now(self) -> None:
        """Factory sets created_at to a recent UTC timestamp."""
        before = datetime.now(UTC)
        product = make_product()
        after = datetime.now(UTC)
        assert before <= product.created_at <= after

    def test_create_raises_on_empty_title_i18n(self) -> None:
        """Invariant: title_i18n must have at least one language entry."""
        with pytest.raises(ValueError, match="title_i18n must contain at least one language entry"):
            Product.create(
                slug="bad-product",
                title_i18n={},
                brand_id=uuid.uuid4(),
                primary_category_id=uuid.uuid4(),
            )

    def test_create_extends_aggregate_root(self) -> None:
        """Product must be an AggregateRoot — supports domain events."""
        product = make_product()
        assert isinstance(product, AggregateRoot)

    def test_create_skus_list_is_independent_per_instance(self) -> None:
        """Risk: attrs factory=list must produce separate list per instance."""
        p1 = make_product()
        p2 = make_product()
        p1.skus.append(object())  # type: ignore[arg-type]
        assert p2.skus == []

    def test_create_tags_list_is_independent_per_instance(self) -> None:
        """Risk: attrs factory=list must produce separate list per instance."""
        p1 = make_product()
        p2 = make_product()
        p1.tags.append("tag-a")
        assert p2.tags == []


# ---------------------------------------------------------------------------
# Product.update()
# ---------------------------------------------------------------------------


class TestProductUpdate:
    """Tests for Product.update() method."""

    def test_update_title_i18n(self) -> None:
        """update() replaces title_i18n when provided."""
        product = make_product()
        product.update(title_i18n={"en": "New Title", "fr": "Nouveau Titre"})
        assert product.title_i18n == {"en": "New Title", "fr": "Nouveau Titre"}

    def test_update_description_i18n(self) -> None:
        """update() replaces description_i18n when provided."""
        product = make_product()
        product.update(description_i18n={"en": "New description"})
        assert product.description_i18n == {"en": "New description"}

    def test_update_slug(self) -> None:
        """update() replaces slug when provided."""
        product = make_product(slug="original-slug")
        product.update(slug="updated-slug")
        assert product.slug == "updated-slug"

    def test_update_brand_id(self) -> None:
        """update() replaces brand_id when provided."""
        product = make_product()
        new_brand = uuid.uuid4()
        product.update(brand_id=new_brand)
        assert product.brand_id == new_brand

    def test_update_primary_category_id(self) -> None:
        """update() replaces primary_category_id when provided."""
        product = make_product()
        new_cat = uuid.uuid4()
        product.update(primary_category_id=new_cat)
        assert product.primary_category_id == new_cat

    def test_update_tags(self) -> None:
        """update() replaces tags list when provided."""
        product = make_product(tags=["old"])
        product.update(tags=["new", "tags"])
        assert product.tags == ["new", "tags"]

    def test_update_supplier_id_to_value(self) -> None:
        """update() sets supplier_id to a UUID when passed explicitly."""
        product = make_product()
        supplier_id = uuid.uuid4()
        product.update(supplier_id=supplier_id)
        assert product.supplier_id == supplier_id

    def test_update_supplier_id_to_none_clears_it(self) -> None:
        """Sentinel: passing None for supplier_id clears it (not skips it)."""
        supplier_id = uuid.uuid4()
        product = make_product(supplier_id=supplier_id)
        product.update(supplier_id=None)
        assert product.supplier_id is None

    def test_update_supplier_id_omitted_keeps_current(self) -> None:
        """Sentinel: omitting supplier_id leaves the current value intact."""
        supplier_id = uuid.uuid4()
        product = make_product(supplier_id=supplier_id)
        product.update()  # no supplier_id argument
        assert product.supplier_id == supplier_id

    def test_update_country_of_origin_to_value(self) -> None:
        """update() sets country_of_origin when provided."""
        product = make_product()
        product.update(country_of_origin="US")
        assert product.country_of_origin == "US"

    def test_update_country_of_origin_to_none_clears_it(self) -> None:
        """Sentinel: passing None for country_of_origin clears it."""
        product = make_product(country_of_origin="DE")
        product.update(country_of_origin=None)
        assert product.country_of_origin is None

    def test_update_country_of_origin_omitted_keeps_current(self) -> None:
        """Sentinel: omitting country_of_origin leaves current value intact."""
        product = make_product(country_of_origin="FR")
        product.update()
        assert product.country_of_origin == "FR"

    def test_update_sets_updated_at(self) -> None:
        """update() advances updated_at to current UTC time."""
        product = make_product()
        before = datetime.now(UTC)
        product.update(slug="new-slug")
        after = datetime.now(UTC)
        assert before <= product.updated_at <= after

    def test_update_with_no_args_only_touches_updated_at(self) -> None:
        """update() with no kwargs sets updated_at but leaves all other fields."""
        product = make_product(slug="original", title_i18n={"en": "Title"})
        original_slug = product.slug
        original_title = product.title_i18n.copy()
        before = datetime.now(UTC)
        product.update()
        after = datetime.now(UTC)
        assert product.slug == original_slug
        assert product.title_i18n == original_title
        assert before <= product.updated_at <= after

    def test_update_raises_on_empty_title_i18n(self) -> None:
        """Validation: update() rejects empty title_i18n dict."""
        product = make_product()
        with pytest.raises(ValueError, match="title_i18n must contain at least one language entry"):
            product.update(title_i18n={})


# ---------------------------------------------------------------------------
# Product.soft_delete()
# ---------------------------------------------------------------------------


class TestProductSoftDelete:
    """Tests for Product.soft_delete() method."""

    def test_soft_delete_sets_deleted_at(self) -> None:
        """soft_delete() sets deleted_at to current UTC timestamp."""
        product = make_product()
        assert product.deleted_at is None
        before = datetime.now(UTC)
        product.soft_delete()
        after = datetime.now(UTC)
        assert product.deleted_at is not None
        assert before <= product.deleted_at <= after

    def test_soft_delete_sets_updated_at(self) -> None:
        """soft_delete() also advances updated_at."""
        product = make_product()
        before = datetime.now(UTC)
        product.soft_delete()
        after = datetime.now(UTC)
        assert before <= product.updated_at <= after

    def test_soft_delete_does_not_remove_product(self) -> None:
        """soft_delete() is non-destructive — product still accessible."""
        product = make_product(slug="keep-me")
        product.soft_delete()
        assert product.slug == "keep-me"

    def test_soft_delete_preserves_skus(self) -> None:
        """soft_delete() on Product does not cascade to SKUs."""
        product = make_product()
        product.add_sku(sku_code="SKU-001", price=make_money())
        product.soft_delete()
        assert len(product.skus) == 1
        assert product.skus[0].deleted_at is None


# ---------------------------------------------------------------------------
# Product.transition_status() — FSM
# ---------------------------------------------------------------------------


class TestProductTransitionStatus:
    """Tests for the Product status FSM (transition_status)."""

    # --- Valid transitions ---

    def test_draft_to_enriching(self) -> None:
        """Valid: DRAFT -> ENRICHING."""
        product = make_product()
        assert product.status == ProductStatus.DRAFT
        product.transition_status(ProductStatus.ENRICHING)
        assert product.status == ProductStatus.ENRICHING

    def test_enriching_to_draft(self) -> None:
        """Valid: ENRICHING -> DRAFT."""
        product = make_product()
        product.transition_status(ProductStatus.ENRICHING)
        product.transition_status(ProductStatus.DRAFT)
        assert product.status == ProductStatus.DRAFT

    def test_enriching_to_ready_for_review(self) -> None:
        """Valid: ENRICHING -> READY_FOR_REVIEW."""
        product = make_product()
        product.transition_status(ProductStatus.ENRICHING)
        product.transition_status(ProductStatus.READY_FOR_REVIEW)
        assert product.status == ProductStatus.READY_FOR_REVIEW

    def test_ready_for_review_to_enriching(self) -> None:
        """Valid: READY_FOR_REVIEW -> ENRICHING (back for more work)."""
        product = make_product()
        product.transition_status(ProductStatus.ENRICHING)
        product.transition_status(ProductStatus.READY_FOR_REVIEW)
        product.transition_status(ProductStatus.ENRICHING)
        assert product.status == ProductStatus.ENRICHING

    def test_ready_for_review_to_published(self) -> None:
        """Valid: READY_FOR_REVIEW -> PUBLISHED."""
        product = make_product()
        product.transition_status(ProductStatus.ENRICHING)
        product.transition_status(ProductStatus.READY_FOR_REVIEW)
        product.transition_status(ProductStatus.PUBLISHED)
        assert product.status == ProductStatus.PUBLISHED

    def test_published_to_archived(self) -> None:
        """Valid: PUBLISHED -> ARCHIVED."""
        product = make_product()
        product.transition_status(ProductStatus.ENRICHING)
        product.transition_status(ProductStatus.READY_FOR_REVIEW)
        product.transition_status(ProductStatus.PUBLISHED)
        product.transition_status(ProductStatus.ARCHIVED)
        assert product.status == ProductStatus.ARCHIVED

    def test_archived_to_draft(self) -> None:
        """Valid: ARCHIVED -> DRAFT (reactivation)."""
        product = make_product()
        product.transition_status(ProductStatus.ENRICHING)
        product.transition_status(ProductStatus.READY_FOR_REVIEW)
        product.transition_status(ProductStatus.PUBLISHED)
        product.transition_status(ProductStatus.ARCHIVED)
        product.transition_status(ProductStatus.DRAFT)
        assert product.status == ProductStatus.DRAFT

    # --- Transition sets published_at ---

    def test_published_transition_sets_published_at(self) -> None:
        """Transition to PUBLISHED sets published_at to current UTC time."""
        product = make_product()
        product.transition_status(ProductStatus.ENRICHING)
        product.transition_status(ProductStatus.READY_FOR_REVIEW)
        assert product.published_at is None
        before = datetime.now(UTC)
        product.transition_status(ProductStatus.PUBLISHED)
        after = datetime.now(UTC)
        assert product.published_at is not None
        assert before <= product.published_at <= after

    def test_non_published_transition_does_not_set_published_at(self) -> None:
        """Transition to non-PUBLISHED status does NOT set published_at."""
        product = make_product()
        product.transition_status(ProductStatus.ENRICHING)
        assert product.published_at is None

    def test_valid_transition_sets_updated_at(self) -> None:
        """Each successful transition advances updated_at."""
        product = make_product()
        before = datetime.now(UTC)
        product.transition_status(ProductStatus.ENRICHING)
        after = datetime.now(UTC)
        assert before <= product.updated_at <= after

    # --- Invalid transitions ---

    def test_draft_to_published_raises(self) -> None:
        """Invalid: DRAFT -> PUBLISHED must raise (skips FSM steps)."""
        product = make_product()
        with pytest.raises(InvalidStatusTransitionError):
            product.transition_status(ProductStatus.PUBLISHED)

    def test_draft_to_ready_for_review_raises(self) -> None:
        """Invalid: DRAFT -> READY_FOR_REVIEW must raise."""
        product = make_product()
        with pytest.raises(InvalidStatusTransitionError):
            product.transition_status(ProductStatus.READY_FOR_REVIEW)

    def test_draft_to_archived_raises(self) -> None:
        """Invalid: DRAFT -> ARCHIVED must raise."""
        product = make_product()
        with pytest.raises(InvalidStatusTransitionError):
            product.transition_status(ProductStatus.ARCHIVED)

    def test_draft_to_draft_raises(self) -> None:
        """Invalid: self-transition DRAFT -> DRAFT must raise."""
        product = make_product()
        with pytest.raises(InvalidStatusTransitionError):
            product.transition_status(ProductStatus.DRAFT)

    def test_published_to_draft_raises(self) -> None:
        """Invalid: PUBLISHED -> DRAFT must raise (no revert without archiving)."""
        product = make_product()
        product.transition_status(ProductStatus.ENRICHING)
        product.transition_status(ProductStatus.READY_FOR_REVIEW)
        product.transition_status(ProductStatus.PUBLISHED)
        with pytest.raises(InvalidStatusTransitionError):
            product.transition_status(ProductStatus.DRAFT)

    def test_published_to_enriching_raises(self) -> None:
        """Invalid: PUBLISHED -> ENRICHING must raise."""
        product = make_product()
        product.transition_status(ProductStatus.ENRICHING)
        product.transition_status(ProductStatus.READY_FOR_REVIEW)
        product.transition_status(ProductStatus.PUBLISHED)
        with pytest.raises(InvalidStatusTransitionError):
            product.transition_status(ProductStatus.ENRICHING)

    def test_archived_to_enriching_raises(self) -> None:
        """Invalid: ARCHIVED -> ENRICHING must raise (must go via DRAFT first)."""
        product = make_product()
        product.transition_status(ProductStatus.ENRICHING)
        product.transition_status(ProductStatus.READY_FOR_REVIEW)
        product.transition_status(ProductStatus.PUBLISHED)
        product.transition_status(ProductStatus.ARCHIVED)
        with pytest.raises(InvalidStatusTransitionError):
            product.transition_status(ProductStatus.ENRICHING)

    def test_invalid_transition_preserves_current_status(self) -> None:
        """After failed transition the status must remain unchanged."""
        product = make_product()
        assert product.status == ProductStatus.DRAFT
        with pytest.raises(InvalidStatusTransitionError):
            product.transition_status(ProductStatus.PUBLISHED)
        assert product.status == ProductStatus.DRAFT


# ---------------------------------------------------------------------------
# Product.add_sku()
# ---------------------------------------------------------------------------


class TestProductAddSku:
    """Tests for Product.add_sku() — SKU creation and variant hash uniqueness."""

    def test_add_sku_returns_sku_instance(self) -> None:
        """add_sku() returns the newly created SKU."""
        product = make_product()
        sku = product.add_sku(sku_code="SKU-001", price=make_money())
        assert isinstance(sku, SKU)

    def test_add_sku_appends_to_skus_list(self) -> None:
        """add_sku() appends the new SKU to product.skus."""
        product = make_product()
        sku = product.add_sku(sku_code="SKU-001", price=make_money())
        assert sku in product.skus
        assert len(product.skus) == 1

    def test_add_sku_sets_correct_product_id(self) -> None:
        """add_sku() wires product_id FK on the new SKU."""
        product = make_product()
        sku = product.add_sku(sku_code="SKU-001", price=make_money())
        assert sku.product_id == product.id

    def test_add_sku_sets_sku_code(self) -> None:
        """add_sku() stores the supplied sku_code."""
        product = make_product()
        sku = product.add_sku(sku_code="MYCODE-42", price=make_money())
        assert sku.sku_code == "MYCODE-42"

    def test_add_sku_stores_price(self) -> None:
        """add_sku() stores the price Money VO."""
        product = make_product()
        price = Money(amount=5000, currency="USD")
        sku = product.add_sku(sku_code="SKU-001", price=price)
        assert sku.price == price

    def test_add_sku_defaults_is_active_to_true(self) -> None:
        """add_sku() creates active SKU by default."""
        product = make_product()
        sku = product.add_sku(sku_code="SKU-001", price=make_money())
        assert sku.is_active is True

    def test_add_sku_respects_is_active_false(self) -> None:
        """add_sku() creates inactive SKU when is_active=False."""
        product = make_product()
        sku = product.add_sku(sku_code="SKU-001", price=make_money(), is_active=False)
        assert sku.is_active is False

    def test_add_sku_generates_uuid_for_sku(self) -> None:
        """add_sku() gives the new SKU a UUID id."""
        product = make_product()
        sku = product.add_sku(sku_code="SKU-001", price=make_money())
        assert isinstance(sku.id, uuid.UUID)

    def test_add_sku_sets_updated_at_on_product(self) -> None:
        """add_sku() advances product.updated_at."""
        product = make_product()
        before = datetime.now(UTC)
        product.add_sku(sku_code="SKU-001", price=make_money())
        after = datetime.now(UTC)
        assert before <= product.updated_at <= after

    def test_add_sku_computes_variant_hash(self) -> None:
        """add_sku() computes a non-empty variant_hash via SHA-256."""
        product = make_product()
        attr_id = uuid.uuid4()
        val_id = uuid.uuid4()
        sku = product.add_sku(
            sku_code="SKU-001",
            price=make_money(),
            variant_attributes=[(attr_id, val_id)],
        )
        assert len(sku.variant_hash) == 64  # 64-char hex digest
        assert sku.variant_hash.isalnum()

    def test_add_two_skus_with_different_variants(self) -> None:
        """Two SKUs with distinct variant_attributes both succeed."""
        product = make_product()
        a1, v1 = uuid.uuid4(), uuid.uuid4()
        a2, v2 = uuid.uuid4(), uuid.uuid4()
        sku1 = product.add_sku(
            sku_code="SKU-001",
            price=make_money(),
            variant_attributes=[(a1, v1)],
        )
        sku2 = product.add_sku(
            sku_code="SKU-002",
            price=make_money(),
            variant_attributes=[(a2, v2)],
        )
        assert sku1.variant_hash != sku2.variant_hash
        assert len(product.skus) == 2

    def test_add_sku_duplicate_variant_hash_raises(self) -> None:
        """add_sku() raises when a non-deleted SKU with identical variant_attributes exists."""
        product = make_product()
        attr_id, val_id = uuid.uuid4(), uuid.uuid4()
        product.add_sku(
            sku_code="SKU-001",
            price=make_money(),
            variant_attributes=[(attr_id, val_id)],
        )
        with pytest.raises(DuplicateVariantCombinationError):
            product.add_sku(
                sku_code="SKU-002",
                price=make_money(),
                variant_attributes=[(attr_id, val_id)],
            )

    def test_add_sku_duplicate_allowed_after_soft_delete(self) -> None:
        """A deleted SKU's variant_hash can be reused (soft-deleted = inactive)."""
        product = make_product()
        attr_id, val_id = uuid.uuid4(), uuid.uuid4()
        sku = product.add_sku(
            sku_code="SKU-001",
            price=make_money(),
            variant_attributes=[(attr_id, val_id)],
        )
        product.remove_sku(sku.id)  # soft-delete the first SKU
        # Now the same variant combination should be allowed again
        sku2 = product.add_sku(
            sku_code="SKU-003",
            price=make_money(),
            variant_attributes=[(attr_id, val_id)],
        )
        assert sku2.variant_hash == sku.variant_hash
        assert sku2.deleted_at is None

    def test_add_sku_with_no_variant_attributes_succeeds(self) -> None:
        """add_sku() with empty variant_attributes creates a zero-variant SKU."""
        product = make_product()
        sku = product.add_sku(sku_code="SKU-001", price=make_money())
        assert sku.variant_attributes == []
        assert len(sku.variant_hash) == 64

    def test_add_two_zero_variant_skus_raises_on_second(self) -> None:
        """Two zero-variant SKUs have identical hash — second must raise."""
        product = make_product()
        product.add_sku(sku_code="SKU-001", price=make_money())
        with pytest.raises(DuplicateVariantCombinationError):
            product.add_sku(sku_code="SKU-002", price=make_money())

    def test_add_sku_with_compare_at_price_succeeds(self) -> None:
        """add_sku() stores compare_at_price when it is greater than price."""
        product = make_product()
        price = Money(amount=5000, currency="RUB")
        compare = Money(amount=7000, currency="RUB")
        sku = product.add_sku(
            sku_code="SKU-001",
            price=price,
            compare_at_price=compare,
        )
        assert sku.compare_at_price == compare

    def test_add_sku_with_compare_at_price_equal_raises(self) -> None:
        """add_sku() rejects compare_at_price == price (must be strictly greater)."""
        product = make_product()
        price = Money(amount=5000, currency="RUB")
        with pytest.raises(ValueError):
            product.add_sku(
                sku_code="SKU-001",
                price=price,
                compare_at_price=price,  # equal, not greater
            )

    def test_add_sku_with_compare_at_price_lower_raises(self) -> None:
        """add_sku() rejects compare_at_price < price."""
        product = make_product()
        price = Money(amount=5000, currency="RUB")
        lower = Money(amount=3000, currency="RUB")
        with pytest.raises(ValueError):
            product.add_sku(
                sku_code="SKU-001",
                price=price,
                compare_at_price=lower,
            )


# ---------------------------------------------------------------------------
# Product.find_sku()
# ---------------------------------------------------------------------------


class TestProductFindSku:
    """Tests for Product.find_sku() method."""

    def test_find_sku_returns_existing_sku(self) -> None:
        """find_sku() returns the SKU when it exists and is active."""
        product = make_product()
        sku = product.add_sku(sku_code="SKU-001", price=make_money())
        found = product.find_sku(sku.id)
        assert found is sku

    def test_find_sku_returns_none_for_missing_id(self) -> None:
        """find_sku() returns None when no SKU with that ID exists."""
        product = make_product()
        product.add_sku(sku_code="SKU-001", price=make_money())
        result = product.find_sku(uuid.uuid4())
        assert result is None

    def test_find_sku_returns_none_for_soft_deleted_sku(self) -> None:
        """find_sku() excludes soft-deleted SKUs from results."""
        product = make_product()
        sku = product.add_sku(sku_code="SKU-001", price=make_money())
        sku.soft_delete()
        result = product.find_sku(sku.id)
        assert result is None

    def test_find_sku_with_empty_list_returns_none(self) -> None:
        """find_sku() returns None when skus list is empty."""
        product = make_product()
        result = product.find_sku(uuid.uuid4())
        assert result is None


# ---------------------------------------------------------------------------
# Product.remove_sku()
# ---------------------------------------------------------------------------


class TestProductRemoveSku:
    """Tests for Product.remove_sku() — soft-delete a child SKU."""

    def test_remove_sku_soft_deletes_the_sku(self) -> None:
        """remove_sku() marks the SKU's deleted_at timestamp."""
        product = make_product()
        sku = product.add_sku(sku_code="SKU-001", price=make_money())
        assert sku.deleted_at is None
        product.remove_sku(sku.id)
        assert sku.deleted_at is not None

    def test_remove_sku_sets_product_updated_at(self) -> None:
        """remove_sku() advances product.updated_at."""
        product = make_product()
        sku = product.add_sku(sku_code="SKU-001", price=make_money())
        before = datetime.now(UTC)
        product.remove_sku(sku.id)
        after = datetime.now(UTC)
        assert before <= product.updated_at <= after

    def test_remove_sku_sku_still_in_list(self) -> None:
        """remove_sku() does not physically remove the SKU from skus list."""
        product = make_product()
        sku = product.add_sku(sku_code="SKU-001", price=make_money())
        product.remove_sku(sku.id)
        assert sku in product.skus  # soft-deleted, not physically removed

    def test_remove_sku_not_found_raises(self) -> None:
        """remove_sku() raises when SKU ID does not exist."""
        product = make_product()
        with pytest.raises(SKUNotFoundError):
            product.remove_sku(uuid.uuid4())

    def test_remove_sku_already_deleted_raises(self) -> None:
        """remove_sku() raises when SKU is already soft-deleted (not found)."""
        product = make_product()
        sku = product.add_sku(sku_code="SKU-001", price=make_money())
        product.remove_sku(sku.id)
        with pytest.raises(SKUNotFoundError):
            product.remove_sku(sku.id)  # second removal must fail


# ---------------------------------------------------------------------------
# Product._compute_variant_hash() — determinism
# ---------------------------------------------------------------------------


class TestProductComputeVariantHash:
    """Tests for Product.compute_variant_hash() static method."""

    def test_empty_list_produces_deterministic_hash(self) -> None:
        """Empty variant_attributes with same variant_id produces the same 64-char hash."""
        vid = uuid.uuid4()
        h1 = Product.compute_variant_hash(vid, [])
        h2 = Product.compute_variant_hash(vid, [])
        assert h1 == h2
        assert len(h1) == 64

    def test_different_variant_ids_with_empty_attrs_produce_different_hashes(self) -> None:
        """Different variant_ids with empty attrs must not collide."""
        vid1 = uuid.uuid4()
        vid2 = uuid.uuid4()
        h1 = Product.compute_variant_hash(vid1, [])
        h2 = Product.compute_variant_hash(vid2, [])
        assert h1 != h2

    def test_same_pairs_same_order_produces_same_hash(self) -> None:
        """Identical inputs always yield identical hash (determinism)."""
        vid = uuid.uuid4()
        a, v = uuid.uuid4(), uuid.uuid4()
        h1 = Product.compute_variant_hash(vid, [(a, v)])
        h2 = Product.compute_variant_hash(vid, [(a, v)])
        assert h1 == h2

    def test_same_pairs_different_order_produces_same_hash(self) -> None:
        """Insertion order independence: sorted by attribute_id."""
        vid = uuid.uuid4()
        a1, v1 = uuid.uuid4(), uuid.uuid4()
        a2, v2 = uuid.uuid4(), uuid.uuid4()
        h1 = Product.compute_variant_hash(vid, [(a1, v1), (a2, v2)])
        h2 = Product.compute_variant_hash(vid, [(a2, v2), (a1, v1)])
        assert h1 == h2

    def test_different_attribute_ids_produce_different_hashes(self) -> None:
        """Different inputs must produce different hashes (collision resistance)."""
        vid = uuid.uuid4()
        a1, v = uuid.uuid4(), uuid.uuid4()
        a2 = uuid.uuid4()
        h1 = Product.compute_variant_hash(vid, [(a1, v)])
        h2 = Product.compute_variant_hash(vid, [(a2, v)])
        assert h1 != h2

    def test_different_value_ids_produce_different_hashes(self) -> None:
        """Different value IDs for same attribute must produce different hashes."""
        vid = uuid.uuid4()
        a = uuid.uuid4()
        v1, v2 = uuid.uuid4(), uuid.uuid4()
        h1 = Product.compute_variant_hash(vid, [(a, v1)])
        h2 = Product.compute_variant_hash(vid, [(a, v2)])
        assert h1 != h2

    def test_hash_is_64_char_lowercase_hex(self) -> None:
        """SHA-256 hexdigest is always 64 lowercase hex chars."""
        vid = uuid.uuid4()
        a, v = uuid.uuid4(), uuid.uuid4()
        h = Product.compute_variant_hash(vid, [(a, v)])
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_multiple_pairs_produces_non_empty_hash(self) -> None:
        """Multi-attribute variant produces a valid 64-char hash."""
        vid = uuid.uuid4()
        pairs = [(uuid.uuid4(), uuid.uuid4()) for _ in range(5)]
        h = Product.compute_variant_hash(vid, pairs)
        assert len(h) == 64


# ---------------------------------------------------------------------------
# Optimistic locking — version field
# ---------------------------------------------------------------------------


class TestProductVersionField:
    """Verify version field exists for optimistic locking."""

    def test_version_field_exists(self) -> None:
        """Product.version must be present (managed by repo for optimistic locking)."""
        product = make_product()
        assert hasattr(product, "version")
        assert isinstance(product.version, int)

    def test_version_starts_at_one(self) -> None:
        """Version starts at 1 per plan spec."""
        product = make_product()
        assert product.version == 1
