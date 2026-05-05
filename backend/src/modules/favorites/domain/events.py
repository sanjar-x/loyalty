"""Favorites domain events.

Events are emitted from the ``FavoriteList`` aggregate, persisted into
the Outbox table inside the same transaction as the business write,
and later picked up by the relay (``src/infrastructure/outbox/relay.py``).

Validation and ``aggregate_id`` auto-fill come from
:class:`src.shared.interfaces.entities.ModuleDomainEvent`.
"""

import uuid
from dataclasses import dataclass

from src.shared.interfaces.entities import ModuleDomainEvent


@dataclass
class FavoritesEvent(ModuleDomainEvent, abstract=True):
    """Intermediate base for all favorites domain events."""

    aggregate_type: str = "favorites"


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
