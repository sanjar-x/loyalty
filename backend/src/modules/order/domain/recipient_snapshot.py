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
"""

from __future__ import annotations

from datetime import date

from attrs import frozen


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

    def with_updated_data(self, *, fresh: RecipientSnapshot) -> RecipientSnapshot:
        """Replace the snapshot with a fresh copy (refresh-recipient flow).

        ``recipient_id`` must match — the snapshot is always tied to the
        same Recipient identity.
        """
        if fresh.recipient_id != self.recipient_id:
            raise ValueError("RecipientSnapshot refresh must keep recipient_id stable")
        return fresh
