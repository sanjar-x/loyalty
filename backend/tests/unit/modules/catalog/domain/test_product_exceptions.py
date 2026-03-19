# tests/unit/modules/catalog/domain/test_product_exceptions.py
"""Unit tests for the 8 Product/SKU domain exception classes added in MT-4.

Covers:
- Base class (inheritance) for each exception
- Correct error_code string on each exception
- Correct HTTP status_code from the shared base
- Message formatting with injected values
- Details dict populated with correct keys and values
- Integration: Product entity raises the correct exception types via its FSM
  and variant-uniqueness guard (transition_status, add_sku, remove_sku)
"""

import uuid

import pytest

from src.modules.catalog.domain.entities import Product
from src.modules.catalog.domain.exceptions import (
    ConcurrencyError,
    DuplicateProductAttributeError,
    DuplicateVariantCombinationError,
    InvalidStatusTransitionError,
    ProductAttributeValueNotFoundError,
    ProductSlugConflictError,
    SKUCodeConflictError,
    SKUNotFoundError,
)
from src.modules.catalog.domain.value_objects import Money, ProductStatus
from src.shared.exceptions import ConflictError, NotFoundError, UnprocessableEntityError

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_product(**kwargs) -> Product:
    """Create a minimal valid Product in DRAFT status."""
    defaults = dict(
        slug=f"test-product-{uuid.uuid4().hex[:6]}",
        title_i18n={"en": "Test Product"},
        brand_id=uuid.uuid4(),
        primary_category_id=uuid.uuid4(),
    )
    defaults.update(kwargs)
    return Product.create(**defaults)


def _make_money(amount: int = 10_000, currency: str = "RUB") -> Money:
    return Money(amount=amount, currency=currency)


# ===========================================================================
# InvalidStatusTransitionError
# ===========================================================================


class TestInvalidStatusTransitionError:
    """Tests for InvalidStatusTransitionError."""

    def _make(
        self,
        current: ProductStatus = ProductStatus.DRAFT,
        target: ProductStatus = ProductStatus.PUBLISHED,
        allowed: list[ProductStatus] | None = None,
    ) -> InvalidStatusTransitionError:
        return InvalidStatusTransitionError(
            current_status=current,
            target_status=target,
            allowed_transitions=allowed if allowed is not None else [ProductStatus.ENRICHING],
        )

    def test_inherits_from_unprocessable_entity_error(self) -> None:
        """InvalidStatusTransitionError is a subclass of UnprocessableEntityError."""
        exc = self._make()
        assert isinstance(exc, UnprocessableEntityError)

    def test_status_code_is_422(self) -> None:
        """HTTP status code must be 422 (Unprocessable Entity)."""
        exc = self._make()
        assert exc.status_code == 422

    def test_error_code(self) -> None:
        """error_code must be the exact string INVALID_STATUS_TRANSITION."""
        exc = self._make()
        assert exc.error_code == "INVALID_STATUS_TRANSITION"

    def test_message_contains_current_and_target_status(self) -> None:
        """Message must embed current_status.value and target_status.value."""
        exc = self._make(
            current=ProductStatus.ENRICHING,
            target=ProductStatus.ARCHIVED,
        )
        assert "enriching" in exc.message
        assert "archived" in exc.message

    def test_message_format(self) -> None:
        """Message must match the exact template from the architect's plan."""
        exc = self._make(
            current=ProductStatus.DRAFT,
            target=ProductStatus.PUBLISHED,
        )
        assert exc.message == "Cannot transition from 'draft' to 'published'."

    def test_details_current_status(self) -> None:
        """details['current_status'] must be the string .value of current_status."""
        exc = self._make(current=ProductStatus.READY_FOR_REVIEW, target=ProductStatus.DRAFT)
        assert exc.details["current_status"] == "ready_for_review"

    def test_details_target_status(self) -> None:
        """details['target_status'] must be the string .value of target_status."""
        exc = self._make(current=ProductStatus.DRAFT, target=ProductStatus.ARCHIVED)
        assert exc.details["target_status"] == "archived"

    def test_details_allowed_transitions_serialized_as_strings(self) -> None:
        """details['allowed_transitions'] must be a list of .value strings, not enums."""
        allowed = [ProductStatus.DRAFT, ProductStatus.READY_FOR_REVIEW]
        exc = self._make(allowed=allowed)
        assert exc.details["allowed_transitions"] == ["draft", "ready_for_review"]

    def test_details_allowed_transitions_empty_list(self) -> None:
        """Empty allowed_transitions is valid — details list is empty."""
        exc = self._make(allowed=[])
        assert exc.details["allowed_transitions"] == []

    def test_details_keys_complete(self) -> None:
        """Details dict must contain exactly: current_status, target_status, allowed_transitions."""
        exc = self._make()
        assert set(exc.details.keys()) == {"current_status", "target_status", "allowed_transitions"}

    def test_is_exception(self) -> None:
        """Must be raise-able as a standard Python exception."""
        with pytest.raises(InvalidStatusTransitionError):
            raise self._make()


# ===========================================================================
# ProductSlugConflictError
# ===========================================================================


class TestProductSlugConflictError:
    """Tests for ProductSlugConflictError."""

    def _make(self, slug: str = "nike-air-max") -> ProductSlugConflictError:
        return ProductSlugConflictError(slug=slug)

    def test_inherits_from_conflict_error(self) -> None:
        """ProductSlugConflictError is a subclass of ConflictError."""
        exc = self._make()
        assert isinstance(exc, ConflictError)

    def test_status_code_is_409(self) -> None:
        """HTTP status code must be 409 (Conflict)."""
        exc = self._make()
        assert exc.status_code == 409

    def test_error_code(self) -> None:
        """error_code must be PRODUCT_SLUG_CONFLICT."""
        exc = self._make()
        assert exc.error_code == "PRODUCT_SLUG_CONFLICT"

    def test_message_contains_slug(self) -> None:
        """Message must embed the conflicting slug value."""
        exc = self._make(slug="my-unique-product")
        assert "my-unique-product" in exc.message

    def test_message_format(self) -> None:
        """Message must match the exact template."""
        exc = self._make(slug="foo-bar")
        assert exc.message == "Product with slug 'foo-bar' already exists."

    def test_details_slug(self) -> None:
        """details['slug'] must be the conflicting slug string."""
        exc = self._make(slug="conflict-slug")
        assert exc.details["slug"] == "conflict-slug"

    def test_details_keys_complete(self) -> None:
        """Details dict must contain exactly: slug."""
        exc = self._make()
        assert set(exc.details.keys()) == {"slug"}

    @pytest.mark.parametrize("slug", ["a", "a-b-c", "x" * 255])
    def test_various_slug_values(self, slug: str) -> None:
        """Accepts slugs of any length."""
        exc = ProductSlugConflictError(slug=slug)
        assert exc.details["slug"] == slug


# ===========================================================================
# SKUNotFoundError
# ===========================================================================


class TestSKUNotFoundError:
    """Tests for SKUNotFoundError."""

    def _make_with_uuid(self) -> tuple[uuid.UUID, SKUNotFoundError]:
        sku_id = uuid.uuid4()
        return sku_id, SKUNotFoundError(sku_id=sku_id)

    def test_inherits_from_not_found_error(self) -> None:
        """SKUNotFoundError is a subclass of NotFoundError."""
        _, exc = self._make_with_uuid()
        assert isinstance(exc, NotFoundError)

    def test_status_code_is_404(self) -> None:
        """HTTP status code must be 404 (Not Found)."""
        _, exc = self._make_with_uuid()
        assert exc.status_code == 404

    def test_error_code(self) -> None:
        """error_code must be SKU_NOT_FOUND."""
        _, exc = self._make_with_uuid()
        assert exc.error_code == "SKU_NOT_FOUND"

    def test_message_contains_sku_id(self) -> None:
        """Message must embed the sku_id string representation."""
        sku_id = uuid.uuid4()
        exc = SKUNotFoundError(sku_id=sku_id)
        assert str(sku_id) in exc.message

    def test_message_format(self) -> None:
        """Message must match the exact template."""
        sku_id = uuid.uuid4()
        exc = SKUNotFoundError(sku_id=sku_id)
        assert exc.message == f"SKU with ID {sku_id} not found."

    def test_details_sku_id_as_string(self) -> None:
        """details['sku_id'] must be a string representation of the UUID."""
        sku_id = uuid.uuid4()
        exc = SKUNotFoundError(sku_id=sku_id)
        assert exc.details["sku_id"] == str(sku_id)

    def test_accepts_string_sku_id(self) -> None:
        """sku_id parameter can be passed as a plain string."""
        str_id = "some-string-id"
        exc = SKUNotFoundError(sku_id=str_id)
        assert exc.details["sku_id"] == str_id

    def test_details_keys_complete(self) -> None:
        """Details dict must contain exactly: sku_id."""
        _, exc = self._make_with_uuid()
        assert set(exc.details.keys()) == {"sku_id"}


# ===========================================================================
# SKUCodeConflictError
# ===========================================================================


class TestSKUCodeConflictError:
    """Tests for SKUCodeConflictError."""

    def _make(
        self, sku_code: str = "SKU-001", product_id: uuid.UUID | None = None
    ) -> SKUCodeConflictError:
        return SKUCodeConflictError(sku_code=sku_code, product_id=product_id or uuid.uuid4())

    def test_inherits_from_conflict_error(self) -> None:
        """SKUCodeConflictError is a subclass of ConflictError."""
        exc = self._make()
        assert isinstance(exc, ConflictError)

    def test_status_code_is_409(self) -> None:
        """HTTP status code must be 409 (Conflict)."""
        exc = self._make()
        assert exc.status_code == 409

    def test_error_code(self) -> None:
        """error_code must be SKU_CODE_CONFLICT."""
        exc = self._make()
        assert exc.error_code == "SKU_CODE_CONFLICT"

    def test_message_contains_sku_code(self) -> None:
        """Message must embed the conflicting sku_code."""
        exc = self._make(sku_code="XYZ-999")
        assert "XYZ-999" in exc.message

    def test_message_format(self) -> None:
        """Message must match the exact template."""
        product_id = uuid.uuid4()
        exc = SKUCodeConflictError(sku_code="A-1", product_id=product_id)
        assert exc.message == "SKU with code 'A-1' already exists for this product."

    def test_details_sku_code(self) -> None:
        """details['sku_code'] must be the conflicting code string."""
        exc = self._make(sku_code="CODE-42")
        assert exc.details["sku_code"] == "CODE-42"

    def test_details_product_id_as_string(self) -> None:
        """details['product_id'] must be the string representation of the UUID."""
        product_id = uuid.uuid4()
        exc = SKUCodeConflictError(sku_code="X", product_id=product_id)
        assert exc.details["product_id"] == str(product_id)

    def test_details_keys_complete(self) -> None:
        """Details dict must contain exactly: sku_code, product_id."""
        exc = self._make()
        assert set(exc.details.keys()) == {"sku_code", "product_id"}


# ===========================================================================
# DuplicateVariantCombinationError
# ===========================================================================


class TestDuplicateVariantCombinationError:
    """Tests for DuplicateVariantCombinationError."""

    def _make(
        self,
        product_id: uuid.UUID | None = None,
        variant_hash: str = "abc123def456",
    ) -> DuplicateVariantCombinationError:
        return DuplicateVariantCombinationError(
            product_id=product_id or uuid.uuid4(),
            variant_hash=variant_hash,
        )

    def test_inherits_from_conflict_error(self) -> None:
        """DuplicateVariantCombinationError is a subclass of ConflictError."""
        exc = self._make()
        assert isinstance(exc, ConflictError)

    def test_status_code_is_409(self) -> None:
        """HTTP status code must be 409 (Conflict)."""
        exc = self._make()
        assert exc.status_code == 409

    def test_error_code(self) -> None:
        """error_code must be DUPLICATE_VARIANT_COMBINATION."""
        exc = self._make()
        assert exc.error_code == "DUPLICATE_VARIANT_COMBINATION"

    def test_message_is_static(self) -> None:
        """Message must be the static descriptive string."""
        exc = self._make()
        assert exc.message == "A variant with the same attribute combination already exists."

    def test_details_product_id_as_string(self) -> None:
        """details['product_id'] must be the string representation of the UUID."""
        product_id = uuid.uuid4()
        exc = DuplicateVariantCombinationError(product_id=product_id, variant_hash="hash")
        assert exc.details["product_id"] == str(product_id)

    def test_details_variant_hash(self) -> None:
        """details['variant_hash'] must be the hash string passed at construction."""
        exc = self._make(variant_hash="deadbeef1234")
        assert exc.details["variant_hash"] == "deadbeef1234"

    def test_details_keys_complete(self) -> None:
        """Details dict must contain exactly: product_id, variant_hash."""
        exc = self._make()
        assert set(exc.details.keys()) == {"product_id", "variant_hash"}


# ===========================================================================
# DuplicateProductAttributeError
# ===========================================================================


class TestDuplicateProductAttributeError:
    """Tests for DuplicateProductAttributeError."""

    def _make(
        self,
        product_id: uuid.UUID | None = None,
        attribute_id: uuid.UUID | None = None,
    ) -> DuplicateProductAttributeError:
        return DuplicateProductAttributeError(
            product_id=product_id or uuid.uuid4(),
            attribute_id=attribute_id or uuid.uuid4(),
        )

    def test_inherits_from_conflict_error(self) -> None:
        """DuplicateProductAttributeError is a subclass of ConflictError."""
        exc = self._make()
        assert isinstance(exc, ConflictError)

    def test_status_code_is_409(self) -> None:
        """HTTP status code must be 409 (Conflict)."""
        exc = self._make()
        assert exc.status_code == 409

    def test_error_code(self) -> None:
        """error_code must be DUPLICATE_PRODUCT_ATTRIBUTE."""
        exc = self._make()
        assert exc.error_code == "DUPLICATE_PRODUCT_ATTRIBUTE"

    def test_message_is_static(self) -> None:
        """Message must be the static string defined in the plan."""
        exc = self._make()
        assert exc.message == "Attribute is already assigned to this product."

    def test_details_product_id_as_string(self) -> None:
        """details['product_id'] must be str(product_id)."""
        product_id = uuid.uuid4()
        exc = DuplicateProductAttributeError(product_id=product_id, attribute_id=uuid.uuid4())
        assert exc.details["product_id"] == str(product_id)

    def test_details_attribute_id_as_string(self) -> None:
        """details['attribute_id'] must be str(attribute_id)."""
        attribute_id = uuid.uuid4()
        exc = DuplicateProductAttributeError(product_id=uuid.uuid4(), attribute_id=attribute_id)
        assert exc.details["attribute_id"] == str(attribute_id)

    def test_details_keys_complete(self) -> None:
        """Details dict must contain exactly: product_id, attribute_id."""
        exc = self._make()
        assert set(exc.details.keys()) == {"product_id", "attribute_id"}


# ===========================================================================
# ProductAttributeValueNotFoundError
# ===========================================================================


class TestProductAttributeValueNotFoundError:
    """Tests for ProductAttributeValueNotFoundError."""

    def _make(
        self,
        product_id: uuid.UUID | None = None,
        attribute_id: uuid.UUID | None = None,
    ) -> ProductAttributeValueNotFoundError:
        return ProductAttributeValueNotFoundError(
            product_id=product_id or uuid.uuid4(),
            attribute_id=attribute_id or uuid.uuid4(),
        )

    def test_inherits_from_not_found_error(self) -> None:
        """ProductAttributeValueNotFoundError is a subclass of NotFoundError."""
        exc = self._make()
        assert isinstance(exc, NotFoundError)

    def test_status_code_is_404(self) -> None:
        """HTTP status code must be 404 (Not Found)."""
        exc = self._make()
        assert exc.status_code == 404

    def test_error_code(self) -> None:
        """error_code must be PRODUCT_ATTRIBUTE_VALUE_NOT_FOUND."""
        exc = self._make()
        assert exc.error_code == "PRODUCT_ATTRIBUTE_VALUE_NOT_FOUND"

    def test_message_is_static(self) -> None:
        """Message must be the static string defined in the plan."""
        exc = self._make()
        assert exc.message == "Product attribute value not found."

    def test_details_product_id_as_string(self) -> None:
        """details['product_id'] must be str(product_id)."""
        product_id = uuid.uuid4()
        exc = ProductAttributeValueNotFoundError(product_id=product_id, attribute_id=uuid.uuid4())
        assert exc.details["product_id"] == str(product_id)

    def test_details_attribute_id_as_string(self) -> None:
        """details['attribute_id'] must be str(attribute_id)."""
        attribute_id = uuid.uuid4()
        exc = ProductAttributeValueNotFoundError(product_id=uuid.uuid4(), attribute_id=attribute_id)
        assert exc.details["attribute_id"] == str(attribute_id)

    def test_accepts_string_product_id(self) -> None:
        """product_id parameter can be passed as a plain string."""
        exc = ProductAttributeValueNotFoundError(
            product_id="string-product-id", attribute_id=uuid.uuid4()
        )
        assert exc.details["product_id"] == "string-product-id"

    def test_accepts_string_attribute_id(self) -> None:
        """attribute_id parameter can be passed as a plain string."""
        exc = ProductAttributeValueNotFoundError(
            product_id=uuid.uuid4(), attribute_id="string-attribute-id"
        )
        assert exc.details["attribute_id"] == "string-attribute-id"

    def test_details_keys_complete(self) -> None:
        """Details dict must contain exactly: product_id, attribute_id."""
        exc = self._make()
        assert set(exc.details.keys()) == {"product_id", "attribute_id"}


# ===========================================================================
# ConcurrencyError
# ===========================================================================


class TestConcurrencyError:
    """Tests for ConcurrencyError."""

    def _make(
        self,
        entity_type: str = "Product",
        entity_id: uuid.UUID | None = None,
        expected_version: int = 3,
        actual_version: int = 5,
    ) -> ConcurrencyError:
        return ConcurrencyError(
            entity_type=entity_type,
            entity_id=entity_id or uuid.uuid4(),
            expected_version=expected_version,
            actual_version=actual_version,
        )

    def test_inherits_from_conflict_error(self) -> None:
        """ConcurrencyError is a subclass of ConflictError."""
        exc = self._make()
        assert isinstance(exc, ConflictError)

    def test_status_code_is_409(self) -> None:
        """HTTP status code must be 409 (Conflict)."""
        exc = self._make()
        assert exc.status_code == 409

    def test_error_code(self) -> None:
        """error_code must be CONCURRENCY_ERROR."""
        exc = self._make()
        assert exc.error_code == "CONCURRENCY_ERROR"

    def test_message_contains_entity_type(self) -> None:
        """Message must embed the entity_type string."""
        exc = self._make(entity_type="SKU")
        assert "SKU" in exc.message

    def test_message_contains_entity_id(self) -> None:
        """Message must embed the entity_id string representation."""
        entity_id = uuid.uuid4()
        exc = self._make(entity_id=entity_id)
        assert str(entity_id) in exc.message

    def test_message_format(self) -> None:
        """Message must match the exact template."""
        entity_id = uuid.uuid4()
        exc = ConcurrencyError(
            entity_type="Product",
            entity_id=entity_id,
            expected_version=1,
            actual_version=2,
        )
        assert exc.message == f"Concurrent modification detected for Product {entity_id}."

    def test_details_entity_type(self) -> None:
        """details['entity_type'] must be the string passed at construction."""
        exc = self._make(entity_type="SKU")
        assert exc.details["entity_type"] == "SKU"

    def test_details_entity_id_as_string(self) -> None:
        """details['entity_id'] must be str(entity_id)."""
        entity_id = uuid.uuid4()
        exc = self._make(entity_id=entity_id)
        assert exc.details["entity_id"] == str(entity_id)

    def test_details_expected_version(self) -> None:
        """details['expected_version'] must be the integer passed."""
        exc = self._make(expected_version=7)
        assert exc.details["expected_version"] == 7

    def test_details_actual_version(self) -> None:
        """details['actual_version'] must be the integer passed."""
        exc = self._make(actual_version=10)
        assert exc.details["actual_version"] == 10

    def test_details_keys_complete(self) -> None:
        """Details dict must contain exactly: entity_type, entity_id, expected_version, actual_version."""
        exc = self._make()
        assert set(exc.details.keys()) == {
            "entity_type",
            "entity_id",
            "expected_version",
            "actual_version",
        }

    @pytest.mark.parametrize("entity_type", ["Product", "SKU", "Order", "Warehouse"])
    def test_generic_entity_types(self, entity_type: str) -> None:
        """ConcurrencyError is reusable for any entity type."""
        exc = self._make(entity_type=entity_type)
        assert exc.details["entity_type"] == entity_type


# ===========================================================================
# Integration: Product entity raises correct exceptions
# ===========================================================================


class TestProductEntityRaisesCorrectExceptions:
    """Integration tests verifying Product/SKU entity methods raise the MT-4 exceptions."""

    # -----------------------------------------------------------------------
    # FSM: transition_status raises InvalidStatusTransitionError
    # -----------------------------------------------------------------------

    def test_transition_status_raises_on_forbidden_transition(self) -> None:
        """Product.transition_status raises InvalidStatusTransitionError for invalid moves."""
        product = _make_product()
        assert product.status == ProductStatus.DRAFT

        with pytest.raises(InvalidStatusTransitionError) as exc_info:
            product.transition_status(ProductStatus.PUBLISHED)

        exc = exc_info.value
        assert exc.error_code == "INVALID_STATUS_TRANSITION"
        assert exc.details["current_status"] == "draft"
        assert exc.details["target_status"] == "published"

    def test_transition_status_allowed_transitions_in_details(self) -> None:
        """allowed_transitions in details must list valid targets from current status."""
        product = _make_product()
        with pytest.raises(InvalidStatusTransitionError) as exc_info:
            product.transition_status(ProductStatus.ARCHIVED)

        allowed = exc_info.value.details["allowed_transitions"]
        assert isinstance(allowed, list)
        # DRAFT only allows ENRICHING
        assert allowed == ["enriching"]

    def test_transition_status_valid_transition_does_not_raise(self) -> None:
        """Sanity: valid DRAFT -> ENRICHING transition succeeds without exception."""
        product = _make_product()
        product.transition_status(ProductStatus.ENRICHING)
        assert product.status == ProductStatus.ENRICHING

    @pytest.mark.parametrize(
        ("start", "invalid_target"),
        [
            (ProductStatus.DRAFT, ProductStatus.ARCHIVED),
            (ProductStatus.DRAFT, ProductStatus.READY_FOR_REVIEW),
            (ProductStatus.DRAFT, ProductStatus.PUBLISHED),
            (ProductStatus.PUBLISHED, ProductStatus.ENRICHING),
            (ProductStatus.PUBLISHED, ProductStatus.DRAFT),
            (ProductStatus.ARCHIVED, ProductStatus.PUBLISHED),
        ],
    )
    def test_forbidden_transitions_all_raise(
        self, start: ProductStatus, invalid_target: ProductStatus
    ) -> None:
        """All FSM-forbidden transitions raise InvalidStatusTransitionError."""
        product = _make_product()

        # Advance product to `start` status via valid transitions
        _advance_to_status(product, start)

        with pytest.raises(InvalidStatusTransitionError):
            product.transition_status(invalid_target)

    # -----------------------------------------------------------------------
    # add_sku raises DuplicateVariantCombinationError on duplicate hash
    # -----------------------------------------------------------------------

    def test_add_sku_raises_on_duplicate_variant_combination(self) -> None:
        """Product.add_sku raises DuplicateVariantCombinationError on hash collision."""
        product = _make_product()
        attr_id = uuid.uuid4()
        val_id = uuid.uuid4()
        attrs: list[tuple[uuid.UUID, uuid.UUID]] = [(attr_id, val_id)]

        # First add succeeds
        product.add_sku(sku_code="SKU-001", price=_make_money(), variant_attributes=attrs)

        # Second add with same combination raises
        with pytest.raises(DuplicateVariantCombinationError) as exc_info:
            product.add_sku(sku_code="SKU-002", price=_make_money(), variant_attributes=attrs)

        exc = exc_info.value
        assert exc.error_code == "DUPLICATE_VARIANT_COMBINATION"
        assert exc.details["product_id"] == str(product.id)
        assert isinstance(exc.details["variant_hash"], str)
        assert len(exc.details["variant_hash"]) == 64  # SHA-256 hex digest

    def test_add_sku_no_raise_on_soft_deleted_duplicate(self) -> None:
        """Adding a SKU whose only 'duplicate' is soft-deleted does NOT raise."""
        product = _make_product()
        attr_id = uuid.uuid4()
        val_id = uuid.uuid4()
        attrs: list[tuple[uuid.UUID, uuid.UUID]] = [(attr_id, val_id)]

        first_sku = product.add_sku(
            sku_code="SKU-001", price=_make_money(), variant_attributes=attrs
        )
        product.remove_sku(first_sku.id)  # soft-delete

        # Reuse same combination after soft-delete must succeed
        second_sku = product.add_sku(
            sku_code="SKU-002", price=_make_money(), variant_attributes=attrs
        )
        assert second_sku.sku_code == "SKU-002"

    # -----------------------------------------------------------------------
    # remove_sku raises SKUNotFoundError for missing/deleted SKU
    # -----------------------------------------------------------------------

    def test_remove_sku_raises_sku_not_found_for_unknown_id(self) -> None:
        """Product.remove_sku raises SKUNotFoundError when id does not exist."""
        product = _make_product()
        unknown_id = uuid.uuid4()

        with pytest.raises(SKUNotFoundError) as exc_info:
            product.remove_sku(unknown_id)

        exc = exc_info.value
        assert exc.error_code == "SKU_NOT_FOUND"
        assert exc.details["sku_id"] == str(unknown_id)

    def test_remove_sku_raises_sku_not_found_for_already_deleted_sku(self) -> None:
        """Product.remove_sku raises SKUNotFoundError for already soft-deleted SKU."""
        product = _make_product()
        sku = product.add_sku(sku_code="DEL-SKU", price=_make_money())
        product.remove_sku(sku.id)  # first removal

        with pytest.raises(SKUNotFoundError):
            product.remove_sku(sku.id)  # second removal on soft-deleted SKU

    def test_remove_sku_succeeds_for_valid_active_sku(self) -> None:
        """Sanity: remove_sku on an active SKU does not raise."""
        product = _make_product()
        sku = product.add_sku(sku_code="VALID-SKU", price=_make_money())
        product.remove_sku(sku.id)
        assert sku.deleted_at is not None


# ---------------------------------------------------------------------------
# Helper: advance a product through valid transitions to reach a target status
# ---------------------------------------------------------------------------

_TRANSITION_PATH: dict[ProductStatus, list[ProductStatus]] = {
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


def _advance_to_status(product: Product, target: ProductStatus) -> None:
    """Drive *product* from DRAFT to *target* via legal FSM transitions."""
    for step in _TRANSITION_PATH[target]:
        product.transition_status(step)
