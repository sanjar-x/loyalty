"""Recipient aggregate.

Owned by ``identity_id``; carries **shipping coordinates** — full name
(printed on the box / used to greet the buyer), phone, email. Multiple
recipients per customer are supported (use case: gifts, ordering for
family members, etc.).

Customs identifiers (passport serial+number+issue date, INN, birth
date) **no longer live here** — they were extracted into the
``passport`` bounded context in Sprint 1.5 Part 2 (ADR-011). Recipient
and Passport are independent aggregates linked only at checkout via
Order. The ``validation_status`` FSM moved with the customs fields;
shipping data has no validation lifecycle (it's a destination, not a
document).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from attr import dataclass

from src.modules.recipient.domain.events import (
    RecipientArchivedEvent,
    RecipientCreatedEvent,
    RecipientUpdatedEvent,
)
from src.modules.recipient.domain.exceptions import RecipientArchivedError
from src.modules.recipient.domain.value_objects import Email, FullName, Phone
from src.shared.interfaces.entities import AggregateRoot


@dataclass
class Recipient(AggregateRoot):
    """Customer-owned shipping recipient (no customs PII).

    Attributes:
        id: UUID (uuid4).
        identity_id: Owner identity.
        full_name: Recipient full name (RU + Lat).
        phone: E.164 phone number.
        email: Contact email.
        is_archived: Soft-delete flag.
        version, created_at, updated_at: Optimistic-lock & timestamps.
    """

    id: uuid.UUID
    identity_id: uuid.UUID
    full_name: FullName
    phone: Phone
    email: Email
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    version: int

    @classmethod
    def create(
        cls,
        *,
        identity_id: uuid.UUID,
        full_name: FullName,
        phone: Phone,
        email: Email,
    ) -> Recipient:
        now = datetime.now(UTC)
        recipient = cls(
            id=uuid.uuid4(),
            identity_id=identity_id,
            full_name=full_name,
            phone=phone,
            email=email,
            is_archived=False,
            created_at=now,
            updated_at=now,
            version=0,
        )
        recipient.add_domain_event(
            RecipientCreatedEvent(recipient_id=recipient.id, identity_id=identity_id)
        )
        return recipient

    def _ensure_active(self) -> None:
        if self.is_archived:
            raise RecipientArchivedError(recipient_id=str(self.id))

    # ---------------------------------------------------------------------
    # Mutations
    # ---------------------------------------------------------------------

    def update(
        self,
        *,
        full_name: FullName | None = None,
        phone: Phone | None = None,
        email: Email | None = None,
    ) -> None:
        self._ensure_active()
        if full_name is not None and full_name != self.full_name:
            self.full_name = full_name
        if phone is not None and phone != self.phone:
            self.phone = phone
        if email is not None and email != self.email:
            self.email = email
        self.updated_at = datetime.now(UTC)
        self.add_domain_event(RecipientUpdatedEvent(recipient_id=self.id))

    def archive(self) -> None:
        if self.is_archived:
            return
        self.is_archived = True
        self.updated_at = datetime.now(UTC)
        self.add_domain_event(RecipientArchivedEvent(recipient_id=self.id))
