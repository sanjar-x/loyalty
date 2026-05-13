"""Integration test for ``ValidateProductPublishHandler`` (C1.1).

Walks a real Product through the FSM via repo + handler and asserts the
verdict structure on real data, including per-SKU diagnostics.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.validate_product_publish import (
    ValidateProductPublishHandler,
    ValidateProductPublishQuery,
)
from src.modules.catalog.domain.entities import Product
from src.modules.catalog.domain.value_objects import (
    Money,
    ProductStatus,
)
from src.modules.catalog.infrastructure.repositories.product import ProductRepository

pytestmark = pytest.mark.integration


class _NullLogger:
    def bind(self, **_: Any) -> _NullLogger:
        return self

    def info(self, *_: Any, **__: Any) -> None: ...
    def warning(self, *_: Any, **__: Any) -> None: ...
    def error(self, *_: Any, **__: Any) -> None: ...
    def critical(self, *_: Any, **__: Any) -> None: ...
    def debug(self, *_: Any, **__: Any) -> None: ...
    def exception(self, *_: Any, **__: Any) -> None: ...


async def _seed_ready_for_review_product(
    db_session: AsyncSession,
    seed_product_deps: dict[str, uuid.UUID],
) -> Product:
    """Insert a product walked to READY_FOR_REVIEW with one priced SKU."""
    repo = ProductRepository(session=db_session)
    product = Product.create(
        slug=f"vp-{uuid.uuid4().hex[:8]}",
        title_i18n={"en": "VP Product", "ru": "Тестовый VP"},
        brand_id=seed_product_deps["brand_id"],
        primary_category_id=seed_product_deps["category_id"],
    )
    variant_id = product.variants[0].id
    product.add_sku(variant_id, sku_code="SKU-VP-1", price=Money(1500, "RUB"))
    product.transition_status(ProductStatus.ENRICHING)
    product.transition_status(ProductStatus.READY_FOR_REVIEW)
    await repo.add(product)
    await db_session.flush()
    return product


async def test_handler_returns_ok_for_published_ready_product(
    db_session: AsyncSession,
    seed_product_deps: dict[str, uuid.UUID],
) -> None:
    product = await _seed_ready_for_review_product(db_session, seed_product_deps)

    repo = ProductRepository(session=db_session)
    handler = ValidateProductPublishHandler(
        repo=repo,
        logger=_NullLogger(),
    )

    result = await handler.handle(ValidateProductPublishQuery(product_id=product.id))

    assert result.ok is True
    assert result.gate_failures == []
    assert result.current_status == ProductStatus.READY_FOR_REVIEW.value
    assert result.next_status == ProductStatus.PUBLISHED.value
    assert len(result.sku_diagnostics) == 1
    diag = result.sku_diagnostics[0]
    assert diag["sku_code"] == "SKU-VP-1"
    assert diag["has_manual_price"] is True
    assert diag["pricing_status"] == "legacy"


async def test_handler_returns_ok_false_for_draft_with_diagnostics(
    db_session: AsyncSession,
    seed_product_deps: dict[str, uuid.UUID],
) -> None:
    """DRAFT carries STATUS_NOT_TRANSITIONABLE + NO_ACTIVE_SKU."""
    repo = ProductRepository(session=db_session)
    product = Product.create(
        slug=f"vp-draft-{uuid.uuid4().hex[:8]}",
        title_i18n={"en": "Draft", "ru": "Черновик"},
        brand_id=seed_product_deps["brand_id"],
        primary_category_id=seed_product_deps["category_id"],
    )
    await repo.add(product)
    await db_session.flush()

    handler = ValidateProductPublishHandler(
        repo=repo,
        logger=_NullLogger(),
    )
    result = await handler.handle(ValidateProductPublishQuery(product_id=product.id))

    assert result.ok is False
    codes = {f.code for f in result.gate_failures}
    assert "STATUS_NOT_TRANSITIONABLE" in codes
    assert "NO_ACTIVE_SKU" in codes
    # No active SKUs → empty diagnostics list.
    assert result.sku_diagnostics == []
