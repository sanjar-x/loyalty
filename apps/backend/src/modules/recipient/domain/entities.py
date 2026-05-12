"""Recipient aggregate.

Owned by ``identity_id``; carries customs-required PII for cross-border
shipments. Multiple recipients per customer are supported (use case:
gifts, ordering for family members, etc.).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from attr import dataclass

from src.modules.recipient.domain.events import (
    RecipientArchivedEvent,
    RecipientCreatedEvent,
    RecipientInvalidatedEvent,
    RecipientUpdatedEvent,
    RecipientVerifiedEvent,
)
from src.modules.recipient.domain.exceptions import RecipientArchivedError
from src.modules.recipient.domain.value_objects import (
    CustomsData,
    Email,
    FullName,
    Phone,
    RecipientValidationStatus,
)
from shared.interfaces.entities import AggregateRoot


@dataclass
class Recipient(AggregateRoot):
    """Customer-owned recipient with customs identifiers."""

    id: uuid.UUID
    identity_id: uuid.UUID
    full_name: FullName
    phone: Phone
    email: Email
    customs_data: CustomsData
    validation_status: RecipientValidationStatus
    validation_failed_reason: str | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    version: int

    # TYPE-003 — guard ``validation_status`` against direct mutation.
    # The ``mark_pending`` / ``mark_verified`` / ``mark_invalid`` methods
    # bypass via ``object.__setattr__``.

    def __setattr__(self, name: str, value: object) -> None:
        if name == "validation_status" and getattr(
            self, "_Recipient__initialized", False
        ):
            raise AttributeError(
                "Cannot set 'validation_status' directly on Recipient. "
                "Use mark_pending() / mark_verified() / mark_invalid() instead."
            )
        super().__setattr__(name, value)

    def __attrs_post_init__(self) -> None:
        super().__attrs_post_init__()
        object.__setattr__(self, "_Recipient__initialized", True)

    @classmethod
    def create(
        cls,
        *,
        identity_id: uuid.UUID,
        full_name: FullName,
        phone: Phone,
        email: Email,
        customs_data: CustomsData,
    ) -> Recipient:
        now = datetime.now(UTC)
        recipient = cls(
            id=uuid.uuid4(),
            identity_id=identity_id,
            full_name=full_name,
            phone=phone,
            email=email,
            customs_data=customs_data,
            validation_status=RecipientValidationStatus.PENDING,
            validation_failed_reason=None,
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
        customs_data: CustomsData | None = None,
    ) -> None:
        self._ensure_active()
        customs_changed = False
        if full_name is not None and full_name != self.full_name:
            self.full_name = full_name
        if phone is not None and phone != self.phone:
            self.phone = phone
        if email is not None and email != self.email:
            self.email = email
        if customs_data is not None and customs_data != self.customs_data:
            self.customs_data = customs_data
            customs_changed = True
        # REC-002 (D1.3) — only customs_data changes invalidate the
        # DobroPost validation result. Phone / email / full_name edits
        # are recipient-side metadata; DobroPost validates passport +
        # INN + birth_date only, so non-customs changes don't require
        # a re-verification round-trip. Pre-fix: every edit reset to
        # PENDING, forcing customers to wait for a fresh DaData ping
        # even after a typo fix.
        if customs_changed:
            object.__setattr__(
                self, "validation_status", RecipientValidationStatus.PENDING
            )
            self.validation_failed_reason = None
        self.updated_at = datetime.now(UTC)
        self.add_domain_event(
            RecipientUpdatedEvent(
                recipient_id=self.id, customs_data_changed=customs_changed
            )
        )

    def mark_verified(self) -> None:
        self._ensure_active()
        if self.validation_status == RecipientValidationStatus.VERIFIED:
            return  # idempotent
        object.__setattr__(
            self, "validation_status", RecipientValidationStatus.VERIFIED
        )
        self.validation_failed_reason = None
        self.updated_at = datetime.now(UTC)
        self.add_domain_event(RecipientVerifiedEvent(recipient_id=self.id))

    def mark_invalid(self, *, reason: str) -> None:
        self._ensure_active()
        if self.validation_status == RecipientValidationStatus.INVALID:
            self.validation_failed_reason = reason
            return  # idempotent on status, refresh reason
        object.__setattr__(self, "validation_status", RecipientValidationStatus.INVALID)
        self.validation_failed_reason = reason
        self.updated_at = datetime.now(UTC)
        self.add_domain_event(
            RecipientInvalidatedEvent(recipient_id=self.id, reason=reason)
        )

    def archive(self) -> None:
        if self.is_archived:
            return
        self.is_archived = True
        self.updated_at = datetime.now(UTC)
        self.add_domain_event(RecipientArchivedEvent(recipient_id=self.id))
