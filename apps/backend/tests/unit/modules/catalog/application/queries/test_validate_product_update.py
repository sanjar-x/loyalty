"""Unit tests for ``ValidateProductUpdateHandler`` (C1.2)."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from src.modules.catalog.application.queries.validate_product_update import (
    ValidateProductUpdateHandler,
    ValidateProductUpdateQuery,
)
from src.modules.catalog.domain.exceptions import ProductNotFoundError
from src.modules.catalog.domain.value_objects import Money
from tests.factories.product_builder import ProductBuilder

pytestmark = pytest.mark.unit


class _FakeProductRepo:
    def __init__(self, product=None) -> None:
        self._product = product
        self._slug_taken: set[str] = set()

    async def get_with_variants(self, product_id: uuid.UUID):
        if self._product is None or self._product.id != product_id:
            return None
        return self._product

    async def check_slug_exists_excluding(self, slug: str, _: uuid.UUID) -> bool:
        return slug in self._slug_taken


class _FakeBrandRepo:
    def __init__(self, *, known: set[uuid.UUID] | None = None) -> None:
        self._known = known or set()

    async def get(self, brand_id: uuid.UUID):
        return object() if brand_id in self._known else None


class _FakeCategoryRepo:
    def __init__(self, *, known: set[uuid.UUID] | None = None) -> None:
        self._known = known or set()

    async def get(self, category_id: uuid.UUID):
        return object() if category_id in self._known else None


class _NullLogger:
    def bind(self, **_: Any) -> _NullLogger:
        return self

    def info(self, *_: Any, **__: Any) -> None: ...
    def warning(self, *_: Any, **__: Any) -> None: ...
    def error(self, *_: Any, **__: Any) -> None: ...
    def critical(self, *_: Any, **__: Any) -> None: ...
    def debug(self, *_: Any, **__: Any) -> None: ...
    def exception(self, *_: Any, **__: Any) -> None: ...


def _make_handler(
    product=None,
    *,
    brand_known: set[uuid.UUID] | None = None,
    category_known: set[uuid.UUID] | None = None,
    slug_taken: set[str] | None = None,
):
    product_repo = _FakeProductRepo(product)
    if slug_taken:
        product_repo._slug_taken = slug_taken
    return ValidateProductUpdateHandler(
        product_repo=product_repo,  # ty: ignore[invalid-argument-type]
        brand_repo=_FakeBrandRepo(known=brand_known),  # ty: ignore[invalid-argument-type]
        category_repo=_FakeCategoryRepo(known=category_known),  # ty: ignore[invalid-argument-type]
        logger=_NullLogger(),
    )


async def test_returns_404_when_product_missing() -> None:
    handler = _make_handler(None)
    with pytest.raises(ProductNotFoundError):
        await handler.handle(
            ValidateProductUpdateQuery(
                product_id=uuid.uuid4(),
                _provided_fields=frozenset({"slug"}),
                slug="something",
            )
        )


async def test_diff_lists_only_changed_fields() -> None:
    product = ProductBuilder().with_slug("orig-slug").build()
    handler = _make_handler(product, brand_known={product.brand_id})
    new_brand_id = product.brand_id  # same — shouldn't appear in diff

    result = await handler.handle(
        ValidateProductUpdateQuery(
            product_id=product.id,
            slug="new-slug",
            brand_id=new_brand_id,
            _provided_fields=frozenset({"slug", "brand_id"}),
        )
    )

    fields = {d.field for d in result.diff}
    assert fields == {"slug"}  # brand_id unchanged → skipped
    assert result.ok is True


async def test_empty_title_produces_validation_error() -> None:
    product = ProductBuilder().build()
    handler = _make_handler(product)

    result = await handler.handle(
        ValidateProductUpdateQuery(
            product_id=product.id,
            title_i18n={},
            _provided_fields=frozenset({"title_i18n"}),
        )
    )

    assert result.ok is False
    codes = {e.code for e in result.validation_errors}
    assert "TITLE_EMPTY" in codes


async def test_unknown_brand_id_produces_validation_error() -> None:
    product = ProductBuilder().build()
    handler = _make_handler(product, brand_known=set())  # nothing known

    new_brand_id = uuid.uuid4()
    result = await handler.handle(
        ValidateProductUpdateQuery(
            product_id=product.id,
            brand_id=new_brand_id,
            _provided_fields=frozenset({"brand_id"}),
        )
    )

    assert result.ok is False
    codes = {e.code for e in result.validation_errors}
    assert "BRAND_NOT_FOUND" in codes


async def test_slug_conflict_produces_validation_error() -> None:
    product = ProductBuilder().with_slug("existing").build()
    handler = _make_handler(product, slug_taken={"taken-slug"})

    result = await handler.handle(
        ValidateProductUpdateQuery(
            product_id=product.id,
            slug="taken-slug",
            _provided_fields=frozenset({"slug"}),
        )
    )

    assert result.ok is False
    codes = {e.code for e in result.validation_errors}
    assert "SLUG_CONFLICT" in codes


async def test_supplier_change_warns_when_skus_present() -> None:
    product = ProductBuilder().build()
    variant_id = product.variants[0].id
    product.add_sku(variant_id, sku_code="SKU-1", price=Money(1000, "RUB"))

    handler = _make_handler(product)
    new_supplier = uuid.uuid4()

    result = await handler.handle(
        ValidateProductUpdateQuery(
            product_id=product.id,
            supplier_id=new_supplier,
            _provided_fields=frozenset({"supplier_id"}),
        )
    )

    codes = {w.code for w in result.warnings}
    assert "SUPPLIER_CHANGE_TRIGGERS_RECOMPUTE" in codes
    affected = next(
        w.details["affected_sku_count"]
        for w in result.warnings
        if w.code == "SUPPLIER_CHANGE_TRIGGERS_RECOMPUTE"
    )
    assert affected == 1
    # Warning is advisory — gate stays open.
    assert result.ok is True


async def test_no_warning_when_supplier_change_with_no_skus() -> None:
    product = ProductBuilder().build()  # no SKUs
    handler = _make_handler(product)

    result = await handler.handle(
        ValidateProductUpdateQuery(
            product_id=product.id,
            supplier_id=uuid.uuid4(),
            _provided_fields=frozenset({"supplier_id"}),
        )
    )

    assert result.warnings == []
    assert result.ok is True


async def test_handler_does_not_mutate_product() -> None:
    product = ProductBuilder().with_slug("locked").build()
    original_slug = product.slug
    handler = _make_handler(product)

    await handler.handle(
        ValidateProductUpdateQuery(
            product_id=product.id,
            slug="something-else",
            _provided_fields=frozenset({"slug"}),
        )
    )

    assert product.slug == original_slug
