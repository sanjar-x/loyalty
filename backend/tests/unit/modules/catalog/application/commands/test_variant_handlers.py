"""Unit tests for all Variant command handlers (CMD-05).

Tests handler orchestration: Product aggregate variant management,
UoW commit/rollback, and domain exception propagation.
Uses FakeUnitOfWork for real in-memory repository behavior (D-08).
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.catalog.application.commands.add_variant import (
    AddVariantCommand,
    AddVariantHandler,
    AddVariantResult,
)
from src.modules.catalog.application.commands.delete_variant import (
    DeleteVariantCommand,
    DeleteVariantHandler,
)
from src.modules.catalog.application.commands.update_variant import (
    UpdateVariantCommand,
    UpdateVariantHandler,
    UpdateVariantResult,
)
from src.modules.catalog.domain.exceptions import (
    LastVariantRemovalError,
    ProductNotFoundError,
    VariantNotFoundError,
)
from src.modules.catalog.domain.value_objects import Money
from tests.factories.product_builder import ProductBuilder
from tests.fakes.fake_uow import FakeUnitOfWork

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_logger():
    """Create a mock logger that supports .bind() chaining."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    return logger


def _seed_product(uow, slug=None):
    """Create and seed a Product with 1 default variant into the fake UoW."""
    builder = ProductBuilder()
    if slug:
        builder = builder.with_slug(slug)
    product = builder.build()
    uow.products._store[product.id] = product
    return product


# ============================================================================
# TestAddVariant
# ============================================================================


class TestAddVariant:
    """Tests for AddVariantHandler."""

    async def test_happy_path_without_price(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)
        initial_variant_count = len(product.variants)

        handler = AddVariantHandler(
            product_repo=uow.products,
            uow=uow,
            cache=AsyncMock(),
            logger=_make_logger(),
        )

        result = await handler.handle(
            AddVariantCommand(
                product_id=product.id,
                name_i18n={"en": "Size 42", "ru": "Размер 42"},
            )
        )

        assert isinstance(result, AddVariantResult)
        assert result.variant_id is not None
        assert uow.committed is True
        updated = uow.products._store[product.id]
        assert len(updated.variants) == initial_variant_count + 1
        # Verify the new variant ID is among the product's variants
        variant_ids = [v.id for v in updated.variants]
        assert result.variant_id in variant_ids

    async def test_happy_path_with_price(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)

        handler = AddVariantHandler(
            product_repo=uow.products,
            uow=uow,
            cache=AsyncMock(),
            logger=_make_logger(),
        )

        result = await handler.handle(
            AddVariantCommand(
                product_id=product.id,
                name_i18n={"en": "Size 42", "ru": "Размер 42"},
                default_price_amount=5000,
                default_price_currency="RUB",
            )
        )

        assert uow.committed is True
        updated = uow.products._store[product.id]
        new_variant = next(v for v in updated.variants if v.id == result.variant_id)
        assert new_variant.default_price == Money(amount=5000, currency="RUB")

    async def test_product_not_found(self):
        uow = FakeUnitOfWork()

        handler = AddVariantHandler(
            product_repo=uow.products,
            uow=uow,
            cache=AsyncMock(),
            logger=_make_logger(),
        )

        with pytest.raises(ProductNotFoundError):
            await handler.handle(
                AddVariantCommand(
                    product_id=uuid.uuid4(),
                    name_i18n={"en": "Size 42", "ru": "Размер 42"},
                )
            )

        assert uow.committed is False

    async def test_variant_added_to_product_aggregate(self):
        """After add, verify product.variants contains the new variant."""
        uow = FakeUnitOfWork()
        product = _seed_product(uow)

        handler = AddVariantHandler(
            product_repo=uow.products,
            uow=uow,
            cache=AsyncMock(),
            logger=_make_logger(),
        )

        result = await handler.handle(
            AddVariantCommand(
                product_id=product.id,
                name_i18n={"en": "Blue", "ru": "Синий"},
                description_i18n={"en": "Blue variant", "ru": "Синий вариант"},
                sort_order=1,
            )
        )

        assert uow.committed is True
        updated = uow.products._store[product.id]
        variant_ids = [v.id for v in updated.variants]
        assert result.variant_id in variant_ids


# ============================================================================
# TestUpdateVariant
# ============================================================================


class TestUpdateVariant:
    """Tests for UpdateVariantHandler."""

    async def test_happy_path_update_name(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)
        variant_id = product.variants[0].id

        handler = UpdateVariantHandler(
            product_repo=uow.products,
            uow=uow,
            cache=AsyncMock(),
            logger=_make_logger(),
        )

        result = await handler.handle(
            UpdateVariantCommand(
                product_id=product.id,
                variant_id=variant_id,
                name_i18n={"en": "Updated Name", "ru": "Обновленное имя"},
                _provided_fields=frozenset({"name_i18n"}),
            )
        )

        assert isinstance(result, UpdateVariantResult)
        assert result.id == variant_id
        assert uow.committed is True
        updated = uow.products._store[product.id]
        variant = next(v for v in updated.variants if v.id == variant_id)
        assert variant.name_i18n["en"] == "Updated Name"

    async def test_happy_path_update_price(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)
        variant_id = product.variants[0].id

        handler = UpdateVariantHandler(
            product_repo=uow.products,
            uow=uow,
            cache=AsyncMock(),
            logger=_make_logger(),
        )

        result = await handler.handle(
            UpdateVariantCommand(
                product_id=product.id,
                variant_id=variant_id,
                default_price_amount=3000,
                default_price_currency="USD",
                _provided_fields=frozenset(
                    {"default_price_amount", "default_price_currency"}
                ),
            )
        )

        assert uow.committed is True
        updated = uow.products._store[product.id]
        variant = next(v for v in updated.variants if v.id == variant_id)
        assert variant.default_price == Money(amount=3000, currency="USD")

    async def test_product_not_found(self):
        uow = FakeUnitOfWork()

        handler = UpdateVariantHandler(
            product_repo=uow.products,
            uow=uow,
            cache=AsyncMock(),
            logger=_make_logger(),
        )

        with pytest.raises(ProductNotFoundError):
            await handler.handle(
                UpdateVariantCommand(
                    product_id=uuid.uuid4(),
                    variant_id=uuid.uuid4(),
                    name_i18n={"en": "X", "ru": "Y"},
                    _provided_fields=frozenset({"name_i18n"}),
                )
            )

        assert uow.committed is False

    async def test_variant_not_found(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)

        handler = UpdateVariantHandler(
            product_repo=uow.products,
            uow=uow,
            cache=AsyncMock(),
            logger=_make_logger(),
        )

        with pytest.raises(VariantNotFoundError):
            await handler.handle(
                UpdateVariantCommand(
                    product_id=product.id,
                    variant_id=uuid.uuid4(),
                    name_i18n={"en": "X", "ru": "Y"},
                    _provided_fields=frozenset({"name_i18n"}),
                )
            )

        assert uow.committed is False

    async def test_invalid_currency_format(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)
        variant_id = product.variants[0].id

        handler = UpdateVariantHandler(
            product_repo=uow.products,
            uow=uow,
            cache=AsyncMock(),
            logger=_make_logger(),
        )

        with pytest.raises(ValueError, match="3 uppercase ASCII"):
            await handler.handle(
                UpdateVariantCommand(
                    product_id=product.id,
                    variant_id=variant_id,
                    default_price_currency="ab",
                    _provided_fields=frozenset({"default_price_currency"}),
                )
            )

        assert uow.committed is False


# ============================================================================
# TestDeleteVariant
# ============================================================================


class TestDeleteVariant:
    """Tests for DeleteVariantHandler."""

    async def test_happy_path(self):
        """Product has 2 variants; deleting one succeeds."""
        uow = FakeUnitOfWork()
        product = _seed_product(uow)
        # Add a second variant so deletion of one is allowed
        second_variant = product.add_variant(
            name_i18n={"en": "Second", "ru": "Второй"},
        )
        variant_to_delete = second_variant.id
        initial_active = len([v for v in product.variants if v.deleted_at is None])

        handler = DeleteVariantHandler(
            product_repo=uow.products,
            uow=uow,
            cache=AsyncMock(),
            logger=_make_logger(),
        )

        await handler.handle(
            DeleteVariantCommand(
                product_id=product.id,
                variant_id=variant_to_delete,
            )
        )

        assert uow.committed is True
        updated = uow.products._store[product.id]
        active_after = [v for v in updated.variants if v.deleted_at is None]
        assert len(active_after) == initial_active - 1

    async def test_product_not_found(self):
        uow = FakeUnitOfWork()

        handler = DeleteVariantHandler(
            product_repo=uow.products,
            uow=uow,
            cache=AsyncMock(),
            logger=_make_logger(),
        )

        with pytest.raises(ProductNotFoundError):
            await handler.handle(
                DeleteVariantCommand(
                    product_id=uuid.uuid4(),
                    variant_id=uuid.uuid4(),
                )
            )

        assert uow.committed is False

    async def test_variant_not_found(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)

        handler = DeleteVariantHandler(
            product_repo=uow.products,
            uow=uow,
            cache=AsyncMock(),
            logger=_make_logger(),
        )

        with pytest.raises(VariantNotFoundError):
            await handler.handle(
                DeleteVariantCommand(
                    product_id=product.id,
                    variant_id=uuid.uuid4(),
                )
            )

        assert uow.committed is False

    async def test_last_variant_removal(self):
        """Cannot delete the only remaining active variant."""
        uow = FakeUnitOfWork()
        product = _seed_product(uow)
        # Product has exactly 1 default variant
        only_variant_id = product.variants[0].id

        handler = DeleteVariantHandler(
            product_repo=uow.products,
            uow=uow,
            cache=AsyncMock(),
            logger=_make_logger(),
        )

        with pytest.raises(LastVariantRemovalError):
            await handler.handle(
                DeleteVariantCommand(
                    product_id=product.id,
                    variant_id=only_variant_id,
                )
            )

        assert uow.committed is False
