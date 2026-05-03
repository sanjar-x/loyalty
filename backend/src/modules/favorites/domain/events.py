"""Favorites domain events.

Events are emitted from the ``FavoriteList`` aggregate, persisted into
the Outbox table inside the same transaction as the business write,
and later picked up by the relay (``src/infrastructure/outbox/relay.py``).

Follows the same ``__init_subclass__`` + ``__post_init__`` pattern as
``CartEvent`` so that ``aggregate_id`` is auto-derived and required
fields are validated centrally.
"""

import uuid
from dataclasses import dataclass
from typing import ClassVar

from src.shared.interfaces.entities import DomainEvent


@dataclass
class FavoritesEvent(DomainEvent):
    """Intermediate base for all favorites domain events."""

    _required_fields: ClassVar[tuple[str, ...]] = ()
    _aggregate_id_field: ClassVar[str] = ""

    aggregate_type: str = "favorites"
    event_type: str = "FavoritesEvent"

    def __init_subclass__(
        cls,
        *,
        required_fields: tuple[str, ...] | None = None,
        aggregate_id_field: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init_subclass__(**kwargs)
        if required_fields is not None:
            cls._required_fields = required_fields
        if aggregate_id_field is not None:
            cls._aggregate_id_field = aggregate_id_field

        if required_fields is not None and cls.event_type == "FavoritesEvent":
            raise TypeError(
                f"{cls.__name__} must define its own 'event_type' "
                f"(inherited default 'FavoritesEvent' would misroute events)"
            )

    def __post_init__(self) -> None:
        cls_name = type(self).__name__
        for field_name in self._required_fields:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} is required for {cls_name}")
        if not self.aggregate_id and self._aggregate_id_field:
            self.aggregate_id = str(getattr(self, self._aggregate_id_field))


# ---------------------------------------------------------------------------
# List lifecycle
# ---------------------------------------------------------------------------


@dataclass
class FavoriteListCreatedEvent(
    FavoritesEvent,
    required_fields=("list_id", "identity_id"),
    aggregate_id_field="list_id",
):
    list_id: uuid.UUID | None = None
    identity_id: uuid.UUID | None = None
    name: str | None = None
    is_default: bool = False
    event_type: str = "FavoriteListCreatedEvent"


@dataclass
class FavoriteListRenamedEvent(
    FavoritesEvent,
    required_fields=("list_id", "identity_id"),
    aggregate_id_field="list_id",
):
    list_id: uuid.UUID | None = None
    identity_id: uuid.UUID | None = None
    new_name: str | None = None
    event_type: str = "FavoriteListRenamedEvent"


@dataclass
class FavoriteListDeletedEvent(
    FavoritesEvent,
    required_fields=("list_id", "identity_id"),
    aggregate_id_field="list_id",
):
    list_id: uuid.UUID | None = None
    identity_id: uuid.UUID | None = None
    event_type: str = "FavoriteListDeletedEvent"


# ---------------------------------------------------------------------------
# Item lifecycle
# ---------------------------------------------------------------------------


@dataclass
class FavoriteItemAddedEvent(
    FavoritesEvent,
    required_fields=("list_id", "identity_id", "target_type", "target_id"),
    aggregate_id_field="list_id",
):
    list_id: uuid.UUID | None = None
    identity_id: uuid.UUID | None = None
    target_type: str | None = None
    target_id: uuid.UUID | None = None
    event_type: str = "FavoriteItemAddedEvent"


@dataclass
class FavoriteItemRemovedEvent(
    FavoritesEvent,
    required_fields=("list_id", "identity_id", "target_type", "target_id"),
    aggregate_id_field="list_id",
):
    list_id: uuid.UUID | None = None
    identity_id: uuid.UUID | None = None
    target_type: str | None = None
    target_id: uuid.UUID | None = None
    event_type: str = "FavoriteItemRemovedEvent"
