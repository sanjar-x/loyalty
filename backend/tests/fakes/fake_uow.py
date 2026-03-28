"""
Fake Unit of Work for catalog command handler unit tests.

Provides ``FakeUnitOfWork`` (in-memory implementation of IUnitOfWork) and
``FakeRepository`` (generic dict-based CRUD base). Used by Phase 4-6 tests
to verify repository interactions and domain event emission without
touching the database.

Per D-03: core test isolation mechanism for catalog command tests.
Per D-04: does NOT replace the existing make_uow() AsyncMock used by
identity/user tests.
"""

from __future__ import annotations

import uuid
from typing import Any

from src.shared.interfaces.entities import AggregateRoot, DomainEvent
from src.shared.interfaces.uow import IUnitOfWork

from tests.fakes.fake_catalog_repos import (
    FakeAttributeGroupRepository,
    FakeAttributeRepository,
    FakeAttributeTemplateRepository,
    FakeAttributeValueRepository,
    FakeBrandRepository,
    FakeCategoryRepository,
    FakeMediaAssetRepository,
    FakeProductAttributeValueRepository,
    FakeProductRepository,
    FakeTemplateAttributeBindingRepository,
)


class FakeRepository[T]:
    """Generic in-memory repository backed by a dict.

    Provides the four CRUD operations that ``ICatalogRepository[T]``
    defines. Concrete fake repos extend this with additional query
    methods.

    Attributes:
        _store: Internal dict mapping entity ID to entity instance.
    """

    def __init__(self) -> None:
        self._store: dict[uuid.UUID, T] = {}

    async def add(self, entity: T) -> T:
        """Persist a new entity in memory."""
        self._store[entity.id] = entity  # type: ignore[attr-defined]
        return entity

    async def get(self, entity_id: uuid.UUID) -> T | None:
        """Retrieve an entity by ID, or None if not found."""
        return self._store.get(entity_id)

    async def update(self, entity: T) -> T:
        """Update an existing entity in memory."""
        self._store[entity.id] = entity  # type: ignore[attr-defined]
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        """Remove an entity by ID (no-op if missing)."""
        self._store.pop(entity_id, None)

    @property
    def items(self) -> dict[uuid.UUID, T]:
        """Direct access to the internal store for test assertions."""
        return self._store


class FakeUnitOfWork(IUnitOfWork):
    """In-memory Unit of Work that replicates real UoW event collection behavior.

    Tracks registered aggregates, collects domain events on commit,
    and exposes ``committed``, ``rolled_back``, and ``collected_events``
    properties for test assertions.

    Initializes all 10 catalog repository attributes and wires cross-repo
    references so that ``has_products()``, ``has_children()``, and
    ``has_attributes()`` can scan related stores.
    """

    def __init__(self) -> None:
        self._aggregates: list[AggregateRoot] = []
        self._committed: bool = False
        self._rolled_back: bool = False
        self._collected_events: list[DomainEvent] = []

        # Initialize all 10 catalog repository fakes
        self.brands: FakeBrandRepository = FakeBrandRepository()
        self.categories: FakeCategoryRepository = FakeCategoryRepository()
        self.attribute_groups: FakeAttributeGroupRepository = (
            FakeAttributeGroupRepository()
        )
        self.attributes: FakeAttributeRepository = FakeAttributeRepository()
        self.attribute_values: FakeAttributeValueRepository = (
            FakeAttributeValueRepository()
        )
        self.products: FakeProductRepository = FakeProductRepository()
        self.product_attribute_values: FakeProductAttributeValueRepository = (
            FakeProductAttributeValueRepository()
        )
        self.media_assets: FakeMediaAssetRepository = FakeMediaAssetRepository()
        self.attribute_templates: FakeAttributeTemplateRepository = (
            FakeAttributeTemplateRepository()
        )
        self.template_bindings: FakeTemplateAttributeBindingRepository = (
            FakeTemplateAttributeBindingRepository()
        )

        # Wire cross-repo references for has_products/has_children/has_attributes
        self.brands._product_store = self.products._store
        self.categories._product_store = self.products._store
        self.categories._child_store = self.categories._store
        self.attribute_groups._attribute_store = self.attributes._store

    async def __aenter__(self) -> FakeUnitOfWork:
        """Enter the transactional context and reset tracking state."""
        self._aggregates.clear()
        self._committed = False
        self._rolled_back = False
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the transactional context.

        Rolls back on exception, then ALWAYS clears aggregates
        (matching real UoW behavior where ``_aggregates.clear()``
        runs unconditionally in __aexit__).
        """
        if exc_type:
            await self.rollback()
        self._aggregates.clear()

    async def flush(self) -> None:
        """No-op flush (no database session to flush)."""
        pass

    async def commit(self) -> None:
        """Collect domain events from registered aggregates, then mark committed.

        Replicates the real UoW's ``_collect_and_persist_outbox_events``
        behavior: iterates aggregates, extends collected_events with each
        aggregate's domain_events, then calls ``clear_domain_events()``
        on each aggregate.
        """
        for aggregate in self._aggregates:
            self._collected_events.extend(aggregate.domain_events)
            aggregate.clear_domain_events()
        self._committed = True

    async def rollback(self) -> None:
        """Mark as rolled back and clear aggregates."""
        self._rolled_back = True
        self._aggregates.clear()

    def register_aggregate(self, aggregate: AggregateRoot) -> None:
        """Register an aggregate for event collection on commit.

        De-duplicates: appends only if the aggregate is not already
        registered (same as real UoW).

        Args:
            aggregate: The mutated aggregate root instance.
        """
        if aggregate not in self._aggregates:
            self._aggregates.append(aggregate)

    @property
    def committed(self) -> bool:
        """Whether commit() has been called."""
        return self._committed

    @property
    def rolled_back(self) -> bool:
        """Whether rollback() has been called."""
        return self._rolled_back

    @property
    def collected_events(self) -> list[DomainEvent]:
        """All domain events collected across all commits."""
        return self._collected_events
