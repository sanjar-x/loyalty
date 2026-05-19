"""Passport domain ports."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from src.modules.passport.domain.entities import Passport


class IPassportRepository(ABC):
    @abstractmethod
    async def add(self, passport: Passport) -> Passport: ...

    @abstractmethod
    async def get(self, passport_id: uuid.UUID) -> Passport | None: ...

    @abstractmethod
    async def get_for_update(self, passport_id: uuid.UUID) -> Passport | None: ...

    @abstractmethod
    async def update(self, passport: Passport) -> Passport: ...

    @abstractmethod
    async def list_by_identity(
        self,
        identity_id: uuid.UUID,
        *,
        include_archived: bool = False,
    ) -> list[Passport]: ...
