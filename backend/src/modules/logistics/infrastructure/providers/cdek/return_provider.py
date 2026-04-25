"""
CDEK return / refusal provider — implements ``IReturnProvider``.

Wraps three CDEK endpoints:
- POST /v2/orders/{uuid}/clientReturn — register a client return.
- POST /v2/orders/{uuid}/refusal — register a delivery refusal at the doorstep.
- POST /v2/reverse/availability — pre-flight check whether a reverse
  shipment is allowed for a given route / tariff / contacts.

The CDEK contract for these endpoints is sparse:

- ``clientReturn`` accepts only ``{"tariff_code": int}`` in the body
  and returns 202 + ``{"entity": {"uuid": ...}}``.
- ``refusal`` takes no body at all and returns 202 + same envelope.
- ``reverse/availability`` returns HTTP 200 with an empty body when
  the reverse path is feasible and HTTP 400 with an ``errors`` list
  otherwise. The 4xx is surfaced by ``CdekClient`` as a
  ``ProviderHTTPError`` which we translate into ``is_available=False``.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.modules.logistics.domain.value_objects import (
    PROVIDER_CDEK,
    Address,
    ClientReturnRequest,
    ProviderCode,
    RefusalRequest,
    ReturnResult,
    ReverseAvailabilityRequest,
    ReverseAvailabilityResult,
)
from src.modules.logistics.infrastructure.providers.cdek.client import CdekClient
from src.modules.logistics.infrastructure.providers.errors import ProviderHTTPError

logger = logging.getLogger(__name__)


class CdekReturnProvider:
    """CDEK implementation of ``IReturnProvider``."""

    def __init__(self, client: CdekClient) -> None:
        self._client = client

    def provider_code(self) -> ProviderCode:
        return PROVIDER_CDEK

    async def register_client_return(
        self, request: ClientReturnRequest
    ) -> ReturnResult:
        # CDEK accepts only ``tariff_code`` in the body — addresses,
        # contacts and parcels are inherited from the original order
        # referenced by ``order_provider_id``.
        body: dict[str, Any] = {"tariff_code": request.tariff_code}
        async with self._client:
            try:
                data = await self._client.register_client_return(
                    request.order_provider_id, body
                )
            except ProviderHTTPError as exc:
                return ReturnResult(success=False, reason=str(exc))

        provider_return_id = _extract_root_uuid(data)
        return ReturnResult(
            success=True,
            provider_return_id=provider_return_id,
            raw_response=json.dumps(data, ensure_ascii=False, default=str),
        )

    async def register_refusal(self, request: RefusalRequest) -> ReturnResult:
        # CDEK refusal endpoint takes no body. ``request.reason`` is
        # logged here for audit but never wired into the request.
        if request.reason:
            logger.info(
                "CDEK refusal note (audit only)",
                extra={
                    "order_provider_id": request.order_provider_id,
                    "reason": request.reason,
                },
            )
        async with self._client:
            try:
                data = await self._client.register_refusal(
                    request.order_provider_id, None
                )
            except ProviderHTTPError as exc:
                return ReturnResult(success=False, reason=str(exc))

        provider_return_id = _extract_root_uuid(data)
        return ReturnResult(
            success=True,
            provider_return_id=provider_return_id,
            raw_response=json.dumps(data, ensure_ascii=False, default=str),
        )

    async def check_reverse_availability(
        self, request: ReverseAvailabilityRequest
    ) -> ReverseAvailabilityResult:
        body = _build_reverse_request(request)
        async with self._client:
            try:
                data = await self._client.check_reverse_availability(body)
            except ProviderHTTPError as exc:
                # CDEK signals "reverse not available" with HTTP 400 +
                # an ``errors`` list. Anything else (5xx, network) is
                # also propagated as "not available" with the raw
                # diagnostic preserved for the operator.
                reason = _format_errors(exc.response_body) or str(exc)
                return ReverseAvailabilityResult(
                    is_available=False,
                    reason=reason,
                    raw_response=exc.response_body,
                )

        # 200 with an empty body == "available". CDEK never echoes
        # ``available: true`` — the absence of an error envelope is
        # the signal.
        return ReverseAvailabilityResult(
            is_available=True,
            reason=None,
            raw_response=json.dumps(data, ensure_ascii=False, default=str)
            if data
            else None,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_root_uuid(data: Any) -> str | None:
    """Pull ``entity.uuid`` from a ``ResponseDtoRootEntityDto`` envelope."""
    if not isinstance(data, dict):
        return None
    entity = data.get("entity")
    if not isinstance(entity, dict):
        return None
    raw = entity.get("uuid")
    return str(raw) if raw else None


def _format_errors(response_body: str | None) -> str | None:
    """Render a CDEK ``errors`` list into a single human-readable string."""
    if not response_body:
        return None
    try:
        parsed = json.loads(response_body)
    except (TypeError, ValueError) as _exc:
        return None
    if not isinstance(parsed, dict):
        return None
    errors = parsed.get("errors")
    if not isinstance(errors, list) or not errors:
        return None
    return "; ".join(
        f"{e.get('code', '?')}: {e.get('message', '?')}"
        for e in errors
        if isinstance(e, dict)
    )


def _build_reverse_request(req: ReverseAvailabilityRequest) -> dict[str, Any]:
    body: dict[str, Any] = {
        "tariff_code": req.tariff_code,
        "sender": _build_reverse_party(req.sender_phones, req.sender_contragent_type),
        "recipient": _build_reverse_party(
            req.recipient_phones, req.recipient_contragent_type
        ),
    }
    # Origin: either a pickup point code OR a from_location dict.
    if req.shipment_point:
        body["shipment_point"] = req.shipment_point
    elif req.from_location is not None:
        body["from_location"] = _build_reverse_location(req.from_location)
    # Destination: either a delivery point code OR a to_location dict.
    if req.delivery_point:
        body["delivery_point"] = req.delivery_point
    elif req.to_location is not None:
        body["to_location"] = _build_reverse_location(req.to_location)
    return body


def _build_reverse_party(
    phones: tuple[str, ...], contragent_type: str | None
) -> dict[str, Any]:
    party: dict[str, Any] = {
        "phones": [{"number": p} for p in phones if p],
    }
    if contragent_type:
        party["contragent_type"] = contragent_type
    return party


def _build_reverse_location(address: Address) -> dict[str, Any]:
    """Build CDEK ``ReverseValidateRequest{From,To}LocationDto``."""
    loc: dict[str, Any] = {}
    if address.metadata.get("cdek_city_code"):
        loc["code"] = int(address.metadata["cdek_city_code"])
    if address.metadata.get("fias_guid"):
        loc["fias_guid"] = address.metadata["fias_guid"]
    if address.country_code:
        loc["country_code"] = address.country_code
    if address.region:
        loc["region"] = address.region
    if address.city:
        loc["city"] = address.city
    if address.postal_code:
        loc["postal_code"] = address.postal_code
    if address.latitude is not None:
        loc["latitude"] = address.latitude
    if address.longitude is not None:
        loc["longitude"] = address.longitude
    parts = []
    if address.street:
        parts.append(address.street)
    if address.house:
        parts.append(f"д. {address.house}")
    if address.apartment:
        parts.append(f"кв. {address.apartment}")
    if parts:
        loc["address"] = ", ".join(parts)
    elif address.raw_address:
        loc["address"] = address.raw_address
    return loc
