"""Unit tests for UpdateSKUCommand, UpdateSKUResult, and UpdateSKUHandler.

Covers:
  - UpdateSKUCommand dataclass creation, field defaults, _provided_fields pattern
  - UpdateSKUResult stores returned SKU id
  - Happy path: SKU found, updated, repo.update + uow.commit called
  - Product not found: raises ProductNotFoundError, no commit
  - SKU not found: raises SKUNotFoundError, no commit
  - Optimistic locking: version mismatch raises ConcurrencyError
  - Variant attribute change: re-computes variant_hash, checks uniqueness
  - Duplicate variant combination: raises DuplicateVariantCombinationError
  - _provided_fields: distinguish "unchanged" vs "clear" vs "set"
  - Price partial update: only amount or currency changed keeps the other
  - compare_at_price <= price: raises ValueError
"""

import uuid
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.catalog.application.commands.update_sku import (
    UpdateSKUCommand,
    UpdateSKUHandler,
    UpdateSKUResult,
)
from src.modules.catalog.domain.exceptions import (
    ConcurrencyError,
    DuplicateVariantCombinationError,
    ProductNotFoundError,
    SKUNotFoundError,
)
from src.modules.catalog.domain.value_objects import Money

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_uow() -> AsyncMock:
    """Build a mock IUnitOfWork that supports async context manager usage."""
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.commit = AsyncMock()
    return uow


def make_sku(
    sku_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
    sku_code: str = "SKU-001",
    price: Money | None = None,
    compare_at_price: Money | None = None,
    is_active: bool = True,
    version: int = 1,
    variant_hash: str = "abc123",
    variant_attributes: list[tuple[uuid.UUID, uuid.UUID]] | None = None,
    deleted_at: datetime | None = None,
) -> MagicMock:
    """Build a minimal mock SKU domain entity."""
    sku = MagicMock()
    sku.id = sku_id or uuid.uuid4()
    sku.product_id = product_id or uuid.uuid4()
    sku.sku_code = sku_code
    sku.price = price or Money(amount=10000, currency="USD")
    sku.compare_at_price = compare_at_price
    sku.is_active = is_active
    sku.version = version
    sku.variant_hash = variant_hash
    sku.variant_attributes = variant_attributes or []
    sku.deleted_at = deleted_at
    sku.update = MagicMock()
    return sku


def _make_mock_variant(skus: list[MagicMock] | None = None) -> MagicMock:
    """Build a mock ProductVariant holding the given SKUs."""
    variant = MagicMock()
    variant.id = uuid.uuid4()
    variant.skus = skus or []
    variant.deleted_at = None
    return variant


def make_product(
    product_id: uuid.UUID | None = None,
    skus: list[MagicMock] | None = None,
) -> MagicMock:
    """Build a minimal mock Product aggregate with SKUs inside a variant."""
    product = MagicMock()
    product.id = product_id or uuid.uuid4()
    # Wrap SKUs inside a single variant (mirrors the new domain model)
    variant = _make_mock_variant(skus or [])
    product.variants = [variant]

    def find_sku_impl(sid: uuid.UUID) -> MagicMock | None:
        for v in product.variants:
            for s in v.skus:
                if s.id == sid and s.deleted_at is None:
                    return s
        return None

    product.find_sku = MagicMock(side_effect=find_sku_impl)

    def compute_hash(attrs: list[tuple[uuid.UUID, uuid.UUID]]) -> str:
        import hashlib

        sorted_attrs = sorted(attrs, key=lambda x: str(x[0]))
        payload = "|".join(f"{a!s}:{v!s}" for a, v in sorted_attrs)
        return hashlib.sha256(payload.encode()).hexdigest()

    product.compute_variant_hash = MagicMock(side_effect=compute_hash)
    return product


def make_product_repo(product: MagicMock | None = None) -> AsyncMock:
    """Build a mock IProductRepository."""
    repo = AsyncMock()
    repo.get_with_variants = AsyncMock(return_value=product)
    repo.update = AsyncMock()
    return repo


# ---------------------------------------------------------------------------
# UpdateSKUCommand dataclass
# ---------------------------------------------------------------------------


class TestUpdateSKUCommand:
    """Tests for UpdateSKUCommand construction and field defaults."""

    def test_required_fields_stored(self) -> None:
        """product_id and sku_id are stored correctly."""
        pid = uuid.uuid4()
        sid = uuid.uuid4()
        cmd = UpdateSKUCommand(product_id=pid, sku_id=sid)
        assert cmd.product_id == pid
        assert cmd.sku_id == sid

    def test_optional_fields_default_to_none(self) -> None:
        """All optional fields default to None."""
        cmd = UpdateSKUCommand(product_id=uuid.uuid4(), sku_id=uuid.uuid4())
        assert cmd.sku_code is None
        assert cmd.price_amount is None
        assert cmd.price_currency is None
        assert cmd.compare_at_price_amount is None
        assert cmd.is_active is None
        assert cmd.variant_attributes is None
        assert cmd.version is None
        assert cmd._provided_fields == frozenset()

    def test_command_is_frozen(self) -> None:
        """UpdateSKUCommand is a frozen dataclass -- mutation raises."""
        cmd = UpdateSKUCommand(product_id=uuid.uuid4(), sku_id=uuid.uuid4())
        with pytest.raises(FrozenInstanceError):
            cmd.sku_code = "mutated"  # type: ignore[misc]

    def test_all_optional_fields_accept_values(self) -> None:
        """All optional fields accept explicit values."""
        attr_id = uuid.uuid4()
        val_id = uuid.uuid4()
        cmd = UpdateSKUCommand(
            product_id=uuid.uuid4(),
            sku_id=uuid.uuid4(),
            sku_code="NEW-CODE",
            price_amount=5000,
            price_currency="EUR",
            compare_at_price_amount=7000,
            is_active=False,
            variant_attributes=[(attr_id, val_id)],
            version=3,
        )
        assert cmd.sku_code == "NEW-CODE"
        assert cmd.price_amount == 5000
        assert cmd.price_currency == "EUR"
        assert cmd.compare_at_price_amount == 7000
        assert cmd.is_active is False
        assert cmd.variant_attributes == [(attr_id, val_id)]
        assert cmd.version == 3

    def test_compare_at_price_amount_none_vs_not_provided(self) -> None:
        """Explicit None with _provided_fields differs from not-provided default."""
        cmd_default = UpdateSKUCommand(product_id=uuid.uuid4(), sku_id=uuid.uuid4())
        cmd_none = UpdateSKUCommand(
            product_id=uuid.uuid4(),
            sku_id=uuid.uuid4(),
            compare_at_price_amount=None,
            _provided_fields=frozenset({"compare_at_price_amount"}),
        )
        assert "compare_at_price_amount" not in cmd_default._provided_fields
        assert "compare_at_price_amount" in cmd_none._provided_fields


# ---------------------------------------------------------------------------
# UpdateSKUResult
# ---------------------------------------------------------------------------


class TestUpdateSKUResult:
    """Tests for UpdateSKUResult DTO."""

    def test_stores_sku_id(self) -> None:
        """id field stores the provided UUID."""
        sid = uuid.uuid4()
        result = UpdateSKUResult(id=sid)
        assert result.id == sid

    def test_result_is_frozen(self) -> None:
        """UpdateSKUResult is frozen -- mutation raises."""
        result = UpdateSKUResult(id=uuid.uuid4())
        with pytest.raises(FrozenInstanceError):
            result.id = uuid.uuid4()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# UpdateSKUHandler -- happy path
# ---------------------------------------------------------------------------


class TestUpdateSKUHandlerHappyPath:
    """Handler tests when product and SKU exist and version matches."""

    async def test_returns_result_with_sku_id(self) -> None:
        """Handler returns UpdateSKUResult with the correct SKU id."""
        sku = make_sku()
        product = make_product(skus=[sku])
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(
            product_id=product.id,
            sku_id=sku.id,
            sku_code="UPDATED-CODE",
        )
        result = await handler.handle(cmd)

        assert isinstance(result, UpdateSKUResult)
        assert result.id == sku.id

    async def test_calls_repo_get_with_variants(self) -> None:
        """Handler calls get_with_variants with the product_id from command."""
        sku = make_sku()
        product = make_product(skus=[sku])
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(product_id=product.id, sku_id=sku.id, sku_code="X")
        await handler.handle(cmd)

        repo.get_with_variants.assert_awaited_once_with(product.id)

    async def test_calls_repo_update_and_uow_commit(self) -> None:
        """Handler calls repo.update(product) and uow.commit() on success."""
        sku = make_sku()
        product = make_product(skus=[sku])
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(product_id=product.id, sku_id=sku.id, sku_code="X")
        await handler.handle(cmd)

        repo.update.assert_awaited_once_with(product)
        uow.commit.assert_awaited_once()

    async def test_calls_sku_update_with_sku_code(self) -> None:
        """When sku_code is provided, it is forwarded to sku.update()."""
        sku = make_sku()
        product = make_product(skus=[sku])
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(product_id=product.id, sku_id=sku.id, sku_code="NEW-SKU")
        await handler.handle(cmd)

        sku.update.assert_called_once()
        call_kwargs = sku.update.call_args[1]
        assert call_kwargs["sku_code"] == "NEW-SKU"

    async def test_calls_sku_update_with_is_active(self) -> None:
        """When is_active is provided, it is forwarded to sku.update()."""
        sku = make_sku()
        product = make_product(skus=[sku])
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(product_id=product.id, sku_id=sku.id, is_active=False)
        await handler.handle(cmd)

        call_kwargs = sku.update.call_args[1]
        assert call_kwargs["is_active"] is False

    async def test_uow_used_as_context_manager(self) -> None:
        """Handler enters and exits the UoW async context manager."""
        sku = make_sku()
        product = make_product(skus=[sku])
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(product_id=product.id, sku_id=sku.id, sku_code="X")
        await handler.handle(cmd)

        uow.__aenter__.assert_awaited_once()
        uow.__aexit__.assert_awaited_once()

    async def test_no_fields_provided_calls_update_with_empty_kwargs(self) -> None:
        """When no optional fields are set, sku.update() is called with no kwargs."""
        sku = make_sku()
        product = make_product(skus=[sku])
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(product_id=product.id, sku_id=sku.id)
        await handler.handle(cmd)

        sku.update.assert_called_once()
        call_kwargs = sku.update.call_args[1]
        assert call_kwargs == {}


# ---------------------------------------------------------------------------
# UpdateSKUHandler -- product not found
# ---------------------------------------------------------------------------


class TestUpdateSKUHandlerProductNotFound:
    """Handler tests when the product does not exist."""

    async def test_raises_product_not_found_error(self) -> None:
        """Handler raises ProductNotFoundError when get_with_variants returns None."""
        repo = make_product_repo(product=None)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        pid = uuid.uuid4()
        cmd = UpdateSKUCommand(product_id=pid, sku_id=uuid.uuid4())

        with pytest.raises(ProductNotFoundError):
            await handler.handle(cmd)

    async def test_no_commit_on_product_not_found(self) -> None:
        """When product is not found, uow.commit must not be called."""
        repo = make_product_repo(product=None)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(product_id=uuid.uuid4(), sku_id=uuid.uuid4())

        with pytest.raises(ProductNotFoundError):
            await handler.handle(cmd)

        uow.commit.assert_not_awaited()

    async def test_no_repo_update_on_product_not_found(self) -> None:
        """When product is not found, repo.update must not be called."""
        repo = make_product_repo(product=None)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(product_id=uuid.uuid4(), sku_id=uuid.uuid4())

        with pytest.raises(ProductNotFoundError):
            await handler.handle(cmd)

        repo.update.assert_not_awaited()


# ---------------------------------------------------------------------------
# UpdateSKUHandler -- SKU not found
# ---------------------------------------------------------------------------


class TestUpdateSKUHandlerSKUNotFound:
    """Handler tests when the SKU does not exist within the product."""

    async def test_raises_sku_not_found_error(self) -> None:
        """Handler raises SKUNotFoundError when find_sku returns None."""
        product = make_product(skus=[])
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(product_id=product.id, sku_id=uuid.uuid4())

        with pytest.raises(SKUNotFoundError):
            await handler.handle(cmd)

    async def test_no_commit_on_sku_not_found(self) -> None:
        """When SKU is not found, uow.commit must not be called."""
        product = make_product(skus=[])
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(product_id=product.id, sku_id=uuid.uuid4())

        with pytest.raises(SKUNotFoundError):
            await handler.handle(cmd)

        uow.commit.assert_not_awaited()

    async def test_soft_deleted_sku_treated_as_not_found(self) -> None:
        """A soft-deleted SKU is not returned by find_sku."""
        deleted_sku = make_sku(deleted_at=datetime.now(UTC))
        product = make_product(skus=[deleted_sku])
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(product_id=product.id, sku_id=deleted_sku.id)

        with pytest.raises(SKUNotFoundError):
            await handler.handle(cmd)


# ---------------------------------------------------------------------------
# UpdateSKUHandler -- optimistic locking (version check)
# ---------------------------------------------------------------------------


class TestUpdateSKUHandlerConcurrency:
    """Handler tests for optimistic locking version checks."""

    async def test_version_mismatch_raises_concurrency_error(self) -> None:
        """ConcurrencyError is raised when command.version != sku.version."""
        sku = make_sku(version=2)
        product = make_product(skus=[sku])
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(
            product_id=product.id,
            sku_id=sku.id,
            sku_code="UPDATED",
            version=1,  # stale version
        )

        with pytest.raises(ConcurrencyError):
            await handler.handle(cmd)

    async def test_no_commit_on_version_mismatch(self) -> None:
        """When version mismatches, uow.commit must not be called."""
        sku = make_sku(version=5)
        product = make_product(skus=[sku])
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(product_id=product.id, sku_id=sku.id, version=3)

        with pytest.raises(ConcurrencyError):
            await handler.handle(cmd)

        uow.commit.assert_not_awaited()

    async def test_matching_version_proceeds(self) -> None:
        """When version matches, handler proceeds normally."""
        sku = make_sku(version=3)
        product = make_product(skus=[sku])
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(
            product_id=product.id,
            sku_id=sku.id,
            sku_code="VALID",
            version=3,
        )
        result = await handler.handle(cmd)

        assert result.id == sku.id
        uow.commit.assert_awaited_once()

    async def test_none_version_skips_check(self) -> None:
        """When command.version is None, optimistic lock check is skipped."""
        sku = make_sku(version=99)
        product = make_product(skus=[sku])
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(
            product_id=product.id,
            sku_id=sku.id,
            sku_code="NO-VERSION-CHECK",
            version=None,
        )
        result = await handler.handle(cmd)

        assert result.id == sku.id
        uow.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# UpdateSKUHandler -- variant attributes + hash recomputation
# ---------------------------------------------------------------------------


class TestUpdateSKUHandlerVariantAttributes:
    """Handler tests for variant attribute changes and hash uniqueness."""

    async def test_variant_attributes_recomputes_hash(self) -> None:
        """When variant_attributes are provided, handler recomputes variant_hash."""
        sku = make_sku()
        product = make_product(skus=[sku])
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        attr_id = uuid.uuid4()
        val_id = uuid.uuid4()
        cmd = UpdateSKUCommand(
            product_id=product.id,
            sku_id=sku.id,
            variant_attributes=[(attr_id, val_id)],
        )
        await handler.handle(cmd)

        product.compute_variant_hash.assert_called_once_with([(attr_id, val_id)])
        call_kwargs = sku.update.call_args[1]
        assert "variant_attributes" in call_kwargs
        assert "variant_hash" in call_kwargs

    async def test_duplicate_variant_hash_raises_error(self) -> None:
        """DuplicateVariantCombinationError raised when hash collides with another SKU."""
        attr_id = uuid.uuid4()
        val_id = uuid.uuid4()

        import hashlib

        sorted_attrs = sorted([(attr_id, val_id)], key=lambda x: str(x[0]))
        payload = "|".join(f"{a!s}:{v!s}" for a, v in sorted_attrs)
        collision_hash = hashlib.sha256(payload.encode()).hexdigest()

        sku_to_update = make_sku(variant_hash="original_hash")
        other_sku = make_sku(
            sku_id=uuid.uuid4(),
            variant_hash=collision_hash,
            deleted_at=None,
        )
        product = make_product(skus=[sku_to_update, other_sku])
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(
            product_id=product.id,
            sku_id=sku_to_update.id,
            variant_attributes=[(attr_id, val_id)],
        )

        with pytest.raises(DuplicateVariantCombinationError):
            await handler.handle(cmd)

    async def test_deleted_sku_hash_collision_ignored(self) -> None:
        """Soft-deleted SKUs are excluded from variant hash uniqueness check."""
        attr_id = uuid.uuid4()
        val_id = uuid.uuid4()

        import hashlib

        sorted_attrs = sorted([(attr_id, val_id)], key=lambda x: str(x[0]))
        payload = "|".join(f"{a!s}:{v!s}" for a, v in sorted_attrs)
        collision_hash = hashlib.sha256(payload.encode()).hexdigest()

        sku_to_update = make_sku(variant_hash="original_hash")
        deleted_sku = make_sku(
            sku_id=uuid.uuid4(),
            variant_hash=collision_hash,
            deleted_at=datetime.now(UTC),
        )
        product = make_product(skus=[sku_to_update, deleted_sku])
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(
            product_id=product.id,
            sku_id=sku_to_update.id,
            variant_attributes=[(attr_id, val_id)],
        )
        result = await handler.handle(cmd)

        assert result.id == sku_to_update.id

    async def test_same_sku_hash_collision_ignored(self) -> None:
        """The SKU being updated is excluded from its own hash collision check."""
        attr_id = uuid.uuid4()
        val_id = uuid.uuid4()

        import hashlib

        sorted_attrs = sorted([(attr_id, val_id)], key=lambda x: str(x[0]))
        payload = "|".join(f"{a!s}:{v!s}" for a, v in sorted_attrs)
        same_hash = hashlib.sha256(payload.encode()).hexdigest()

        sku = make_sku(variant_hash=same_hash)
        product = make_product(skus=[sku])
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(
            product_id=product.id,
            sku_id=sku.id,
            variant_attributes=[(attr_id, val_id)],
        )
        result = await handler.handle(cmd)

        assert result.id == sku.id

    async def test_no_variant_attributes_skips_hash_computation(self) -> None:
        """When variant_attributes is None, hash is not recomputed."""
        sku = make_sku()
        product = make_product(skus=[sku])
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(product_id=product.id, sku_id=sku.id, sku_code="NEW")
        await handler.handle(cmd)

        product.compute_variant_hash.assert_not_called()
        call_kwargs = sku.update.call_args[1]
        assert "variant_hash" not in call_kwargs
        assert "variant_attributes" not in call_kwargs


# ---------------------------------------------------------------------------
# UpdateSKUHandler -- price updates
# ---------------------------------------------------------------------------


class TestUpdateSKUHandlerPrice:
    """Handler tests for price field updates."""

    async def test_price_amount_only_uses_existing_currency(self) -> None:
        """When only price_amount is provided, currency is taken from existing SKU price."""
        sku = make_sku(price=Money(amount=10000, currency="USD"))
        product = make_product(skus=[sku])
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(
            product_id=product.id,
            sku_id=sku.id,
            price_amount=15000,
        )
        await handler.handle(cmd)

        call_kwargs = sku.update.call_args[1]
        assert call_kwargs["price"] == Money(amount=15000, currency="USD")

    async def test_price_currency_only_uses_existing_amount(self) -> None:
        """When only price_currency is provided, amount is taken from existing SKU price."""
        sku = make_sku(price=Money(amount=10000, currency="USD"))
        product = make_product(skus=[sku])
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(
            product_id=product.id,
            sku_id=sku.id,
            price_currency="EUR",
        )
        await handler.handle(cmd)

        call_kwargs = sku.update.call_args[1]
        assert call_kwargs["price"] == Money(amount=10000, currency="EUR")

    async def test_both_price_fields_creates_new_money(self) -> None:
        """When both amount and currency are provided, a new Money is created."""
        sku = make_sku(price=Money(amount=10000, currency="USD"))
        product = make_product(skus=[sku])
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(
            product_id=product.id,
            sku_id=sku.id,
            price_amount=20000,
            price_currency="GBP",
        )
        await handler.handle(cmd)

        call_kwargs = sku.update.call_args[1]
        assert call_kwargs["price"] == Money(amount=20000, currency="GBP")

    async def test_no_price_fields_omits_price_from_kwargs(self) -> None:
        """When neither price_amount nor price_currency is set, price is not in kwargs."""
        sku = make_sku()
        product = make_product(skus=[sku])
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(product_id=product.id, sku_id=sku.id, sku_code="X")
        await handler.handle(cmd)

        call_kwargs = sku.update.call_args[1]
        assert "price" not in call_kwargs


# ---------------------------------------------------------------------------
# UpdateSKUHandler -- compare_at_price sentinel pattern
# ---------------------------------------------------------------------------


class TestUpdateSKUHandlerCompareAtPrice:
    """Handler tests for compare_at_price _provided_fields-based updates."""

    async def test_not_provided_omits_compare_at_price(self) -> None:
        """When compare_at_price_amount is not in _provided_fields, compare_at_price not in kwargs."""
        sku = make_sku()
        product = make_product(skus=[sku])
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(product_id=product.id, sku_id=sku.id, sku_code="X")
        await handler.handle(cmd)

        call_kwargs = sku.update.call_args[1]
        assert "compare_at_price" not in call_kwargs

    async def test_explicit_none_clears_compare_at_price(self) -> None:
        """When compare_at_price_amount is None, compare_at_price=None in kwargs."""
        sku = make_sku()
        product = make_product(skus=[sku])
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(
            product_id=product.id,
            sku_id=sku.id,
            compare_at_price_amount=None,
            _provided_fields=frozenset({"compare_at_price_amount"}),
        )
        await handler.handle(cmd)

        call_kwargs = sku.update.call_args[1]
        assert call_kwargs["compare_at_price"] is None

    async def test_explicit_amount_sets_money_with_effective_currency(self) -> None:
        """When compare_at_price_amount is an int, Money is built with effective currency."""
        sku = make_sku(price=Money(amount=10000, currency="USD"))
        product = make_product(skus=[sku])
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(
            product_id=product.id,
            sku_id=sku.id,
            compare_at_price_amount=15000,
            _provided_fields=frozenset({"compare_at_price_amount"}),
        )
        await handler.handle(cmd)

        call_kwargs = sku.update.call_args[1]
        assert call_kwargs["compare_at_price"] == Money(amount=15000, currency="USD")

    async def test_compare_at_price_uses_new_currency_when_price_currency_changes(
        self,
    ) -> None:
        """When both price_currency and compare_at_price_amount change, new currency used."""
        sku = make_sku(price=Money(amount=10000, currency="USD"))
        product = make_product(skus=[sku])
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(
            product_id=product.id,
            sku_id=sku.id,
            price_currency="EUR",
            compare_at_price_amount=20000,
            _provided_fields=frozenset({"compare_at_price_amount", "price_currency"}),
        )
        await handler.handle(cmd)

        call_kwargs = sku.update.call_args[1]
        assert call_kwargs["compare_at_price"] == Money(amount=20000, currency="EUR")


# ---------------------------------------------------------------------------
# UpdateSKUHandler -- compare_at_price <= price validation
# ---------------------------------------------------------------------------


class TestUpdateSKUHandlerCompareAtPriceValidation:
    """Handler tests for compare_at_price vs price validation (delegated to SKU.update)."""

    async def test_compare_at_price_lte_price_raises_value_error(self) -> None:
        """ValueError when compare_at_price <= price (validated by SKU.update)."""
        sku = make_sku(price=Money(amount=10000, currency="USD"))
        # Make sku.update raise ValueError as the real SKU would
        sku.update = MagicMock(
            side_effect=ValueError("compare_at_price must be greater than price")
        )
        product = make_product(skus=[sku])
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = UpdateSKUHandler(product_repo=repo, uow=uow)

        cmd = UpdateSKUCommand(
            product_id=product.id,
            sku_id=sku.id,
            compare_at_price_amount=5000,  # less than price
            _provided_fields=frozenset({"compare_at_price_amount"}),
        )

        with pytest.raises(ValueError, match="compare_at_price must be greater than price"):
            await handler.handle(cmd)
