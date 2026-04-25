"""
CDEK intake provider — implements ``IIntakeProvider``.

Wraps the four ``/v2/intakes`` endpoints into a unified capability:
- POST /v2/intakes/availableDays — list pickup-eligible dates.
- POST /v2/intakes — register a courier-pickup request.
- GET /v2/intakes/{uuid} — poll intake status.
- DELETE /v2/intakes/{uuid} — cancel an unfulfilled intake.
"""

from __future__ import annotations

import json
import logging

from src.modules.logistics.domain.value_objects import (
    PROVIDER_CDEK,
    Address,
    ContactInfo,
    IntakeRequest,
    IntakeResult,
    IntakeStatus,
    IntakeWindow,
    ProviderCode,
)
from src.modules.logistics.infrastructure.providers.cdek.client import CdekClient
from src.modules.logistics.infrastructure.providers.cdek.constants import (
    CDEK_INTAKE_STATUS_ACCEPTED,
    CDEK_INTAKE_STATUS_CANCELLED,
    CDEK_INTAKE_STATUS_COMPLETED,
    CDEK_INTAKE_STATUS_DELAYED,
    CDEK_INTAKE_STATUS_WAITING,
)
from src.modules.logistics.infrastructure.providers.errors import ProviderHTTPError

logger = logging.getLogger(__name__)


_CDEK_INTAKE_STATUS_MAP = {
    CDEK_INTAKE_STATUS_ACCEPTED: IntakeStatus.ACCEPTED,
    CDEK_INTAKE_STATUS_WAITING: IntakeStatus.WAITING,
    CDEK_INTAKE_STATUS_DELAYED: IntakeStatus.DELAYED,
    CDEK_INTAKE_STATUS_COMPLETED: IntakeStatus.COMPLETED,
    CDEK_INTAKE_STATUS_CANCELLED: IntakeStatus.CANCELLED,
}


class CdekIntakeProvider:
    """CDEK implementation of ``IIntakeProvider``."""

    def __init__(self, client: CdekClient) -> None:
        self._client = client

    def provider_code(self) -> ProviderCode:
        return PROVIDER_CDEK

    async def get_available_days(
        self,
        from_address: Address,
        until: str | None = None,
    ) -> list[IntakeWindow]:
        body: dict = {"from_location": _build_intake_location(from_address)}
        if until:
            body["date"] = until
        async with self._client:
            data = await self._client.get_intake_available_days(body)
        return _parse_available_days(data)

    async def create_intake(self, request: IntakeRequest) -> IntakeResult:
        body = _build_intake_request(request)
        async with self._client:
            data = await self._client.create_intake(body)

        entity = data.get("entity", {}) if isinstance(data, dict) else {}
        provider_intake_id = entity.get("uuid") or ""
        if not provider_intake_id:
            raise ProviderHTTPError(
                status_code=0,
                message="No entity UUID in CDEK intake creation response",
                response_body=json.dumps(data, ensure_ascii=False),
            )
        return IntakeResult(
            provider_intake_id=provider_intake_id,
            status=IntakeStatus.ACCEPTED,
            raw_response=json.dumps(data, ensure_ascii=False, default=str),
        )

    async def get_intake(self, provider_intake_id: str) -> IntakeStatus:
        async with self._client:
            data = await self._client.get_intake(provider_intake_id)
        entity = data.get("entity", data) if isinstance(data, dict) else {}
        statuses = entity.get("statuses", []) if isinstance(entity, dict) else []
        if not statuses:
            return IntakeStatus.UNKNOWN
        latest = statuses[-1]
        code = latest.get("code", "") if isinstance(latest, dict) else ""
        return _CDEK_INTAKE_STATUS_MAP.get(code, IntakeStatus.UNKNOWN)

    async def cancel_intake(self, provider_intake_id: str) -> bool:
        async with self._client:
            try:
                await self._client.delete_intake(provider_intake_id)
            except ProviderHTTPError:
                logger.exception("CDEK intake cancel failed", exc_info=True)
                return False
        return True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_intake_location(address: Address) -> dict:
    """Build CDEK intake-location dict from an Address VO."""
    loc: dict = {}
    if address.metadata.get("cdek_city_code"):
        loc["code"] = int(address.metadata["cdek_city_code"])
    if address.postal_code:
        loc["postal_code"] = address.postal_code
    if address.country_code:
        loc["country_code"] = address.country_code
    if address.city:
        loc["city"] = address.city
    parts = []
    if address.street:
        parts.append(address.street)
    if address.house:
        parts.append(f"д. {address.house}")
    if address.apartment:
        parts.append(f"кв. {address.apartment}")
    loc["address"] = ", ".join(parts) if parts else address.raw_address or address.city
    return loc


def _build_intake_request(req: IntakeRequest) -> dict:
    """Build CDEK ``POST /v2/intakes`` request body."""
    parcel = req.package
    body: dict = {
        "intake_date": req.intake_date,
        "intake_time_from": req.intake_time_from,
        "intake_time_to": req.intake_time_to,
        "name": parcel.description or "Заказ интернет-магазина",
        "weight": parcel.weight.grams,
        "from_location": _build_intake_location(req.from_address),
        "sender": _build_intake_contact(req.sender),
        "need_call": req.need_call,
    }
    if parcel.dimensions:
        body["length"] = parcel.dimensions.length_cm
        body["width"] = parcel.dimensions.width_cm
        body["height"] = parcel.dimensions.height_cm
    if req.lunch_time_from:
        body["lunch_time_from"] = req.lunch_time_from
    if req.lunch_time_to:
        body["lunch_time_to"] = req.lunch_time_to
    if req.comment:
        body["comment"] = req.comment
    if req.order_provider_id:
        body["order_uuid"] = req.order_provider_id
    return body


def _build_intake_contact(contact: ContactInfo) -> dict:
    """Build CDEK intake-contact from a ContactInfo VO."""
    result: dict = {"name": contact.full_name}
    if contact.phone:
        result["phones"] = [{"number": contact.phone}]
    if contact.email:
        result["email"] = contact.email
    if contact.company_name:
        result["company"] = contact.company_name
    return result


def _parse_available_days(data: dict) -> list[IntakeWindow]:
    """Parse CDEK ``/v2/intakes/availableDays`` response into IntakeWindow list."""
    if not isinstance(data, dict):
        return []
    dates = data.get("date") or []
    if data.get("all_days") is True:
        # CDEK signals "all days available" by setting ``all_days=true``;
        # we synthesise nothing — caller should fall back to its own
        # calendar. Returning an empty list communicates the absence of
        # explicit windows without losing the intent.
        return []
    result: list[IntakeWindow] = []
    if isinstance(dates, list):
        for entry in dates:
            if isinstance(entry, str):
                result.append(IntakeWindow(date=entry))
            elif isinstance(entry, dict):
                date_str = entry.get("date") or entry.get("value") or ""
                if date_str:
                    result.append(IntakeWindow(date=date_str))
    return result
