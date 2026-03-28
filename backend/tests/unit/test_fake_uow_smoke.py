"""
Smoke tests for FakeUnitOfWork behavior.

Verifies that FakeUoW correctly implements IUnitOfWork semantics:
CRUD operations, commit/rollback flags, domain event collection and
clearing, aggregate deduplication, context manager behavior, fake
repository query methods, and cross-repo reference wiring.

All tests are pure unit tests -- no database connection required.
"""

import uuid
from dataclasses import dataclass

import pytest

from src.modules.catalog.domain.entities import Brand as DomainBrand
from src.modules.catalog.domain.entities import Product as DomainProduct
from src.modules.catalog.domain.value_objects import ProductStatus
from src.shared.interfaces.entities import DomainEvent

from tests.fakes.fake_uow import FakeUnitOfWork


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


@dataclass
class _TestEvent(DomainEvent):
    """Minimal domain event for testing FakeUoW event collection."""

    aggregate_type: str = "Brand"
    aggregate_id: str = ""
    event_type: str = "test_event"


def _make_brand(
    slug: str = "nike",
    name: str = "Nike",
    brand_id: uuid.UUID | None = None,
) -> DomainBrand:
    """Create a Brand entity via its factory method."""
    return DomainBrand.create(
        name=name,
        slug=slug,
        brand_id=brand_id or uuid.uuid4(),
    )


def _make_product(
    slug: str = "nike-air-max",
    brand_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
) -> DomainProduct:
    """Create a Product entity via its factory method."""
    return DomainProduct.create(
        slug=slug,
        title_i18n={"en": "Air Max", "ru": "Эйр Макс"},
        brand_id=brand_id or uuid.uuid4(),
        primary_category_id=category_id or uuid.uuid4(),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFakeUnitOfWork:
    """Smoke tests proving FakeUoW behaves like the real UoW."""

    async def test_add_and_get_entity(self) -> None:
        """Adding a Brand via uow.brands.add makes it retrievable via get."""
        uow = FakeUnitOfWork()
        brand = _make_brand()

        await uow.brands.add(brand)
        retrieved = await uow.brands.get(brand.id)

        assert retrieved is brand

    async def test_committed_flag(self) -> None:
        """committed is False before commit(), True after."""
        uow = FakeUnitOfWork()

        assert uow.committed is False
        await uow.commit()
        assert uow.committed is True

    async def test_rolled_back_flag(self) -> None:
        """rolled_back is False before rollback(), True after."""
        uow = FakeUnitOfWork()

        assert uow.rolled_back is False
        await uow.rollback()
        assert uow.rolled_back is True

    async def test_event_collection_on_commit(self) -> None:
        """commit() collects domain events from registered aggregates."""
        uow = FakeUnitOfWork()
        brand = _make_brand()
        event = _TestEvent(aggregate_id=str(brand.id))
        brand.add_domain_event(event)
        uow.register_aggregate(brand)

        await uow.commit()

        assert len(uow.collected_events) == 1
        assert uow.collected_events[0] is event

    async def test_events_cleared_after_commit(self) -> None:
        """After commit(), aggregate's domain_events are empty (clear was called)."""
        uow = FakeUnitOfWork()
        brand = _make_brand()
        brand.add_domain_event(_TestEvent(aggregate_id=str(brand.id)))
        uow.register_aggregate(brand)

        await uow.commit()

        assert len(brand.domain_events) == 0

    async def test_register_aggregate_deduplication(self) -> None:
        """Registering the same aggregate twice only collects events once."""
        uow = FakeUnitOfWork()
        brand = _make_brand()
        brand.add_domain_event(_TestEvent(aggregate_id=str(brand.id)))
        uow.register_aggregate(brand)
        uow.register_aggregate(brand)  # duplicate

        await uow.commit()

        # Event should be collected only once
        assert len(uow.collected_events) == 1

    async def test_context_manager_rollback_on_exception(self) -> None:
        """Using `async with uow:` and raising inside triggers rollback."""
        uow = FakeUnitOfWork()

        with pytest.raises(ValueError, match="boom"):
            async with uow:
                raise ValueError("boom")

        assert uow.rolled_back is True

    async def test_context_manager_always_clears_aggregates(self) -> None:
        """After normal exit from `async with uow:`, _aggregates is empty.

        This matches real UoW behavior where __aexit__ always clears
        aggregates regardless of whether an exception occurred.
        """
        uow = FakeUnitOfWork()

        async with uow:
            brand = _make_brand()
            uow.register_aggregate(brand)
            # aggregates exist inside the context
            assert len(uow._aggregates) == 1

        # After exit (no exception), aggregates are cleared
        assert len(uow._aggregates) == 0

    async def test_check_slug_exists_on_fake_brand_repo(self) -> None:
        """FakeBrandRepository.check_slug_exists scans store values."""
        uow = FakeUnitOfWork()
        brand = _make_brand(slug="nike")
        await uow.brands.add(brand)

        assert await uow.brands.check_slug_exists("nike") is True
        assert await uow.brands.check_slug_exists("adidas") is False

    async def test_delete_entity(self) -> None:
        """After add then delete, get returns None."""
        uow = FakeUnitOfWork()
        brand = _make_brand()
        await uow.brands.add(brand)

        await uow.brands.delete(brand.id)

        assert await uow.brands.get(brand.id) is None

    async def test_has_products_cross_repo(self) -> None:
        """has_products() scans the cross-referenced product store.

        Verifies that the FakeUoW correctly wires brand._product_store
        to products._store so has_products() returns True when a product
        references the brand.
        """
        uow = FakeUnitOfWork()
        brand = _make_brand()
        product = _make_product(brand_id=brand.id)

        await uow.brands.add(brand)
        await uow.products.add(product)

        assert await uow.brands.has_products(brand.id) is True
        assert await uow.brands.has_products(uuid.uuid4()) is False
