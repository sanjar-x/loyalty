"""Domain entity base types and event infrastructure.

Provides:

* :class:`DomainEvent` — root base for every domain event in the system.
* :class:`ModuleDomainEvent` — intermediate base that pins ``aggregate_type``
  to a single bounded context and supplies declarative
  ``required_fields`` / ``aggregate_id_field`` validation, used by every
  module's ``domain/events.py``.
* :class:`AggregateRoot` — mixin for aggregates that buffer events for the
  Transactional Outbox pattern.

All three live in the shared kernel and may not import any module.

Typical usage in a module's ``domain/events.py``::

    @dataclass
    class OrderEvent(ModuleDomainEvent, abstract=True):
        aggregate_type: str = "order"

    @dataclass
    class OrderCreatedEvent(
        OrderEvent,
        required_fields=("order_id", "identity_id"),
        aggregate_id_field="order_id",
    ):
        order_id: uuid.UUID | None = None
        identity_id: uuid.UUID | None = None
        event_type: str = "OrderCreatedEvent"
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import ClassVar, Protocol


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
    """Root base class for all domain events.

    Events are serialized via ``dataclasses.asdict()`` and written to the
    ``outbox_messages`` table atomically within the business transaction.

    Concrete subclasses **must** override ``aggregate_type`` and
    ``event_type`` with non-empty string defaults; abstract intermediate
    bases may opt out by passing ``abstract=True`` to the class
    declaration.

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

    # Set on intermediate bases via ``class X(DomainEvent, abstract=True):``
    # so that the integrity check below skips them.
    __abstract_event__: ClassVar[bool] = False

    def __init_subclass__(cls, *, abstract: bool = False, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        cls.__abstract_event__ = abstract
        if abstract:
            return
        if cls.aggregate_type == "" or cls.event_type == "":
            raise TypeError(
                f"{cls.__name__} must override 'aggregate_type' and 'event_type'"
            )


@dataclass
class ModuleDomainEvent(DomainEvent, abstract=True):
    """Intermediate event base shared by every bounded context.

    A module declares its own abstract subclass that fixes
    ``aggregate_type`` once::

        @dataclass
        class OrderEvent(ModuleDomainEvent, abstract=True):
            aggregate_type: str = "order"

    Concrete events then inherit from that subclass and use the
    ``required_fields`` / ``aggregate_id_field`` keyword arguments::

        @dataclass
        class OrderCreatedEvent(
            OrderEvent,
            required_fields=("order_id",),
            aggregate_id_field="order_id",
        ):
            order_id: uuid.UUID | None = None
            event_type: str = "OrderCreatedEvent"

    The base machinery validates that every required field is non-``None``
    on construction (catching forgotten kwargs at the boundary) and
    auto-fills ``aggregate_id`` from the named attribute so that the
    outbox routing layer never has to know about per-module field
    naming.
    """

    _required_fields: ClassVar[tuple[str, ...]] = ()
    _aggregate_id_field: ClassVar[str] = ""

    def __init_subclass__(
        cls,
        *,
        abstract: bool = False,
        required_fields: tuple[str, ...] | None = None,
        aggregate_id_field: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init_subclass__(abstract=abstract, **kwargs)
        if required_fields is not None:
            cls._required_fields = required_fields
        if aggregate_id_field is not None:
            cls._aggregate_id_field = aggregate_id_field

        if required_fields is None:
            return

        # When a subclass declares required_fields it MUST also provide its
        # own ``event_type`` — otherwise events would be persisted under the
        # parent's discriminator and routed to the wrong consumer.
        if "event_type" not in cls.__dict__:
            raise TypeError(
                f"{cls.__name__} declares required_fields but does not "
                "override 'event_type' — events would be misrouted."
            )

    def __post_init__(self) -> None:
        cls_name = type(self).__name__
        for field_name in self._required_fields:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} is required for {cls_name}")
        if not self.aggregate_id and self._aggregate_id_field:
            self.aggregate_id = str(getattr(self, self._aggregate_id_field))


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
