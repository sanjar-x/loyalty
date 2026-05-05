"""Unit tests for ApplySkuPricingResultHandler (ADR-005a).

Verifies the catalog-side apply path of the pricing recompute pipeline:
WriteOutcome discrimination, hash-noop short-circuit, version-conflict
detection, mutation through SKU domain mutators, audit row persistence,
and domain event emission on the Product aggregate.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.catalog.application.commands.apply_sku_pricing_result import (
    ApplySkuPricingResultHandler,
)
from src.modules.catalog.domain.entities import SKU
from src.modules.catalog.domain.events import SKUPricedEvent, SKUPricingFailedEvent
from src.modules.catalog.domain.interfaces import (
    PricingHistoryEntry,
    SkuPricingApplyRequest,
    SkuPricingFailureRequest,
    WriteOutcome,
)
from src.modules.catalog.domain.value_objects import Money, SkuPricingStatus
from tests.fakes.fake_uow import FakeUnitOfWork

_PRODUCT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_VARIANT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
_SKU_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
_FORMULA_VERSION_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
_INPUTS_HASH = "a" * 64
_OTHER_HASH = "b" * 64


def _make_logger() -> MagicMock:
    """Create a mock logger that supports .bind() chaining."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    return logger


def _make_sku(
    *,
    version: int = 1,
    pricing_status: SkuPricingStatus = SkuPricingStatus.PENDING,
    priced_inputs_hash: str | None = None,
) -> SKU:
    """Construct a minimal SKU in a controllable state.

    PRICED status requires both ``selling_price`` and ``priced_inputs_hash``
    per SKU invariants (``__attrs_post_init__`` enforces this); we
    populate consistent provenance fields when the caller asks for the
    PRICED pre-state.
    """
    if pricing_status is SkuPricingStatus.PRICED:
        return SKU(
            id=_SKU_ID,
            product_id=_PRODUCT_ID,
            variant_id=_VARIANT_ID,
            sku_code="TEST-SKU-001",
            variant_hash="dummyhash",
            version=version,
            pricing_status=pricing_status,
            priced_inputs_hash=priced_inputs_hash,
            selling_price=Money(amount=12500, currency="RUB"),
            priced_with_formula_version_id=_FORMULA_VERSION_ID,
            priced_at=datetime.now(UTC),
        )
    return SKU(
        id=_SKU_ID,
        product_id=_PRODUCT_ID,
        variant_id=_VARIANT_ID,
        sku_code="TEST-SKU-001",
        variant_hash="dummyhash",
        version=version,
        pricing_status=pricing_status,
        priced_inputs_hash=priced_inputs_hash,
    )


def _make_product_with_sku(sku: SKU) -> MagicMock:
    """Mock Product aggregate that returns the given SKU from find_sku."""
    product = MagicMock()
    product.find_sku = MagicMock(return_value=sku)
    product.add_domain_event = MagicMock()
    return product


def _make_apply_request(
    *,
    expected_version: int = 1,
    inputs_hash: str = _INPUTS_HASH,
    selling_price_minor: int = 12500,
) -> SkuPricingApplyRequest:
    return SkuPricingApplyRequest(
        product_id=_PRODUCT_ID,
        sku_id=_SKU_ID,
        expected_version=expected_version,
        previous_status="pending",
        selling_price_minor=selling_price_minor,
        selling_currency="RUB",
        formula_version_id=_FORMULA_VERSION_ID,
        inputs_hash=inputs_hash,
        priced_at=datetime.now(UTC),
        correlation_id="corr-123",
    )


def _make_failure_request(
    *,
    expected_version: int = 1,
    pricing_status: str = "formula_error",
    failure_kind: str | None = None,
) -> SkuPricingFailureRequest:
    return SkuPricingFailureRequest(
        product_id=_PRODUCT_ID,
        sku_id=_SKU_ID,
        expected_version=expected_version,
        previous_status="pending",
        pricing_status=pricing_status,
        failure_reason="Division by zero in formula AST",
        failure_kind=failure_kind,
        correlation_id="corr-456",
    )


def _make_handler(
    *,
    product: MagicMock | None,
    history_repo: AsyncMock | None = None,
) -> tuple[ApplySkuPricingResultHandler, AsyncMock, AsyncMock, FakeUnitOfWork]:
    product_repo = AsyncMock()
    product_repo.get_for_update_with_variants = AsyncMock(return_value=product)
    product_repo.update = AsyncMock(return_value=product)
    if history_repo is None:
        history_repo = AsyncMock()
    uow = FakeUnitOfWork()
    handler = ApplySkuPricingResultHandler(
        product_repo=product_repo,
        history_repo=history_repo,
        uow=uow,
        logger=_make_logger(),
    )
    return handler, product_repo, history_repo, uow


# ---------------------------------------------------------------------------
# apply_success
# ---------------------------------------------------------------------------


class TestApplySuccess:
    @pytest.mark.asyncio
    async def test_happy_path_returns_applied_and_mutates_sku(self):
        sku = _make_sku()
        product = _make_product_with_sku(sku)
        handler, product_repo, history_repo, uow = _make_handler(product=product)

        outcome = await handler.apply_success(_make_apply_request())

        assert outcome is WriteOutcome.APPLIED
        assert sku.pricing_status is SkuPricingStatus.PRICED
        assert sku.priced_inputs_hash == _INPUTS_HASH
        assert sku.selling_price == Money(amount=12500, currency="RUB")
        product_repo.update.assert_awaited_once_with(product)
        history_repo.add.assert_awaited_once()
        history_entry = history_repo.add.await_args.args[0]
        assert isinstance(history_entry, PricingHistoryEntry)
        assert history_entry.new_status == SkuPricingStatus.PRICED.value
        assert history_entry.failure_kind is None
        product.add_domain_event.assert_called_once()
        event = product.add_domain_event.call_args.args[0]
        assert isinstance(event, SKUPricedEvent)
        assert event.sku_id == _SKU_ID
        assert uow.committed

    @pytest.mark.asyncio
    async def test_hash_match_returns_noop_without_mutation(self):
        sku = _make_sku(
            pricing_status=SkuPricingStatus.PRICED,
            priced_inputs_hash=_INPUTS_HASH,
        )
        product = _make_product_with_sku(sku)
        handler, product_repo, history_repo, _uow = _make_handler(product=product)

        outcome = await handler.apply_success(_make_apply_request())

        assert outcome is WriteOutcome.HASH_NOOP
        product_repo.update.assert_not_awaited()
        history_repo.add.assert_not_awaited()
        product.add_domain_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_hash_match_takes_priority_over_version_drift(self):
        # Even if version drifted, identical hash means desired state.
        sku = _make_sku(
            version=99,
            pricing_status=SkuPricingStatus.PRICED,
            priced_inputs_hash=_INPUTS_HASH,
        )
        product = _make_product_with_sku(sku)
        handler, _, history_repo, _ = _make_handler(product=product)

        outcome = await handler.apply_success(_make_apply_request(expected_version=1))

        assert outcome is WriteOutcome.HASH_NOOP
        history_repo.add.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_version_mismatch_returns_conflict(self):
        sku = _make_sku(version=42)
        product = _make_product_with_sku(sku)
        handler, product_repo, history_repo, _ = _make_handler(product=product)

        outcome = await handler.apply_success(_make_apply_request(expected_version=1))

        assert outcome is WriteOutcome.VERSION_CONFLICT
        product_repo.update.assert_not_awaited()
        history_repo.add.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_product_not_found_returns_conflict(self):
        handler, product_repo, history_repo, _ = _make_handler(product=None)

        outcome = await handler.apply_success(_make_apply_request())

        assert outcome is WriteOutcome.VERSION_CONFLICT
        product_repo.update.assert_not_awaited()
        history_repo.add.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_sku_not_found_returns_conflict(self):
        product = MagicMock()
        product.find_sku = MagicMock(return_value=None)
        handler, _, history_repo, _ = _make_handler(product=product)

        outcome = await handler.apply_success(_make_apply_request())

        assert outcome is WriteOutcome.VERSION_CONFLICT
        history_repo.add.assert_not_awaited()


# ---------------------------------------------------------------------------
# apply_failure
# ---------------------------------------------------------------------------


class TestApplyFailure:
    @pytest.mark.asyncio
    async def test_happy_path_returns_failure_persisted(self):
        sku = _make_sku()
        product = _make_product_with_sku(sku)
        handler, product_repo, history_repo, uow = _make_handler(product=product)

        outcome = await handler.apply_failure(
            _make_failure_request(pricing_status="stale_fx")
        )

        assert outcome is WriteOutcome.FAILURE_PERSISTED
        assert sku.pricing_status is SkuPricingStatus.STALE_FX
        assert sku.priced_failure_reason == "Division by zero in formula AST"
        assert sku.selling_price is None
        product_repo.update.assert_awaited_once_with(product)
        history_repo.add.assert_awaited_once()
        history_entry = history_repo.add.await_args.args[0]
        assert history_entry.new_status == "stale_fx"
        assert history_entry.failure_reason == "Division by zero in formula AST"
        assert history_entry.failure_kind is None
        product.add_domain_event.assert_called_once()
        event = product.add_domain_event.call_args.args[0]
        assert isinstance(event, SKUPricingFailedEvent)
        assert event.pricing_status == "stale_fx"
        assert uow.committed

    @pytest.mark.asyncio
    async def test_retry_exhausted_kind_persisted_in_history(self):
        sku = _make_sku()
        product = _make_product_with_sku(sku)
        handler, _, history_repo, _ = _make_handler(product=product)

        outcome = await handler.apply_failure(
            _make_failure_request(
                pricing_status="formula_error",
                failure_kind="retry_exhausted",
            )
        )

        assert outcome is WriteOutcome.FAILURE_PERSISTED
        history_entry = history_repo.add.await_args.args[0]
        assert history_entry.failure_kind == "retry_exhausted"
        assert history_entry.new_status == "formula_error"

    @pytest.mark.asyncio
    async def test_version_mismatch_returns_conflict(self):
        sku = _make_sku(version=42)
        product = _make_product_with_sku(sku)
        handler, product_repo, history_repo, _ = _make_handler(product=product)

        outcome = await handler.apply_failure(_make_failure_request(expected_version=1))

        assert outcome is WriteOutcome.VERSION_CONFLICT
        product_repo.update.assert_not_awaited()
        history_repo.add.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_invalid_pricing_status_raises(self):
        sku = _make_sku()
        product = _make_product_with_sku(sku)
        handler, _, _, _ = _make_handler(product=product)

        with pytest.raises(ValueError):
            await handler.apply_failure(
                _make_failure_request(pricing_status="not_a_real_status")
            )
