"""Integration test for ``ValidateProductUpdateHandler`` (C1.2)."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.validate_product_update import (
    ValidateProductUpdateHandler,
    ValidateProductUpdateQuery,
)
from src.modules.catalog.domain.entities import Product
from src.modules.catalog.domain.value_objects import Money
from src.modules.catalog.infrastructure.repositories.brand import BrandRepository
from src.modules.catalog.infrastructure.repositories.category import CategoryRepository
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


def _build_handler(db_session: AsyncSession) -> ValidateProductUpdateHandler:
    return ValidateProductUpdateHandler(
        product_repo=ProductRepository(session=db_session),
        brand_repo=BrandRepository(session=db_session),
        category_repo=CategoryRepository(session=db_session),
        logger=_NullLogger(),
    )


async def _seed_product(
    db_session: AsyncSession,
    seed_product_deps: dict[str, uuid.UUID],
    *,
    slug: str,
) -> Product:
    repo = ProductRepository(session=db_session)
    product = Product.create(
        slug=slug,
        title_i18n={"en": "VU Product", "ru": "VU"},
        brand_id=seed_product_deps["brand_id"],
        primary_category_id=seed_product_deps["category_id"],
    )
    await repo.add(product)
    await db_session.flush()
    return product


async def test_diff_and_warning_for_supplier_change(
    db_session: AsyncSession,
    seed_product_deps: dict[str, uuid.UUID],
) -> None:
    product = await _seed_product(db_session, seed_product_deps, slug="vu-supp-1")
    # Add an active SKU so the warning fires.
    repo = ProductRepository(session=db_session)
    domain = await repo.get_with_variants(product.id)
    assert domain is not None
    domain.add_sku(domain.variants[0].id, sku_code="VU-SKU-1", price=Money(1500, "RUB"))
    await repo.update(domain)
    await db_session.flush()

    handler = _build_handler(db_session)
    new_supplier = uuid.uuid4()

    result = await handler.handle(
        ValidateProductUpdateQuery(
            product_id=product.id,
            supplier_id=new_supplier,
            _provided_fields=frozenset({"supplier_id"}),
        )
    )

    assert result.ok is True  # warning is advisory, not a gate
    fields = {d.field for d in result.diff}
    assert "supplier_id" in fields
    codes = {w.code for w in result.warnings}
    assert "SUPPLIER_CHANGE_TRIGGERS_RECOMPUTE" in codes
    affected = next(
        w.details["affected_sku_count"]
        for w in result.warnings
        if w.code == "SUPPLIER_CHANGE_TRIGGERS_RECOMPUTE"
    )
    assert affected == 1


async def test_slug_conflict_against_real_db(
    db_session: AsyncSession,
    seed_product_deps: dict[str, uuid.UUID],
) -> None:
    target = await _seed_product(db_session, seed_product_deps, slug="vu-target")
    occupant = await _seed_product(db_session, seed_product_deps, slug="vu-occupant")

    handler = _build_handler(db_session)
    result = await handler.handle(
        ValidateProductUpdateQuery(
            product_id=target.id,
            slug=occupant.slug,
            _provided_fields=frozenset({"slug"}),
        )
    )

    assert result.ok is False
    codes = {e.code for e in result.validation_errors}
    assert "SLUG_CONFLICT" in codes


async def test_unknown_brand_id_real_db(
    db_session: AsyncSession,
    seed_product_deps: dict[str, uuid.UUID],
) -> None:
    product = await _seed_product(db_session, seed_product_deps, slug="vu-brand")
    handler = _build_handler(db_session)

    result = await handler.handle(
        ValidateProductUpdateQuery(
            product_id=product.id,
            brand_id=uuid.uuid4(),  # not seeded
            _provided_fields=frozenset({"brand_id"}),
        )
    )

    assert result.ok is False
    codes = {e.code for e in result.validation_errors}
    assert "BRAND_NOT_FOUND" in codes
