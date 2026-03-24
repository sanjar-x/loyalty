"""
Domain entity base types and event infrastructure.

Provides ``DomainEvent`` (base dataclass for all domain events) and
``AggregateRoot`` (mixin that collects events in-memory for the
Transactional Outbox pattern). Part of the shared kernel.

Typical usage:
    @attrs.define
    class Brand(AggregateRoot):
        id: uuid.UUID
        name: str

        def rename(self, new_name: str) -> None:
            self.name = new_name
            self.add_domain_event(BrandRenamedEvent(...))
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


class IBase(Protocol):
    """Contract for any identifiable domain entity.

    Repository generic constraints depend on this protocol — any object
    with an ``id: UUID`` attribute satisfies it, regardless of whether
    it is an ORM model, attrs class, or Pydantic schema.

    Attributes:
        id: Unique identifier of the entity.
    """

    id: uuid.UUID


# ---------------------------------------------------------------------------
# Domain Events (base types for Transactional Outbox)
# ---------------------------------------------------------------------------


@dataclass
class DomainEvent:
    """Base class for all domain events.

    Events are serialized via ``dataclasses.asdict()`` and written to the
    ``outbox_messages`` table atomically within the business transaction.

    Subclasses **must** override ``aggregate_type`` and ``event_type``
    with non-empty string defaults; failure to do so raises ``TypeError``
    at class definition time (enforced by ``__init_subclass__``).

    Attributes:
        event_id: Unique identifier for this event instance.
        occurred_at: UTC timestamp of when the event was created.
        aggregate_type: Name of the aggregate that produced the event.
        aggregate_id: String representation of the aggregate's ID.
        event_type: Discriminator string identifying the event kind.
    """

    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Subclasses MUST override these with non-empty defaults
    aggregate_type: str = ""
    aggregate_id: str = ""
    event_type: str = ""

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if cls.aggregate_type == "" or cls.event_type == "":
            raise TypeError(
                f"{cls.__name__} must override 'aggregate_type' and 'event_type'"
            )


class AggregateRoot:
    """Mixin for domain aggregates that collect events in-memory.

    Used as a mixin with attrs dataclasses::

        @attrs.define
        class Brand(AggregateRoot):
            ...

    The aggregate accumulates events via ``add_domain_event()``.
    ``UnitOfWork.commit()`` extracts them and writes to the Outbox table
    atomically with the business transaction.
    """

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)

    def __attrs_post_init__(self) -> None:
        # attrs calls __attrs_post_init__ after its generated __init__
        self._domain_events: list[DomainEvent] = []

    def add_domain_event(self, event: DomainEvent) -> None:
        """Append a domain event to be published on commit.

        Args:
            event: The domain event instance to enqueue.
        """
        self._domain_events.append(event)

    def clear_domain_events(self) -> None:
        """Discard all accumulated events without publishing them."""
        self._domain_events.clear()

    @property
    def domain_events(self) -> list[DomainEvent]:
        """Return a defensive copy of the accumulated event list."""
        return self._domain_events.copy()
