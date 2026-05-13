"""Favorites domain ports (Hexagonal Architecture).

Application handlers depend only on these contracts; concrete
implementations (SQLAlchemy repositories, catalog ACL) live in the
infrastructure layer.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.modules.favorites.domain.entities import FavoriteItem, FavoriteList
from src.modules.favorites.domain.value_objects import FavoriteTargetType


@dataclass(frozen=True)
class FavoriteTargetCheck:
    """Result of an ACL check against catalog (Product/Brand existence)."""

    target_type: FavoriteTargetType
    target_id: uuid.UUID
    exists: bool
    reason: str | None = None


class IFavoriteListRepository(ABC):
    """Persistence contract for ``FavoriteList`` aggregates."""

    @abstractmethod
    async def add(self, favorite_list: FavoriteList) -> FavoriteList: ...

    @abstractmethod
    async def get(self, list_id: uuid.UUID) -> FavoriteList | None:
        """Load a list with its items eagerly attached."""

    @abstractmethod
    async def get_for_update(self, list_id: uuid.UUID) -> FavoriteList | None:
        """Load with pessimistic lock (SELECT FOR UPDATE) for write paths."""

    @abstractmethod
    async def get_default_for_identity(
        self, identity_id: uuid.UUID
    ) -> FavoriteList | None: ...

    @abstractmethod
    async def list_by_identity(self, identity_id: uuid.UUID) -> list[FavoriteList]:
        """Return all lists owned by ``identity_id`` ordered by sort_order."""

    @abstractmethod
    async def update(self, favorite_list: FavoriteList) -> None:
        """Persist list-level changes (name, sort_order, updated_at)."""

    @abstractmethod
    async def delete(self, list_id: uuid.UUID) -> None: ...

    @abstractmethod
    async def name_exists(self, identity_id: uuid.UUID, name: str) -> bool: ...


class IFavoriteItemRepository(ABC):
    """Persistence contract for ``FavoriteItem`` child entities.

    The item repository writes through the aggregate (it is *not* a
    parallel write path); it exists so that command handlers can flush
    a single new item without rewriting the entire list.
    """

    @abstractmethod
    async def add(self, item: FavoriteItem) -> None: ...

    @abstractmethod
    async def remove(
        self,
        *,
        list_id: uuid.UUID,
        target_type: FavoriteTargetType,
        target_id: uuid.UUID,
    ) -> bool:
        """Delete by natural key. Returns True iff a row was deleted."""

    @abstractmethod
    async def count_by_list(self, list_id: uuid.UUID) -> int: ...

    @abstractmethod
    async def check_batch(
        self,
        *,
        identity_id: uuid.UUID,
        target_type: FavoriteTargetType,
        target_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, uuid.UUID]:
        """For each target_id present in *any* of the user's lists,
        return the list_id it lives in (the default list takes priority
        when a target appears in several lists).
        """


class IFavoriteTargetValidator(ABC):
    """ACL port that proves a (target_type, target_id) pair is real.

    Concrete implementation reads catalog ORM directly — this is the
    single approved cross-module touchpoint and is whitelisted in
    ``tests/architecture/test_boundaries.py``.
    """

    @abstractmethod
    async def check(
        self,
        *,
        target_type: FavoriteTargetType,
        target_id: uuid.UUID,
    ) -> FavoriteTargetCheck: ...
