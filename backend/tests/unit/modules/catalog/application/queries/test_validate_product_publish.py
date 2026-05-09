"""Unit tests for ``ValidateProductPublishHandler`` (C1.1).

Builds in-memory Product aggregates via the ``ProductBuilder`` and
fakes the repository to assert the handler's verdict matches what the
real ``Product.transition_status(PUBLISHED)`` would do — without ever
mutating the aggregate.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from src.modules.catalog.application.queries.validate_product_publish import (
    ValidateProductPublishHandler,
    ValidateProductPublishQuery,
)
from src.modules.catalog.domain.exceptions import ProductNotFoundError
from src.modules.catalog.domain.value_objects import (
    Money,
    ProductStatus,
)
from tests.factories.product_builder import ProductBuilder

pytestmark = pytest.mark.unit


class _FakeRepo:
    def __init__(self, products: dict[uuid.UUID, Any] | None = None) -> None:
        self._products = products or {}

    async def get_with_variants(self, product_id: uuid.UUID):
        return self._products.get(product_id)


class _NullLogger:
    def bind(self, **_: Any) -> _NullLogger:
        return self

    def info(self, *_: Any, **__: Any) -> None: ...
    def warning(self, *_: Any, **__: Any) -> None: ...
    def error(self, *_: Any, **__: Any) -> None: ...
    def critical(self, *_: Any, **__: Any) -> None: ...
    def debug(self, *_: Any, **__: Any) -> None: ...
    def exception(self, *_: Any, **__: Any) -> None: ...


def _make_handler(product=None) -> ValidateProductPublishHandler:
    repo = _FakeRepo({product.id: product} if product is not None else {})
    return ValidateProductPublishHandler(
        repo=repo,  # ty: ignore[invalid-argument-type]
        logger=_NullLogger(),
    )


async def test_returns_404_like_when_product_not_found() -> None:
    handler = _make_handler(None)
    with pytest.raises(ProductNotFoundError):
        await handler.handle(ValidateProductPublishQuery(product_id=uuid.uuid4()))


async def test_draft_with_priced_sku_fails_status_gate() -> None:
    """DRAFT can only go to ENRICHING — PUBLISHED is unreachable."""
    product = ProductBuilder().build()
    variant_id = product.variants[0].id
    product.add_sku(variant_id, sku_code="SKU-1", price=Money(1000, "RUB"))

    handler = _make_handler(product)
    result = await handler.handle(ValidateProductPublishQuery(product_id=product.id))

    assert result.ok is False
    assert result.current_status == ProductStatus.DRAFT.value
    assert result.next_status == ProductStatus.PUBLISHED.value
    codes = {f.code for f in result.gate_failures}
    assert "STATUS_NOT_TRANSITIONABLE" in codes
    # FSM gate fails BEFORE pricing — so ALL_SKUS_UNPRICED is absent
    # because the SKU IS priced. NO_ACTIVE_SKU also absent.
    assert "ALL_SKUS_UNPRICED" not in codes
    assert "NO_ACTIVE_SKU" not in codes


async def test_ready_for_review_no_active_sku_fails() -> None:
    """READY_FOR_REVIEW + zero active SKUs → NO_ACTIVE_SKU + ALL_SKUS_UNPRICED both absent
    (no SKUs to be unpriced)."""
    product = ProductBuilder().build()
    # Add a priced SKU only to walk the FSM, then deactivate it.
    variant_id = product.variants[0].id
    sku = product.add_sku(variant_id, sku_code="SKU-1", price=Money(1000, "RUB"))
    product.transition_status(ProductStatus.ENRICHING)
    product.transition_status(ProductStatus.READY_FOR_REVIEW)
    sku.update(is_active=False)

    handler = _make_handler(product)
    result = await handler.handle(ValidateProductPublishQuery(product_id=product.id))

    assert result.ok is False
    codes = {f.code for f in result.gate_failures}
    assert "NO_ACTIVE_SKU" in codes
    # Status gate passes (READY_FOR_REVIEW → PUBLISHED is allowed).
    assert "STATUS_NOT_TRANSITIONABLE" not in codes
    # Empty active set → no per-SKU diagnostics.
    assert result.sku_diagnostics == []


async def test_ready_for_review_unpriced_sku_fails() -> None:
    """READY_FOR_REVIEW + active SKU without price → ALL_SKUS_UNPRICED."""
    product = ProductBuilder().build()
    variant_id = product.variants[0].id
    # Walk FSM with a priced SKU (publish gate passes), then drop its
    # price by deactivating it and adding a second variant with an
    # unpriced SKU. ``variant_hash`` collisions on same-variant empty-
    # attribute SKUs prevent a second SKU on the same variant, so we
    # add a fresh variant for the unpriced row.
    sku_priced = product.add_sku(
        variant_id, sku_code="SKU-PRICED", price=Money(1000, "RUB")
    )
    product.transition_status(ProductStatus.ENRICHING)
    product.transition_status(ProductStatus.READY_FOR_REVIEW)

    new_variant = product.add_variant(name_i18n=_i18n_for_secondary())
    product.add_sku(new_variant.id, sku_code="SKU-UNPRICED", price=None)
    product.remove_sku(sku_priced.id)

    handler = _make_handler(product)
    result = await handler.handle(ValidateProductPublishQuery(product_id=product.id))

    assert result.ok is False
    codes = {f.code for f in result.gate_failures}
    assert "ALL_SKUS_UNPRICED" in codes
    assert "STATUS_NOT_TRANSITIONABLE" not in codes
    assert "NO_ACTIVE_SKU" not in codes
    # Diagnostic carries actionable next_step
    assert len(result.sku_diagnostics) == 1
    assert result.sku_diagnostics[0]["sku_code"] == "SKU-UNPRICED"
    assert result.sku_diagnostics[0]["has_manual_price"] is False
    assert result.sku_diagnostics[0]["has_selling_price"] is False


def _i18n_for_secondary() -> dict[str, str]:
    return {"en": "Secondary variant", "ru": "Доп. вариант"}


async def test_ready_for_review_priced_sku_passes() -> None:
    """The happy path: ok=true, no failures, diagnostics surface the priced SKU."""
    product = ProductBuilder().build()
    variant_id = product.variants[0].id
    product.add_sku(variant_id, sku_code="SKU-OK", price=Money(1000, "RUB"))
    product.transition_status(ProductStatus.ENRICHING)
    product.transition_status(ProductStatus.READY_FOR_REVIEW)

    handler = _make_handler(product)
    result = await handler.handle(ValidateProductPublishQuery(product_id=product.id))

    assert result.ok is True
    assert result.gate_failures == []
    assert result.current_status == ProductStatus.READY_FOR_REVIEW.value
    assert result.next_status == ProductStatus.PUBLISHED.value
    assert len(result.sku_diagnostics) == 1
    assert result.sku_diagnostics[0]["has_manual_price"] is True


async def test_handler_does_not_mutate_aggregate() -> None:
    """Read-only contract — current status stays put even when ok=true.

    Locks the no-side-effect promise: subsequent calls observe identical state.
    """
    product = ProductBuilder().build()
    variant_id = product.variants[0].id
    product.add_sku(variant_id, sku_code="SKU-OK", price=Money(1000, "RUB"))
    product.transition_status(ProductStatus.ENRICHING)
    product.transition_status(ProductStatus.READY_FOR_REVIEW)

    status_before = product.status
    pending_events_before = len(product.domain_events)

    handler = _make_handler(product)
    await handler.handle(ValidateProductPublishQuery(product_id=product.id))
    await handler.handle(ValidateProductPublishQuery(product_id=product.id))

    assert product.status == status_before
    assert len(product.domain_events) == pending_events_before


async def test_published_product_fails_status_gate() -> None:
    """A PUBLISHED product cannot re-publish (PUBLISHED → ARCHIVED only)."""
    product = ProductBuilder().build()
    variant_id = product.variants[0].id
    product.add_sku(variant_id, sku_code="SKU-PUB", price=Money(1000, "RUB"))
    product.transition_status(ProductStatus.ENRICHING)
    product.transition_status(ProductStatus.READY_FOR_REVIEW)
    product.transition_status(ProductStatus.PUBLISHED)

    handler = _make_handler(product)
    result = await handler.handle(ValidateProductPublishQuery(product_id=product.id))

    assert result.ok is False
    codes = {f.code for f in result.gate_failures}
    assert codes == {"STATUS_NOT_TRANSITIONABLE"}
