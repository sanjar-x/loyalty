"""Frozen snapshots persisted on the Order aggregate.

Two independent snapshots live here (post-Sprint-1.5 Part 2 / ADR-011):

* :class:`RecipientSnapshot` — shipping coordinates copy (name, phone,
  email) taken at checkout time. Stable even if the customer edits
  their Recipient row later. ALWAYS present on every order.

* :class:`PassportSnapshot` — customs PII copy (full name on passport,
  serial+number+issue date+birth date+INN, validation status). Present
  on cross-border orders and OPTIONAL for local-supplier orders. The
  Order invariant in ``Order.create`` raises
  ``PassportRequiredForCrossBorderError`` when a cross-border item
  appears without a passport snapshot.

Both shapes are kept local to the Order BC (the order module imports
neither recipient.domain.value_objects nor passport.domain.value_objects
in its domain layer — see the ACL adapters in
``order.infrastructure.adapters`` for the cross-module reads).

TYPE-005 — defense-in-depth ``__attrs_post_init__`` validation.
Recipient / Passport own VOs validate the same invariants at the
source; these checks here are a tripwire on the Order side, since
snapshots survive any subsequent edits via ``with_updated_data`` /
``with_updated_passport``.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Final

from attrs import frozen

# Format patterns (shared with the source modules' VOs).
_PASSPORT_SERIAL_RE: Final = re.compile(r"^\d{4}$")
_PASSPORT_NUMBER_RE: Final = re.compile(r"^\d{6}$")
_PHONE_RE: Final = re.compile(r"^\+?\d{8,15}$")
_EMAIL_RE: Final = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
_INN_RE: Final = re.compile(r"^\d{12}$")


@frozen
class RecipientSnapshot:
    """Immutable shipping-coordinate copy of a Recipient at checkout time.

    Post-Sprint-1.5 Part 2: customs identifiers extracted to
    :class:`PassportSnapshot`. RecipientSnapshot is required on every
    order (every parcel needs a name + contact); PassportSnapshot is
    cross-border only.
    """

    recipient_id: str  # str-encoded UUID (snapshot survives recipient deletion)
    full_name_ru: str
    full_name_lat: str
    phone: str
    email: str

    def __attrs_post_init__(self) -> None:
        if not self.full_name_ru.strip():
            raise ValueError("RecipientSnapshot.full_name_ru must be non-empty")
        if not self.full_name_lat.strip():
            raise ValueError("RecipientSnapshot.full_name_lat must be non-empty")
        if not _PHONE_RE.match(self.phone):
            raise ValueError(
                f"RecipientSnapshot.phone {self.phone!r} is not a valid "
                "E.164-shaped phone number (8-15 digits, optional leading +)"
            )
        if not _EMAIL_RE.match(self.email):
            raise ValueError(
                f"RecipientSnapshot.email {self.email!r} is not a valid email"
            )

    def with_updated_data(self, *, fresh: RecipientSnapshot) -> RecipientSnapshot:
        """Replace the snapshot with a fresh copy.

        ``recipient_id`` must match — the snapshot is always tied to
        the same Recipient identity.
        """
        if fresh.recipient_id != self.recipient_id:
            raise ValueError("RecipientSnapshot refresh must keep recipient_id stable")
        return fresh


@frozen
class PassportSnapshot:
    """Immutable customs-PII copy of a Passport at checkout time.

    Present on every cross-border order (Order invariant). Optional for
    local-supplier orders — they don't pass through customs. Carries
    enough data to reconstruct the customs declaration even if the
    customer later archives the Passport row.

    Attributes:
        passport_id: str-encoded UUID of the source Passport.
        full_name_ru: Name as printed on the passport (Cyrillic).
        full_name_lat: Same name transliterated (Latin) — what DobroPost
            forwards to the customs officer.
        passport_serial: 4 digits.
        passport_number: 6 digits.
        passport_issue_date: Issue date (≥ 1991-01-01 ≤ today at the
            source — here we don't re-check date bounds because the
            snapshot can lawfully be older than 1991 if the migration
            inherits historical data).
        birth_date: Holder birth date.
        inn: 12-digit ИНН ФЛ (Минфин checksum verified at the source).
        validation_status: ``pending`` | ``verified`` | ``invalid`` at
            checkout time. Frozen on the order — later edits to the
            Passport do NOT mutate the snapshot.
    """

    passport_id: str
    full_name_ru: str
    full_name_lat: str
    passport_serial: str
    passport_number: str
    passport_issue_date: date
    birth_date: date
    inn: str
    validation_status: str

    def __attrs_post_init__(self) -> None:
        if not self.full_name_ru.strip():
            raise ValueError("PassportSnapshot.full_name_ru must be non-empty")
        if not self.full_name_lat.strip():
            raise ValueError("PassportSnapshot.full_name_lat must be non-empty")
        if not _PASSPORT_SERIAL_RE.match(self.passport_serial):
            raise ValueError(
                f"PassportSnapshot.passport_serial {self.passport_serial!r} "
                "must be exactly 4 digits"
            )
        if not _PASSPORT_NUMBER_RE.match(self.passport_number):
            raise ValueError(
                f"PassportSnapshot.passport_number {self.passport_number!r} "
                "must be exactly 6 digits"
            )
        if not _INN_RE.match(self.inn):
            raise ValueError(
                f"PassportSnapshot.inn {self.inn!r} must be exactly 12 digits"
            )

    def with_updated_passport(self, *, fresh: PassportSnapshot) -> PassportSnapshot:
        """Replace the snapshot with a fresh copy (refresh-passport flow).

        ``passport_id`` must match — the snapshot is always tied to
        the same Passport identity.
        """
        if fresh.passport_id != self.passport_id:
            raise ValueError("PassportSnapshot refresh must keep passport_id stable")
        return fresh
