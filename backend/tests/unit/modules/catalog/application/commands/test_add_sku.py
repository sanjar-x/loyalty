"""Unit tests for AddSKUCommand, AddSKUResult, and AddSKUHandler.

Tests cover:
- Command dataclass field defaults and immutability
- Handler happy path: product found, SKU added, repo.update + uow.commit called
- Handler product not found: raises ProductNotFoundError, no commit
- Handler compare_at_price validation: raises ValueError when <= price
- Handler duplicate variant hash: propagates DuplicateVariantCombinationError
- Result carries correct sku_id
"""

import uuid
from dataclasses import FrozenInstanceError
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.catalog.application.commands.add_sku import (
    AddSKUCommand,
    AddSKUHandler,
    AddSKUResult,
)
from src.modules.catalog.domain.entities import SKU, Product, ProductVariant
from src.modules.catalog.domain.exceptions import (
    DuplicateVariantCombinationError,
    ProductNotFoundError,
)
from src.modules.catalog.domain.value_objects import Money

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_uow() -> AsyncMock:
    """Build a fully-mocked IUnitOfWork that works as an async context manager."""
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.commit = AsyncMock()
    uow.register_aggregate = MagicMock()
    return uow


def make_product(
    product_id: uuid.UUID | None = None,
    skus: list[SKU] | None = None,
) -> Product:
    """Build a minimal valid Product aggregate for testing.

    Creates a product with one default variant so that add_sku() can find it.

    Args:
        product_id: Optional explicit product UUID.
        skus: Optional list of existing SKUs on the product (unused, kept for API compat).

    Returns:
        A ready-to-use Product instance in DRAFT status with a default variant.
    """
    product = Product.create(
        slug=f"test-product-{uuid.uuid4().hex[:6]}",
        title_i18n={"en": "Test Product"},
        brand_id=uuid.uuid4(),
        primary_category_id=uuid.uuid4(),
        product_id=product_id,
    )
    # Add a default variant so add_sku has a target
    product.add_variant(
        name_i18n={"en": "Default"},
        sort_order=0,
    )
    return product


def make_product_repo(product: Product | None = None) -> AsyncMock:
    """Build a mocked IProductRepository.

    Args:
        product: Product to return from get_with_skus, or None for not-found.

    Returns:
        Configured AsyncMock.
    """
    repo = AsyncMock()
    repo.get_with_variants = AsyncMock(return_value=product)
    repo.update = AsyncMock()
    return repo


def make_command(
    product_id: uuid.UUID | None = None,
    variant_id: uuid.UUID | None = None,
    sku_code: str = "SKU-001",
    price_amount: int | None = 10000,
    price_currency: str = "USD",
    compare_at_price_amount: int | None = None,
    is_active: bool = True,
    variant_attributes: list[tuple[uuid.UUID, uuid.UUID]] | None = None,
) -> AddSKUCommand:
    """Build a minimal valid AddSKUCommand.

    Args:
        product_id: Product UUID; generates one if None.
        variant_id: Variant UUID; generates one if None.
        sku_code: Human-readable SKU code.
        price_amount: Price in smallest currency units (None for no price).
        price_currency: ISO 4217 currency code.
        compare_at_price_amount: Optional strikethrough price amount.
        is_active: Whether SKU is immediately active.
        variant_attributes: Optional variant attribute pairs.

    Returns:
        A ready-to-use command instance.
    """
    return AddSKUCommand(
        product_id=product_id or uuid.uuid4(),
        variant_id=variant_id or uuid.uuid4(),
        sku_code=sku_code,
        price_amount=price_amount,
        price_currency=price_currency,
        compare_at_price_amount=compare_at_price_amount,
        is_active=is_active,
        variant_attributes=variant_attributes or [],
    )


# ---------------------------------------------------------------------------
# AddSKUCommand
# ---------------------------------------------------------------------------


class TestAddSKUCommand:
    """Structural tests for the AddSKUCommand DTO."""

    def test_required_fields_stored_correctly(self) -> None:
        """All required fields are stored on the dataclass."""
        product_id = uuid.uuid4()
        cmd = AddSKUCommand(
            product_id=product_id,
            sku_code="SKU-TEST",
            price_amount=5000,
            price_currency="RUB",
        )
        assert cmd.product_id == product_id
        assert cmd.sku_code == "SKU-TEST"
        assert cmd.price_amount == 5000
        assert cmd.price_currency == "RUB"

    def test_optional_fields_have_correct_defaults(self) -> None:
        """Optional fields default to None, True, and empty list."""
        cmd = make_command()
        assert cmd.compare_at_price_amount is None
        assert cmd.is_active is True
        assert cmd.variant_attributes == []

    def test_command_is_frozen(self) -> None:
        """AddSKUCommand is a frozen dataclass -- mutation must raise."""
        cmd = make_command()
        with pytest.raises(FrozenInstanceError):
            cmd.sku_code = "MUTATED"  # type: ignore[misc]

    def test_default_factory_instances_are_independent(self) -> None:
        """Two commands with defaults share no mutable state."""
        cmd1 = make_command(sku_code="SKU-1")
        cmd2 = make_command(sku_code="SKU-2")
        assert cmd1.variant_attributes is not cmd2.variant_attributes

    def test_variant_attributes_stored(self) -> None:
        """Variant attributes list is stored correctly."""
        attr_id = uuid.uuid4()
        val_id = uuid.uuid4()
        cmd = make_command(variant_attributes=[(attr_id, val_id)])
        assert cmd.variant_attributes == [(attr_id, val_id)]


# ---------------------------------------------------------------------------
# AddSKUResult
# ---------------------------------------------------------------------------


class TestAddSKUResult:
    """Structural tests for the AddSKUResult DTO."""

    def test_stores_sku_id(self) -> None:
        """sku_id is stored as supplied."""
        sku_id = uuid.uuid4()
        result = AddSKUResult(sku_id=sku_id)
        assert result.sku_id == sku_id

    def test_result_is_frozen(self) -> None:
        """AddSKUResult is a frozen dataclass -- mutation must raise."""
        result = AddSKUResult(sku_id=uuid.uuid4())
        with pytest.raises(FrozenInstanceError):
            result.sku_id = uuid.uuid4()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# AddSKUHandler -- happy path
# ---------------------------------------------------------------------------


class TestAddSKUHandlerHappyPath:
    """Handler tests when the product exists and SKU is valid."""

    async def test_returns_result_with_sku_id(self) -> None:
        """Handler returns AddSKUResult whose sku_id is a UUID."""
        product = make_product()
        product_id = product.id
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = AddSKUHandler(product_repo=repo, uow=uow)

        vid = product.variants[0].id
        result = await handler.handle(make_command(product_id=product_id, variant_id=vid))

        assert isinstance(result, AddSKUResult)
        assert isinstance(result.sku_id, uuid.UUID)

    async def test_sku_id_matches_added_sku(self) -> None:
        """The sku_id in the result matches the SKU appended to the product."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = AddSKUHandler(product_repo=repo, uow=uow)

        vid = product.variants[0].id
        result = await handler.handle(make_command(product_id=product.id, variant_id=vid))

        assert len(product.variants[0].skus) == 1
        assert result.sku_id == product.variants[0].skus[0].id

    async def test_calls_get_with_variants_with_correct_id(self) -> None:
        """Handler calls get_with_variants with the command's product_id."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = AddSKUHandler(product_repo=repo, uow=uow)

        vid = product.variants[0].id
        await handler.handle(make_command(product_id=product.id, variant_id=vid))

        repo.get_with_variants.assert_awaited_once_with(product.id)

    async def test_calls_repo_update_with_product(self) -> None:
        """Handler calls repo.update exactly once with the product."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = AddSKUHandler(product_repo=repo, uow=uow)

        vid = product.variants[0].id
        await handler.handle(make_command(product_id=product.id, variant_id=vid))

        repo.update.assert_awaited_once_with(product)

    async def test_calls_uow_commit_once(self) -> None:
        """Handler commits the UoW exactly once on success."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = AddSKUHandler(product_repo=repo, uow=uow)

        vid = product.variants[0].id
        await handler.handle(make_command(product_id=product.id, variant_id=vid))

        uow.commit.assert_awaited_once()

    async def test_uow_used_as_context_manager(self) -> None:
        """Handler enters and exits the UoW async context manager."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = AddSKUHandler(product_repo=repo, uow=uow)

        vid = product.variants[0].id
        await handler.handle(make_command(product_id=product.id, variant_id=vid))

        uow.__aenter__.assert_awaited_once()
        uow.__aexit__.assert_awaited_once()

    async def test_sku_has_correct_price(self) -> None:
        """The added SKU has the price from the command."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = AddSKUHandler(product_repo=repo, uow=uow)

        vid = product.variants[0].id
        await handler.handle(
            make_command(
                product_id=product.id,
                variant_id=vid,
                price_amount=7500,
                price_currency="RUB",
            )
        )

        sku = product.variants[0].skus[0]
        assert sku.price == Money(amount=7500, currency="RUB")

    async def test_sku_has_correct_sku_code(self) -> None:
        """The added SKU has the sku_code from the command."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = AddSKUHandler(product_repo=repo, uow=uow)

        vid = product.variants[0].id
        await handler.handle(make_command(product_id=product.id, variant_id=vid, sku_code="CUSTOM-CODE-99"))

        assert product.variants[0].skus[0].sku_code == "CUSTOM-CODE-99"

    async def test_sku_is_active_by_default(self) -> None:
        """SKU is active when is_active=True (default)."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = AddSKUHandler(product_repo=repo, uow=uow)

        vid = product.variants[0].id
        await handler.handle(make_command(product_id=product.id, variant_id=vid))

        assert product.variants[0].skus[0].is_active is True

    async def test_sku_can_be_inactive(self) -> None:
        """SKU respects is_active=False from the command."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = AddSKUHandler(product_repo=repo, uow=uow)

        vid = product.variants[0].id
        await handler.handle(make_command(product_id=product.id, variant_id=vid, is_active=False))

        assert product.variants[0].skus[0].is_active is False

    async def test_compare_at_price_set_when_valid(self) -> None:
        """When compare_at_price > price, it is set on the SKU."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = AddSKUHandler(product_repo=repo, uow=uow)

        vid = product.variants[0].id
        await handler.handle(
            make_command(
                product_id=product.id,
                variant_id=vid,
                price_amount=5000,
                price_currency="USD",
                compare_at_price_amount=8000,
            )
        )

        sku = product.variants[0].skus[0]
        assert sku.compare_at_price == Money(amount=8000, currency="USD")

    async def test_compare_at_price_none_when_not_provided(self) -> None:
        """When compare_at_price_amount is None, SKU has no compare_at_price."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = AddSKUHandler(product_repo=repo, uow=uow)

        vid = product.variants[0].id
        await handler.handle(make_command(product_id=product.id, variant_id=vid))

        assert product.variants[0].skus[0].compare_at_price is None


# ---------------------------------------------------------------------------
# AddSKUHandler -- product not found
# ---------------------------------------------------------------------------


class TestAddSKUHandlerProductNotFound:
    """Handler tests when the product does not exist."""

    async def test_raises_product_not_found_error(self) -> None:
        """Handler raises ProductNotFoundError when product is None."""
        repo = make_product_repo(product=None)
        uow = make_uow()
        handler = AddSKUHandler(product_repo=repo, uow=uow)

        with pytest.raises(ProductNotFoundError):
            await handler.handle(make_command())

    async def test_error_contains_product_id(self) -> None:
        """Raised exception details include the missing product_id."""
        product_id = uuid.uuid4()
        repo = make_product_repo(product=None)
        uow = make_uow()
        handler = AddSKUHandler(product_repo=repo, uow=uow)

        with pytest.raises(ProductNotFoundError) as exc_info:
            await handler.handle(make_command(product_id=product_id))

        assert str(product_id) in str(exc_info.value)

    async def test_repo_update_not_called(self) -> None:
        """When product not found, repo.update must not be called."""
        repo = make_product_repo(product=None)
        uow = make_uow()
        handler = AddSKUHandler(product_repo=repo, uow=uow)

        with pytest.raises(ProductNotFoundError):
            await handler.handle(make_command())

        repo.update.assert_not_awaited()

    async def test_commit_not_called(self) -> None:
        """When product not found, uow.commit must not be called."""
        repo = make_product_repo(product=None)
        uow = make_uow()
        handler = AddSKUHandler(product_repo=repo, uow=uow)

        with pytest.raises(ProductNotFoundError):
            await handler.handle(make_command())

        uow.commit.assert_not_awaited()


# ---------------------------------------------------------------------------
# AddSKUHandler -- compare_at_price validation
# ---------------------------------------------------------------------------


class TestAddSKUHandlerCompareAtPriceValidation:
    """Handler tests for compare_at_price_amount validation."""

    async def test_raises_value_error_when_compare_equals_price(self) -> None:
        """compare_at_price == price raises ValueError."""
        product = make_product()
        vid = product.variants[0].id
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = AddSKUHandler(product_repo=repo, uow=uow)

        with pytest.raises(ValueError, match="compare_at_price must be greater than price"):
            await handler.handle(
                make_command(
                    product_id=product.id,
                    variant_id=vid,
                    price_amount=5000,
                    compare_at_price_amount=5000,
                )
            )

    async def test_raises_value_error_when_compare_less_than_price(self) -> None:
        """compare_at_price < price raises ValueError."""
        product = make_product()
        vid = product.variants[0].id
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = AddSKUHandler(product_repo=repo, uow=uow)

        with pytest.raises(ValueError, match="compare_at_price must be greater than price"):
            await handler.handle(
                make_command(
                    product_id=product.id,
                    variant_id=vid,
                    price_amount=5000,
                    compare_at_price_amount=3000,
                )
            )

    async def test_commit_not_called_on_price_validation_error(self) -> None:
        """When compare_at_price validation fails, commit is not called."""
        product = make_product()
        vid = product.variants[0].id
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = AddSKUHandler(product_repo=repo, uow=uow)

        with pytest.raises(ValueError):
            await handler.handle(
                make_command(
                    product_id=product.id,
                    variant_id=vid,
                    price_amount=5000,
                    compare_at_price_amount=3000,
                )
            )

        uow.commit.assert_not_awaited()

    async def test_repo_update_not_called_on_price_validation_error(self) -> None:
        """When compare_at_price validation fails, repo.update is not called."""
        product = make_product()
        vid = product.variants[0].id
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = AddSKUHandler(product_repo=repo, uow=uow)

        with pytest.raises(ValueError):
            await handler.handle(
                make_command(
                    product_id=product.id,
                    variant_id=vid,
                    price_amount=5000,
                    compare_at_price_amount=3000,
                )
            )

        repo.update.assert_not_awaited()

    @pytest.mark.parametrize(
        ("price_amount", "compare_at_price_amount"),
        [
            (5000, 4999),
            (5000, 5000),
            (5000, 1),
            (5000, 0),
            (10000, 9999),
        ],
    )
    async def test_various_invalid_compare_at_prices(
        self,
        price_amount: int,
        compare_at_price_amount: int,
    ) -> None:
        """Parametrized: various invalid compare_at_price values all raise ValueError."""
        product = make_product()
        vid = product.variants[0].id
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = AddSKUHandler(product_repo=repo, uow=uow)

        with pytest.raises(ValueError):
            await handler.handle(
                make_command(
                    product_id=product.id,
                    variant_id=vid,
                    price_amount=price_amount,
                    compare_at_price_amount=compare_at_price_amount,
                )
            )


# ---------------------------------------------------------------------------
# AddSKUHandler -- duplicate variant combination
# ---------------------------------------------------------------------------


class TestAddSKUHandlerDuplicateVariant:
    """Handler tests for duplicate variant hash collision."""

    async def test_raises_duplicate_variant_combination_error(self) -> None:
        """Adding a SKU with same variant attributes raises DuplicateVariantCombinationError."""
        attr_id = uuid.uuid4()
        val_id = uuid.uuid4()
        variant_attrs: list[tuple[uuid.UUID, uuid.UUID]] = [(attr_id, val_id)]

        product = make_product()
        vid = product.variants[0].id
        # Pre-add a SKU with the same variant attributes.
        product.add_sku(
            vid,
            sku_code="EXISTING-SKU",
            price=Money(amount=5000, currency="USD"),
            variant_attributes=variant_attrs,
        )

        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = AddSKUHandler(product_repo=repo, uow=uow)

        with pytest.raises(DuplicateVariantCombinationError):
            await handler.handle(
                make_command(
                    product_id=product.id,
                    variant_id=vid,
                    variant_attributes=variant_attrs,
                )
            )

    async def test_commit_not_called_on_duplicate(self) -> None:
        """When variant hash collides, commit is not called."""
        attr_id = uuid.uuid4()
        val_id = uuid.uuid4()
        variant_attrs: list[tuple[uuid.UUID, uuid.UUID]] = [(attr_id, val_id)]

        product = make_product()
        vid = product.variants[0].id
        product.add_sku(
            vid,
            sku_code="EXISTING-SKU",
            price=Money(amount=5000, currency="USD"),
            variant_attributes=variant_attrs,
        )

        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = AddSKUHandler(product_repo=repo, uow=uow)

        with pytest.raises(DuplicateVariantCombinationError):
            await handler.handle(
                make_command(
                    product_id=product.id,
                    variant_id=vid,
                    variant_attributes=variant_attrs,
                )
            )

        uow.commit.assert_not_awaited()

    async def test_different_variant_attributes_no_collision(self) -> None:
        """Adding SKUs with different variant attributes succeeds."""
        product = make_product()
        vid = product.variants[0].id
        product.add_sku(
            vid,
            sku_code="EXISTING-SKU",
            price=Money(amount=5000, currency="USD"),
            variant_attributes=[(uuid.uuid4(), uuid.uuid4())],
        )

        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = AddSKUHandler(product_repo=repo, uow=uow)

        result = await handler.handle(
            make_command(
                product_id=product.id,
                variant_id=vid,
                variant_attributes=[(uuid.uuid4(), uuid.uuid4())],
            )
        )

        assert isinstance(result, AddSKUResult)
        assert len(product.variants[0].skus) == 2


# ---------------------------------------------------------------------------
# AddSKUHandler -- variant attributes handling
# ---------------------------------------------------------------------------


class TestAddSKUHandlerVariantAttributes:
    """Handler tests for variant_attributes edge cases."""

    async def test_empty_variant_attributes_creates_sku(self) -> None:
        """Empty variant_attributes list still creates a valid SKU."""
        product = make_product()
        vid = product.variants[0].id
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = AddSKUHandler(product_repo=repo, uow=uow)

        result = await handler.handle(make_command(product_id=product.id, variant_id=vid, variant_attributes=[]))

        assert isinstance(result, AddSKUResult)
        assert product.variants[0].skus[0].variant_attributes == []

    async def test_multiple_variant_attributes_stored(self) -> None:
        """Multiple variant attribute pairs are forwarded to the SKU."""
        attr1, val1 = uuid.uuid4(), uuid.uuid4()
        attr2, val2 = uuid.uuid4(), uuid.uuid4()
        variant_attrs: list[tuple[uuid.UUID, uuid.UUID]] = [(attr1, val1), (attr2, val2)]

        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = AddSKUHandler(product_repo=repo, uow=uow)

        vid = product.variants[0].id
        await handler.handle(make_command(product_id=product.id, variant_id=vid, variant_attributes=variant_attrs))

        sku = product.variants[0].skus[0]
        assert len(sku.variant_attributes) == 2
