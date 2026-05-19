"""Recipient domain ports.

Post-Sprint-1.5 Part 2: ``IRecipientValidator`` removed — passport
validation moved to the ``passport`` bounded context (the FSM lives
on Passport now). Recipient holds shipping coordinates with no
validation lifecycle.
"""

import uuid
from abc import ABC, abstractmethod

from src.modules.recipient.domain.entities import Recipient


class IRecipientRepository(ABC):
    @abstractmethod
    async def add(self, recipient: Recipient) -> Recipient: ...

    @abstractmethod
    async def get(self, recipient_id: uuid.UUID) -> Recipient | None: ...

    @abstractmethod
    async def get_for_update(self, recipient_id: uuid.UUID) -> Recipient | None: ...

    @abstractmethod
    async def update(self, recipient: Recipient) -> Recipient: ...

    @abstractmethod
    async def list_by_identity(
        self,
        identity_id: uuid.UUID,
        *,
        include_archived: bool = False,
    ) -> list[Recipient]: ...
