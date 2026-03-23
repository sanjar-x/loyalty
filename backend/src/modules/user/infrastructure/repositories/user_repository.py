"""Null-object implementation of the deprecated IUserRepository.

The legacy ``users`` table no longer exists; all new profiles are created
as Customer or StaffMember. This stub satisfies the DI graph so that
backward-compatible consumers can still inject IUserRepository without
error — every lookup returns None, and writes are no-ops.
"""

import uuid

from src.modules.user.domain.entities import User
from src.modules.user.domain.interfaces import IUserRepository


class NullUserRepository(IUserRepository):
    """No-op repository for the deprecated User aggregate."""

    async def add(self, user: User) -> User:
        return user

    async def get(self, user_id: uuid.UUID) -> User | None:
        return None

    async def update(self, user: User) -> None:
        pass
