"""Passport aggregate root.

Customer-owned customs document with FSM validation lifecycle
(``pending`` → ``verified | invalid``; both can be reset to
``pending`` by data edits). Independent bounded context from
``recipient`` — see ADR-011 (Sprint 1.5 Part 2). They share only
``identity_id`` and are linked via Order at checkout time.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from attr import dataclass

from src.modules.passport.domain.events import (
    PassportArchivedEvent,
    PassportCreatedEvent,
    PassportInvalidatedEvent,
    PassportUpdatedEvent,
    PassportVerifiedEvent,
)
from src.modules.passport.domain.exceptions import PassportArchivedError
from src.modules.passport.domain.value_objects import (
    CustomsData,
    FullName,
    PassportValidationStatus,
)
from src.shared.interfaces.entities import AggregateRoot


@dataclass
class Passport(AggregateRoot):
    """Customer-owned customs passport.

    Lifecycle:

    * ``Passport.create(...)`` — new aggregate in ``PENDING`` validation.
    * ``update(...)`` — owner-driven mutation; ``mark_pending`` reset
      iff customs_data changed (DaData/DobroPost re-validation required).
    * ``mark_verified / mark_invalid`` — driven by future DaData
      consumer (not wired in Sprint 1.5 — FSM ready, transport later).
    * ``archive()`` — soft delete; archived passports cannot be
      mutated, and Order endpoints reject ``passport_id`` pointing at
      an archived row.

    Attributes:
        id: UUID (uuid4).
        identity_id: Owner identity. Cross-checked at every Order
            attach via ``IPassportLookup``.
        full_name: Holder name (RU + Latin).
        customs_data: Passport serial+number, issue date, birth date, INN.
        validation_status: PENDING | VERIFIED | INVALID.
        validation_failed_reason: Filled when status=INVALID.
        is_archived: Soft-delete flag.
        version, created_at, updated_at: Optimistic-lock & timestamps.
    """

    id: uuid.UUID
    identity_id: uuid.UUID
    full_name: FullName
    customs_data: CustomsData
    validation_status: PassportValidationStatus
    validation_failed_reason: str | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    version: int

    # TYPE-003 — guard ``validation_status`` against direct mutation.
    # mark_pending / mark_verified / mark_invalid use object.__setattr__.

    def __setattr__(self, name: str, value: object) -> None:
        if name == "validation_status" and getattr(
            self, "_Passport__initialized", False
        ):
            raise AttributeError(
                "Cannot set 'validation_status' directly on Passport. "
                "Use mark_pending() / mark_verified() / mark_invalid()."
            )
        super().__setattr__(name, value)

    def __attrs_post_init__(self) -> None:
        super().__attrs_post_init__()
        object.__setattr__(self, "_Passport__initialized", True)

    @classmethod
    def create(
        cls,
        *,
        identity_id: uuid.UUID,
        full_name: FullName,
        customs_data: CustomsData,
    ) -> Passport:
        now = datetime.now(UTC)
        passport = cls(
            id=uuid.uuid4(),
            identity_id=identity_id,
            full_name=full_name,
            customs_data=customs_data,
            validation_status=PassportValidationStatus.PENDING,
            validation_failed_reason=None,
            is_archived=False,
            created_at=now,
            updated_at=now,
            version=0,
        )
        passport.add_domain_event(
            PassportCreatedEvent(passport_id=passport.id, identity_id=identity_id)
        )
        return passport

    def _ensure_active(self) -> None:
        if self.is_archived:
            raise PassportArchivedError(passport_id=str(self.id))

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def update(
        self,
        *,
        full_name: FullName | None = None,
        customs_data: CustomsData | None = None,
    ) -> None:
        """Owner-driven mutation. Reset validation iff customs_data changed.

        Mirrors the recipient module's edit semantics: name-only edits
        (full_name) do NOT reset validation — DobroPost validates
        passport serial+number+issue date+birth date+INN, not the
        printed name. Customs-data changes invalidate the prior
        verification and require re-running DaData/DobroPost when
        that path is wired in a future SPEC.
        """
        self._ensure_active()
        customs_changed = False
        if full_name is not None and full_name != self.full_name:
            self.full_name = full_name
        if customs_data is not None and customs_data != self.customs_data:
            self.customs_data = customs_data
            customs_changed = True
        if customs_changed:
            object.__setattr__(
                self, "validation_status", PassportValidationStatus.PENDING
            )
            self.validation_failed_reason = None
        self.updated_at = datetime.now(UTC)
        self.add_domain_event(
            PassportUpdatedEvent(
                passport_id=self.id, customs_data_changed=customs_changed
            )
        )

    def mark_verified(self) -> None:
        self._ensure_active()
        if self.validation_status == PassportValidationStatus.VERIFIED:
            return  # idempotent
        object.__setattr__(self, "validation_status", PassportValidationStatus.VERIFIED)
        self.validation_failed_reason = None
        self.updated_at = datetime.now(UTC)
        self.add_domain_event(PassportVerifiedEvent(passport_id=self.id))

    def mark_invalid(self, *, reason: str) -> None:
        self._ensure_active()
        if self.validation_status == PassportValidationStatus.INVALID:
            self.validation_failed_reason = reason
            return  # idempotent on status, refresh reason
        object.__setattr__(self, "validation_status", PassportValidationStatus.INVALID)
        self.validation_failed_reason = reason
        self.updated_at = datetime.now(UTC)
        self.add_domain_event(
            PassportInvalidatedEvent(passport_id=self.id, reason=reason)
        )

    def archive(self) -> None:
        if self.is_archived:
            return
        self.is_archived = True
        self.updated_at = datetime.now(UTC)
        self.add_domain_event(PassportArchivedEvent(passport_id=self.id))
