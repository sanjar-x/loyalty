"""Payload structures for DobroPost-specific shipment data.

DobroPost requires fields that are *not* part of the generic
``BookingRequest`` (ContactInfo + Parcel) — namely passport / ИНН /
``incomingDeclaration`` / ``dpTariffId`` / item description / store URL.
The Loyality booking flow (admin-managed cross-border command) packs
these into a JSON blob that becomes ``Shipment.provider_payload``;
``DobroPostBookingProvider`` deserialises and uses them.

Keeping the shape here (single source of truth) means the command
layer and the provider adapter cannot drift.

The DobroPost-assigned ``id`` (``provider_shipment_id``) and
``dptrackNumber`` (``tracking_number``) live as first-class columns on
the ``Shipment`` aggregate after booking — they are *not* duplicated
back into the JSON payload (the payload stays a faithful representation
of the *request* that built the carrier order, used for replay /
``PUT /api/shipment`` corrective updates).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DobroPostRecipientPassport:
    """Passport / ИНН of the customs recipient — DobroPost mandatory.

    Field validations (mirror ``reference.md`` §2):
    - ``passport_serial`` exactly 4 chars.
    - ``passport_number`` exactly 6 chars.
    - ``vat_identification_number`` (ИНН) exactly 12 chars.
    - ``birth_date`` mandatory only for tariff "DP Ultra".
    """

    family_name: str
    name: str
    middle_name: str | None
    passport_serial: str
    passport_number: str
    passport_issue_date: date
    vat_identification_number: str
    full_address: str
    city: str
    state: str
    zip_code: str
    phone_number: str
    email: str
    birth_date: date | None = None  # required only for DP Ultra tariff


@dataclass(frozen=True)
class DobroPostItem:
    """Item description for customs declaration."""

    description: str  # < 60 chars per DobroPost validation
    pieces: int
    price_cny: float  # per-unit price in CNY (yuan)
    store_link: str  # URL to the listing on the Chinese marketplace


@dataclass(frozen=True)
class DobroPostShipmentPayload:
    """Everything DobroPost needs in ``POST /api/shipment``.

    ``incoming_declaration`` is the China-side carrier track that the
    manager pastes after buying the item from a Chinese marketplace.
    ``dp_tariff_id`` selects DobroPost's fixed tariff (manager-picked,
    no rate calc).
    """

    total_amount_cny: float
    recipient: DobroPostRecipientPassport
    item: DobroPostItem
    dp_tariff_id: int
    incoming_declaration: str  # < 16 chars per DobroPost validation
    comment: str | None = None  # < 60 chars; appears on shipping label

    # ------------------------------------------------------------------
    # Serialization — None fields are omitted to keep the stored
    # ``Shipment.provider_payload`` JSON compact and audit-friendly.
    # ------------------------------------------------------------------

    def to_json(self) -> str:
        """Serialise to the string stored on ``Shipment.provider_payload``."""
        return json.dumps(self._to_dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> DobroPostShipmentPayload:
        """Deserialise from ``Shipment.provider_payload``."""
        data = json.loads(raw)
        return cls._from_dict(data)

    def _to_dict(self) -> dict:
        rec_dict: dict = {
            "family_name": self.recipient.family_name,
            "name": self.recipient.name,
            "passport_serial": self.recipient.passport_serial,
            "passport_number": self.recipient.passport_number,
            "passport_issue_date": self.recipient.passport_issue_date.isoformat(),
            "vat_identification_number": self.recipient.vat_identification_number,
            "full_address": self.recipient.full_address,
            "city": self.recipient.city,
            "state": self.recipient.state,
            "zip_code": self.recipient.zip_code,
            "phone_number": self.recipient.phone_number,
            "email": self.recipient.email,
        }
        if self.recipient.middle_name:
            rec_dict["middle_name"] = self.recipient.middle_name
        if self.recipient.birth_date:
            rec_dict["birth_date"] = self.recipient.birth_date.isoformat()
        out: dict = {
            "total_amount_cny": self.total_amount_cny,
            "recipient": rec_dict,
            "item": {
                "description": self.item.description,
                "pieces": self.item.pieces,
                "price_cny": self.item.price_cny,
                "store_link": self.item.store_link,
            },
            "dp_tariff_id": self.dp_tariff_id,
            "incoming_declaration": self.incoming_declaration,
        }
        if self.comment:
            out["comment"] = self.comment
        return out

    @classmethod
    def _from_dict(cls, data: dict) -> DobroPostShipmentPayload:
        rec = data["recipient"]
        item = data["item"]
        return cls(
            total_amount_cny=float(data["total_amount_cny"]),
            recipient=DobroPostRecipientPassport(
                family_name=rec["family_name"],
                name=rec["name"],
                middle_name=rec.get("middle_name"),
                passport_serial=rec["passport_serial"],
                passport_number=rec["passport_number"],
                passport_issue_date=date.fromisoformat(rec["passport_issue_date"]),
                birth_date=(
                    date.fromisoformat(rec["birth_date"])
                    if rec.get("birth_date")
                    else None
                ),
                vat_identification_number=rec["vat_identification_number"],
                full_address=rec["full_address"],
                city=rec["city"],
                state=rec["state"],
                zip_code=rec["zip_code"],
                phone_number=rec["phone_number"],
                email=rec["email"],
            ),
            item=DobroPostItem(
                description=item["description"],
                pieces=int(item["pieces"]),
                price_cny=float(item["price_cny"]),
                store_link=item["store_link"],
            ),
            dp_tariff_id=int(data["dp_tariff_id"]),
            incoming_declaration=data["incoming_declaration"],
            comment=data.get("comment"),
        )
