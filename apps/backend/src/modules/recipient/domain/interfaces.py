"""Recipient domain ports."""

import uuid
from abc import ABC, abstractmethod

from attrs import frozen

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


@frozen
class ValidationResult:
    is_valid: bool
    reason: str | None = None


class IRecipientValidator(ABC):
    """Sync validator (e.g. DaData). Format checks happen earlier in
    ``CustomsData.parse``; this layer adds external lookup."""

    @abstractmethod
    async def validate(self, recipient: Recipient) -> ValidationResult: ...
