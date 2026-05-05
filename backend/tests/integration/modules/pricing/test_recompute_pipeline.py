"""Integration tests for the recompute pipeline (ADR-005a, PC-201d).

Exercises the catalog-side ``ApplySkuPricingResultHandler`` against a
real PostgreSQL session (test container savepoint), verifying the
end-to-end SQL outcomes promised by :class:`WriteOutcome`:

* APPLIED -- selling_price/status/version updated, audit row INSERTed,
  outbox event emitted via the UoW.
* FAILURE_PERSISTED -- pricing_status/failure_reason updated, audit
  row carries the ``failure_kind`` discriminator (ADR-005a Open Issue
  #3 -- ``"retry_exhausted"`` distinguishable from ordinary failure).
* VERSION_CONFLICT -- expected_version mismatch, no row mutation.

The ``RecomputeSkuPricingService`` retry-orchestration loop is covered
by unit tests (test_apply_sku_pricing_result.py) with mocked port +
real domain mutators; these integration tests focus on the
catalog-side write path that those unit tests cannot exercise.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import registry as _registry  # noqa: F401
from src.infrastructure.database.uow import UnitOfWork
from src.modules.catalog.application.commands.apply_sku_pricing_result import (
    ApplySkuPricingResultHandler,
)
from src.modules.catalog.domain.interfaces import (
    SkuPricingApplyRequest,
    SkuPricingFailureRequest,
    WriteOutcome,
)
from src.modules.catalog.domain.value_objects import Money, SkuPricingStatus
from src.modules.catalog.infrastructure.models import (
    SKU as SkuOrm,
)
from src.modules.catalog.infrastructure.models import (
    Brand as BrandOrm,
)
from src.modules.catalog.infrastructure.models import (
    Category as CategoryOrm,
)
from src.modules.catalog.infrastructure.models import (
    SkuPricingHistoryModel,
)
from src.modules.catalog.infrastructure.repositories import ProductRepository
from src.modules.catalog.infrastructure.repositories.sku_pricing_history import (
    SkuPricingHistoryRepository,
)
from src.modules.geo.infrastructure.models import CurrencyModel
from src.modules.pricing.infrastructure.models import FormulaVersionModel
from tests.factories.product_builder import ProductBuilder
from tests.factories.sku_builder import SKUBuilder

pytestmark = pytest.mark.integration


def _make_logger() -> MagicMock:
    """Real-ish logger -- structlog returns chainable bind()."""
    return structlog.get_logger("test")


async def _ensure_rub_currency(session: AsyncSession) -> None:
    """Ensure a RUB currency row exists for FK resolution.

    ProductVariant.default_currency FKs to currencies.code; integration
    DB starts empty so we insert a minimal row idempotently.
    """
    existing = await session.execute(
        select(CurrencyModel).where(CurrencyModel.code == "RUB")
    )
    if existing.scalar_one_or_none() is not None:
        return
    session.add(
        CurrencyModel(
            code="RUB",
            numeric="643",
            name="Russian Ruble",
            minor_unit=2,
            is_active=True,
        )
    )
    await session.flush()


async def _seed_brand_and_category(
    session: AsyncSession,
) -> tuple[uuid.UUID, uuid.UUID]:
    """Insert a Brand + Category row so Product FKs can resolve."""
    await _ensure_rub_currency(session)
    brand_id = uuid.uuid4()
    category_id = uuid.uuid4()
    session.add(
        BrandOrm(
            id=brand_id,
            name=f"Brand-{brand_id.hex[:6]}",
            slug=f"brand-{brand_id.hex[:6]}",
        )
    )
    session.add(
        CategoryOrm(
            id=category_id,
            name_i18n={"en": "Test category"},
            slug=f"cat-{category_id.hex[:6]}",
            full_slug=f"cat-{category_id.hex[:6]}",
            level=0,
            sort_order=0,
        )
    )
    await session.flush()
    return brand_id, category_id


async def _seed_formula_version(session: AsyncSession) -> uuid.UUID:
    """Insert a pricing_formula_versions row so SKU.priced_with_formula_version_id FK resolves."""
    formula_id = uuid.uuid4()
    session.add(
        FormulaVersionModel(
            id=formula_id,
            context_id=uuid.uuid4(),
            version_number=1,
            status="draft",
            ast={},
        )
    )
    await session.flush()
    return formula_id


async def _seed_priced_pending_sku(
    session: AsyncSession,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    """Persist a Product+Variant+SKU triple in PENDING state.

    Returns ``(product_id, variant_id, sku_id, formula_version_id)`` for
    downstream test construction of apply requests; the formula_version
    row is required because SKU.priced_with_formula_version_id has a
    FK constraint on the apply path.
    """
    brand_id, category_id = await _seed_brand_and_category(session)
    formula_version_id = await _seed_formula_version(session)
    product = (
        ProductBuilder().with_brand_id(brand_id).with_category_id(category_id).build()
    )
    sku = (
        SKUBuilder()
        .for_product(product)
        .for_variant(product.variants[0].id)
        .with_sku_code(f"TEST-SKU-{uuid.uuid4().hex[:6]}")
        .with_price(Money(amount=10000, currency="RUB"))
        .build()
    )
    # Force PENDING state -- the recompute pipeline normally arrives
    # only after Product->SKU has been transitioned to PENDING.
    sku.pricing_status = SkuPricingStatus.PENDING
    product.clear_domain_events()

    repo = ProductRepository(session)
    await repo.add(product)
    await session.flush()
    return product.id, product.variants[0].id, sku.id, formula_version_id


def _build_handler(session: AsyncSession) -> ApplySkuPricingResultHandler:
    return ApplySkuPricingResultHandler(
        product_repo=ProductRepository(session),
        history_repo=SkuPricingHistoryRepository(session),
        uow=UnitOfWork(session),
        logger=_make_logger(),
    )


# ---------------------------------------------------------------------------
# apply_success -- happy path
# ---------------------------------------------------------------------------


async def test_apply_success_persists_priced_state_and_audit_row(
    db_session: AsyncSession,
) -> None:
    (
        product_id,
        _variant_id,
        sku_id,
        formula_version_id,
    ) = await _seed_priced_pending_sku(db_session)
    handler = _build_handler(db_session)
    inputs_hash = "a" * 64

    outcome = await handler.apply_success(
        SkuPricingApplyRequest(
            product_id=product_id,
            sku_id=sku_id,
            expected_version=1,
            previous_status="pending",
            selling_price_minor=12500,
            selling_currency="RUB",
            formula_version_id=formula_version_id,
            inputs_hash=inputs_hash,
            priced_at=datetime.now(UTC),
            correlation_id="corr-int-success",
        )
    )

    assert outcome is WriteOutcome.APPLIED

    # SKU row reflects the priced state.
    refreshed = await db_session.get(SkuOrm, sku_id)
    assert refreshed is not None
    assert refreshed.selling_price == 12500
    assert refreshed.selling_currency == "RUB"
    assert refreshed.pricing_status is SkuPricingStatus.PRICED
    assert refreshed.priced_inputs_hash == inputs_hash
    assert refreshed.priced_at is not None
    assert refreshed.priced_failure_reason is None
    assert refreshed.version == 2  # incremented from initial 1

    # Audit row recorded the transition.
    history = (
        await db_session.execute(
            select(SkuPricingHistoryModel).where(
                SkuPricingHistoryModel.sku_id == sku_id
            )
        )
    ).scalar_one()
    assert history.new_status == "priced"
    assert history.previous_status == "pending"
    assert history.selling_price == 12500
    assert history.selling_currency == "RUB"
    assert history.inputs_hash == inputs_hash
    assert history.failure_reason is None
    assert history.failure_kind is None
    assert history.correlation_id == "corr-int-success"


# ---------------------------------------------------------------------------
# apply_failure -- retry_exhausted discriminator persisted
# ---------------------------------------------------------------------------


async def test_apply_failure_persists_retry_exhausted_failure_kind(
    db_session: AsyncSession,
) -> None:
    (
        product_id,
        _variant_id,
        sku_id,
        _formula_version_id,
    ) = await _seed_priced_pending_sku(db_session)
    handler = _build_handler(db_session)

    outcome = await handler.apply_failure(
        SkuPricingFailureRequest(
            product_id=product_id,
            sku_id=sku_id,
            expected_version=1,
            previous_status="pending",
            pricing_status="formula_error",
            failure_reason="Optimistic-lock retries exhausted",
            failure_kind="retry_exhausted",
            correlation_id="corr-int-retry",
        )
    )

    assert outcome is WriteOutcome.FAILURE_PERSISTED

    refreshed = await db_session.get(SkuOrm, sku_id)
    assert refreshed is not None
    assert refreshed.pricing_status is SkuPricingStatus.FORMULA_ERROR
    assert refreshed.priced_failure_reason == "Optimistic-lock retries exhausted"
    assert refreshed.selling_price is None  # cleared on failure
    assert refreshed.version == 2

    history = (
        await db_session.execute(
            select(SkuPricingHistoryModel).where(
                SkuPricingHistoryModel.sku_id == sku_id
            )
        )
    ).scalar_one()
    assert history.new_status == "formula_error"
    assert history.failure_kind == "retry_exhausted"
    assert history.failure_reason == "Optimistic-lock retries exhausted"
    assert history.selling_price is None
    assert history.inputs_hash is None
    assert history.correlation_id == "corr-int-retry"


# ---------------------------------------------------------------------------
# apply_success -- version mismatch returns conflict, no mutation
# ---------------------------------------------------------------------------


async def test_apply_success_version_mismatch_returns_conflict_no_mutation(
    db_session: AsyncSession,
) -> None:
    (
        product_id,
        _variant_id,
        sku_id,
        formula_version_id,
    ) = await _seed_priced_pending_sku(db_session)
    handler = _build_handler(db_session)

    # Simulate a concurrent admin edit between the (unmocked) reader
    # snapshot and the apply -- the SKU.version drifts ahead of what
    # the pricing service captured.
    sku_orm = await db_session.get(SkuOrm, sku_id)
    assert sku_orm is not None
    sku_orm.version = 99  # drifted away
    await db_session.flush()

    outcome = await handler.apply_success(
        SkuPricingApplyRequest(
            product_id=product_id,
            sku_id=sku_id,
            expected_version=1,
            previous_status="pending",
            selling_price_minor=12500,
            selling_currency="RUB",
            formula_version_id=formula_version_id,
            inputs_hash="b" * 64,
            priced_at=datetime.now(UTC),
            correlation_id="corr-int-conflict",
        )
    )

    assert outcome is WriteOutcome.VERSION_CONFLICT

    # Row state is unchanged (still PENDING) -- handler returned before
    # touching pricing fields.
    refreshed = await db_session.get(SkuOrm, sku_id)
    assert refreshed is not None
    assert refreshed.pricing_status is SkuPricingStatus.PENDING
    assert refreshed.selling_price is None
    assert refreshed.version == 99  # only the drift bump, no apply bump

    # No audit row inserted.
    history_count = (
        await db_session.execute(
            select(SkuPricingHistoryModel).where(
                SkuPricingHistoryModel.sku_id == sku_id
            )
        )
    ).all()
    assert len(history_count) == 0
