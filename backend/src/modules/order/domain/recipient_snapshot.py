"""Frozen snapshot of a Recipient's data at order-creation time.

The Order aggregate carries this snapshot so that customs declarations
sent to DobroPost are stable even if the customer later edits the
underlying Recipient. The snapshot is regenerated only via the explicit
``refresh_recipient`` admin/customer command after a passport-validation
failure puts the order ``ON_HOLD``.

The shape mirrors ``recipient.domain.value_objects.CustomsData`` plus
the contact identifiers, but lives inside the Order BC to avoid a
domain dependency on the Recipient module (only the ACL adapter in
``order.infrastructure.adapters.recipient_lookup`` knows about
Recipient).

TYPE-005 — added ``__attrs_post_init__`` field validation so a buggy
ACL adapter cannot persist customs garbage. Recipient's own
``CustomsData`` / ``Phone`` / ``Email`` / ``FullName`` VOs validate
the same invariants at the source — these checks here are a
defense-in-depth tripwire on the Order side, since the snapshot
survives Recipient edits via ``with_updated_data``.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Final

from attrs import frozen

# Validation patterns (mirroring recipient/domain/value_objects.py).
_PASSPORT_SERIAL_RE: Final = re.compile(r"^\d{4}$")
_PASSPORT_NUMBER_RE: Final = re.compile(r"^\d{6}$")
# E.164 phone (loose — accepts +CCxxxxxx with 8-15 digits incl. country code).
_PHONE_RE: Final = re.compile(r"^\+?\d{8,15}$")
# Permissive email regex: alphanumeric + ``._%+-`` local, domain has at
# least one dot, TLD is 2+ letters. Same shape as recipient.Email.
_EMAIL_RE: Final = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
# INN: 12 digits (individuals) per Минфин format. Checksum verification
# happens at the recipient-VO layer; here we only enforce the length
# and digit-only invariant so an obviously-malformed INN cannot land
# in the snapshot at all.
_INN_RE: Final = re.compile(r"^\d{12}$")


@frozen
class RecipientSnapshot:
    """Immutable copy of a Recipient at checkout time."""

    recipient_id: str  # str-encoded UUID (snapshot survives recipient deletion)
    full_name_ru: str
    full_name_lat: str
    phone: str
    email: str
    passport_serial: str
    passport_number: str
    passport_issue_date: date
    birth_date: date
    inn: str

    def __attrs_post_init__(self) -> None:
        """Defense-in-depth validation (TYPE-005).

        Raises:
            ValueError: When any field fails the format check. The
                error message names the field so observability can
                pinpoint which boundary leaked.
        """
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
        if not _PASSPORT_SERIAL_RE.match(self.passport_serial):
            raise ValueError(
                f"RecipientSnapshot.passport_serial {self.passport_serial!r} "
                "must be exactly 4 digits"
            )
        if not _PASSPORT_NUMBER_RE.match(self.passport_number):
            raise ValueError(
                f"RecipientSnapshot.passport_number {self.passport_number!r} "
                "must be exactly 6 digits"
            )
        if not _INN_RE.match(self.inn):
            raise ValueError(
                f"RecipientSnapshot.inn {self.inn!r} must be exactly 12 digits"
            )

    def with_updated_data(self, *, fresh: RecipientSnapshot) -> RecipientSnapshot:
        """Replace the snapshot with a fresh copy (refresh-recipient flow).

        ``recipient_id`` must match — the snapshot is always tied to
        the same Recipient identity. ``fresh`` is itself constructed
        via the same validators (``__attrs_post_init__``), so
        re-validation is guaranteed even when admin tooling refreshes
        the snapshot post-PASSPORT_INVALID hold.
        """
        if fresh.recipient_id != self.recipient_id:
            raise ValueError("RecipientSnapshot refresh must keep recipient_id stable")
        return fresh
