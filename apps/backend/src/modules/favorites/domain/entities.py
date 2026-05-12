"""
Favorites aggregate root and child entities.

``FavoriteList`` is the aggregate root. Items (``FavoriteItem``) are
child entities — they have identity but cannot exist outside a list,
and all mutations go through the aggregate to preserve invariants
(unique target per list, default-list immutability).

Part of the domain layer -- zero infrastructure imports.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from attr import dataclass, field

from src.modules.favorites.domain.events import (
    FavoriteItemAddedEvent,
    FavoriteItemRemovedEvent,
    FavoriteListCreatedEvent,
    FavoriteListDeletedEvent,
    FavoriteListRenamedEvent,
)
from src.modules.favorites.domain.exceptions import (
    DefaultListImmutableError,
)
from src.modules.favorites.domain.value_objects import FavoriteTargetType
from shared.interfaces.entities import AggregateRoot

DEFAULT_LIST_NAME = "Избранное"
MAX_LIST_NAME_LENGTH = 120


def _generate_id() -> uuid.UUID:
    return uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4()


def _validate_name(name: str) -> str:
    name = (name or "").strip()
    if not name:
        raise ValueError("Favorite list name must not be empty")
    if len(name) > MAX_LIST_NAME_LENGTH:
        raise ValueError(f"Favorite list name must be <= {MAX_LIST_NAME_LENGTH} chars")
    return name


@dataclass
class FavoriteItem:
    """Child entity inside a ``FavoriteList`` (no AggregateRoot).

    Attributes:
        id: Unique item identifier within the favorites bounded context.
        list_id: FK to the owning ``FavoriteList`` (denormalized).
        target_type: One of :class:`FavoriteTargetType` values.
        target_id: The catalog UUID of the favorited entity (Product/Brand).
        added_at: Creation timestamp (UTC).
    """

    id: uuid.UUID
    list_id: uuid.UUID
    target_type: FavoriteTargetType
    target_id: uuid.UUID
    added_at: datetime = field(factory=lambda: datetime.now(UTC))


@dataclass
class FavoriteList(AggregateRoot):
    """Favorite list aggregate root.

    Owns ``FavoriteItem`` child entities. Each user has exactly one
    *default* list (``is_default=True``) — auto-created on first write.
    The default list cannot be renamed or deleted; user-created lists
    are unconstrained other than name uniqueness per identity.

    Attributes:
        id: Unique list identifier (UUIDv7).
        identity_id: Owning Identity UUID (FK).
        name: Display name (≤ 120 chars, non-empty after trim).
        is_default: True for the auto-created default list.
        sort_order: Display ordering among the user's lists.
        created_at: Creation timestamp (UTC).
        updated_at: Last modification timestamp (UTC).
        items: Owned ``FavoriteItem`` children.
    """

    id: uuid.UUID
    identity_id: uuid.UUID
    name: str
    is_default: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime
    _items: list[FavoriteItem] = field(factory=list, alias="items")

    @property
    def items(self) -> tuple[FavoriteItem, ...]:
        """Immutable view of the list's items (TYPE-004).

        External code reads this tuple; ``add_item`` / ``remove_item``
        mutate the private ``self._items`` after enforcing the
        uniqueness invariant on a single code path.
        """
        return tuple(self._items)

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def create_default(cls, identity_id: uuid.UUID) -> FavoriteList:
        """Build the user's default ``Избранное`` list.

        Idempotency on creation is guaranteed at the DB level by a
        partial unique index on ``(identity_id) WHERE is_default``.
        """
        now = datetime.now(UTC)
        favorite_list = cls(
            id=_generate_id(),
            identity_id=identity_id,
            name=DEFAULT_LIST_NAME,
            is_default=True,
            sort_order=0,
            created_at=now,
            updated_at=now,
            items=[],
        )
        favorite_list.add_domain_event(
            FavoriteListCreatedEvent(
                list_id=favorite_list.id,
                identity_id=identity_id,
                name=favorite_list.name,
                is_default=True,
            )
        )
        return favorite_list

    @classmethod
    def create(
        cls,
        *,
        identity_id: uuid.UUID,
        name: str,
        sort_order: int = 0,
    ) -> FavoriteList:
        """Build a user-named list (``is_default=False``)."""
        validated_name = _validate_name(name)
        now = datetime.now(UTC)
        favorite_list = cls(
            id=_generate_id(),
            identity_id=identity_id,
            name=validated_name,
            is_default=False,
            sort_order=sort_order,
            created_at=now,
            updated_at=now,
            items=[],
        )
        favorite_list.add_domain_event(
            FavoriteListCreatedEvent(
                list_id=favorite_list.id,
                identity_id=identity_id,
                name=validated_name,
                is_default=False,
            )
        )
        return favorite_list

    # ------------------------------------------------------------------
    # List-level mutators
    # ------------------------------------------------------------------

    def rename(self, new_name: str) -> None:
        """Rename a user-created list.

        Raises:
            DefaultListImmutableError: If this is the default list.
            ValueError: If ``new_name`` fails validation.
        """
        if self.is_default:
            raise DefaultListImmutableError(action="rename")
        validated = _validate_name(new_name)
        if validated == self.name:
            return
        self.name = validated
        self.updated_at = datetime.now(UTC)
        self.add_domain_event(
            FavoriteListRenamedEvent(
                list_id=self.id,
                identity_id=self.identity_id,
                new_name=validated,
            )
        )

    def reorder(self, sort_order: int) -> None:
        """Reposition the list in the user's display order."""
        if sort_order == self.sort_order:
            return
        self.sort_order = sort_order
        self.updated_at = datetime.now(UTC)

    def mark_deleted(self) -> None:
        """Emit a deletion event. Caller is responsible for repo-level delete.

        Raises:
            DefaultListImmutableError: If this is the default list.
        """
        if self.is_default:
            raise DefaultListImmutableError(action="delete")
        self.add_domain_event(
            FavoriteListDeletedEvent(
                list_id=self.id,
                identity_id=self.identity_id,
            )
        )

    # ------------------------------------------------------------------
    # Item management
    # ------------------------------------------------------------------

    def find_item(
        self,
        target_type: FavoriteTargetType,
        target_id: uuid.UUID,
    ) -> FavoriteItem | None:
        """Locate an item by (target_type, target_id) or return None."""
        for item in self._items:
            if item.target_type == target_type and item.target_id == target_id:
                return item
        return None

    def add_item(
        self,
        *,
        target_type: FavoriteTargetType,
        target_id: uuid.UUID,
    ) -> FavoriteItem | None:
        """Add a target to this list. Idempotent.

        Returns:
            The newly created ``FavoriteItem``, or ``None`` when the
            target was already in the list (no event is emitted in that
            case so the operation is safe to retry).
        """
        existing = self.find_item(target_type, target_id)
        if existing is not None:
            return None

        item = FavoriteItem(
            id=_generate_id(),
            list_id=self.id,
            target_type=target_type,
            target_id=target_id,
        )
        self._items.append(item)
        self.updated_at = datetime.now(UTC)
        self.add_domain_event(
            FavoriteItemAddedEvent(
                list_id=self.id,
                identity_id=self.identity_id,
                target_type=target_type.value,
                target_id=target_id,
            )
        )
        return item

    def remove_item(
        self,
        *,
        target_type: FavoriteTargetType,
        target_id: uuid.UUID,
    ) -> bool:
        """Remove a target from this list. Idempotent.

        Returns:
            ``True`` if a row was removed; ``False`` if the item was
            already absent (no event is emitted in that case).
        """
        item = self.find_item(target_type, target_id)
        if item is None:
            return False
        self._items.remove(item)
        self.updated_at = datetime.now(UTC)
        self.add_domain_event(
            FavoriteItemRemovedEvent(
                list_id=self.id,
                identity_id=self.identity_id,
                target_type=target_type.value,
                target_id=target_id,
            )
        )
        return True
