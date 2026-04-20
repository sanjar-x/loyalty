"""Integration tests for ``ProductPricingProfileRepository`` (real DB)."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.pricing.domain.entities import ProductPricingProfile
from src.modules.pricing.domain.value_objects import ProfileStatus
from src.modules.pricing.infrastructure.repositories.product_pricing_profile import (
    ProductPricingProfileRepository,
)

pytestmark = pytest.mark.integration


async def test_add_and_get_roundtrip(db_session: AsyncSession) -> None:
    repo = ProductPricingProfileRepository(db_session)
    product_id = uuid.uuid4()
    actor = uuid.uuid4()

    profile = ProductPricingProfile.create(
        product_id=product_id,
        values={"purchase_price_cny": Decimal("199.50"), "weight": Decimal("0.75")},
        actor_id=actor,
    )
    profile.clear_domain_events()
    await repo.add(profile)
    await db_session.flush()

    fetched = await repo.get_by_product_id(product_id)
    assert fetched is not None
    assert fetched.id == profile.id
    assert fetched.values == {
        "purchase_price_cny": Decimal("199.50"),
        "weight": Decimal("0.75"),
    }
    assert fetched.status is ProfileStatus.DRAFT
    assert fetched.version_lock == 0


async def test_update_increments_version_lock(db_session: AsyncSession) -> None:
    repo = ProductPricingProfileRepository(db_session)
    product_id = uuid.uuid4()
    actor = uuid.uuid4()

    profile = ProductPricingProfile.create(
        product_id=product_id, values={"a": Decimal("1")}, actor_id=actor
    )
    profile.clear_domain_events()
    await repo.add(profile)
    await db_session.flush()

    loaded = await repo.get_by_product_id_for_update(product_id)
    assert loaded is not None
    loaded.update_values(values={"a": Decimal("2")}, actor_id=actor)
    loaded.clear_domain_events()
    await repo.update(loaded)
    await db_session.flush()

    reloaded = await repo.get_by_product_id(product_id)
    assert reloaded is not None
    assert reloaded.version_lock == 1
    assert reloaded.values == {"a": Decimal("2")}


async def test_soft_deleted_profile_hidden_by_default(
    db_session: AsyncSession,
) -> None:
    repo = ProductPricingProfileRepository(db_session)
    product_id = uuid.uuid4()
    actor = uuid.uuid4()

    profile = ProductPricingProfile.create(
        product_id=product_id, values={}, actor_id=actor
    )
    profile.clear_domain_events()
    await repo.add(profile)
    await db_session.flush()

    loaded = await repo.get_by_product_id_for_update(product_id)
    assert loaded is not None
    loaded.soft_delete(actor_id=actor)
    loaded.clear_domain_events()
    await repo.update(loaded)
    await db_session.flush()

    assert await repo.get_by_product_id(product_id) is None
    assert await repo.get_by_product_id(product_id, include_deleted=True) is not None


async def test_partial_unique_index_allows_recreate_after_soft_delete(
    db_session: AsyncSession,
) -> None:
    repo = ProductPricingProfileRepository(db_session)
    product_id = uuid.uuid4()
    actor = uuid.uuid4()

    first = ProductPricingProfile.create(
        product_id=product_id, values={}, actor_id=actor
    )
    first.clear_domain_events()
    await repo.add(first)
    await db_session.flush()

    loaded = await repo.get_by_product_id_for_update(product_id)
    assert loaded is not None
    loaded.soft_delete(actor_id=actor)
    loaded.clear_domain_events()
    await repo.update(loaded)
    await db_session.flush()

    second = ProductPricingProfile.create(
        product_id=product_id,
        values={"price": Decimal("10")},
        actor_id=actor,
    )
    second.clear_domain_events()
    await repo.add(second)
    await db_session.flush()

    active = await repo.get_by_product_id(product_id)
    assert active is not None
    assert active.id == second.id
