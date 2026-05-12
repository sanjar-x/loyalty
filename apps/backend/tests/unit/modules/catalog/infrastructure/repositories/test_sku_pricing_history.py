"""Unit tests for SkuPricingHistoryRepository (ADR-005a).

Verifies that the concrete repository persists each PricingHistoryEntry
field (including the failure_kind discriminator added by ADR-005a Open
Issue #3) into a single INSERT statement. The repository is a thin
wrapper around session.execute, so we assert against the executed
statement compiled into a parameter dict rather than running real SQL.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import Insert

from src.modules.catalog.domain.interfaces import PricingHistoryEntry
from src.modules.catalog.infrastructure.repositories.sku_pricing_history import (
    SkuPricingHistoryRepository,
)


def _compiled_params(stmt: Insert) -> dict[str, object]:
    """Compile an SQLAlchemy Insert into its parameter dict."""
    compiled = stmt.compile(
        dialect=postgresql.dialect(),
        compile_kwargs={"render_postcompile": True},
    )
    return dict(compiled.params)


@pytest.mark.asyncio
class TestSkuPricingHistoryRepositoryAdd:
    async def test_add_passes_through_all_priced_fields(self):
        session = MagicMock()
        session.execute = AsyncMock(return_value=None)
        repo = SkuPricingHistoryRepository(session=session)
        formula_id = uuid.uuid4()
        sku_id = uuid.uuid4()

        await repo.add(
            PricingHistoryEntry(
                sku_id=sku_id,
                new_status="priced",
                previous_status="pending",
                selling_price=12500,
                selling_currency="RUB",
                formula_version_id=formula_id,
                inputs_hash="a" * 64,
                failure_reason=None,
                failure_kind=None,
                correlation_id="corr-123",
            )
        )

        session.execute.assert_awaited_once()
        await_args = session.execute.await_args
        assert await_args is not None
        stmt = await_args.args[0]
        assert isinstance(stmt, Insert)
        params = _compiled_params(stmt)
        assert params["sku_id"] == sku_id
        assert params["new_status"] == "priced"
        assert params["previous_status"] == "pending"
        assert params["selling_price"] == 12500
        assert params["selling_currency"] == "RUB"
        assert params["formula_version_id"] == formula_id
        assert params["inputs_hash"] == "a" * 64
        assert params["failure_reason"] is None
        assert params["failure_kind"] is None
        assert params["correlation_id"] == "corr-123"

    async def test_add_persists_retry_exhausted_failure_kind(self):
        session = MagicMock()
        session.execute = AsyncMock(return_value=None)
        repo = SkuPricingHistoryRepository(session=session)

        await repo.add(
            PricingHistoryEntry(
                sku_id=uuid.uuid4(),
                new_status="formula_error",
                previous_status="priced",
                selling_price=None,
                selling_currency=None,
                formula_version_id=None,
                inputs_hash=None,
                failure_reason="Optimistic-lock retries exhausted",
                failure_kind="retry_exhausted",
                correlation_id="corr-456",
            )
        )

        await_args = session.execute.await_args
        assert await_args is not None
        stmt = await_args.args[0]
        params = _compiled_params(stmt)
        assert params["failure_kind"] == "retry_exhausted"
        assert params["new_status"] == "formula_error"
        assert params["selling_price"] is None
        assert params["selling_currency"] is None
        assert params["inputs_hash"] is None

    async def test_add_does_not_commit_or_flush(self):
        session = MagicMock()
        session.execute = AsyncMock(return_value=None)
        repo = SkuPricingHistoryRepository(session=session)

        await repo.add(
            PricingHistoryEntry(
                sku_id=uuid.uuid4(),
                new_status="priced",
                previous_status=None,
                selling_price=100,
                selling_currency="RUB",
                formula_version_id=uuid.uuid4(),
                inputs_hash="b" * 64,
                failure_reason=None,
                failure_kind=None,
                correlation_id=None,
            )
        )

        # Caller's UoW owns commit/flush; repo only executes the insert.
        assert not session.commit.called
        assert not session.flush.called
