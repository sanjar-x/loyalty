"""
CDEK return / refusal provider — implements ``IReturnProvider``.

Wraps three CDEK endpoints:
- POST /v2/orders/{uuid}/clientReturn — register a client return.
- POST /v2/orders/{uuid}/refusal — register a delivery refusal at the doorstep.
- POST /v2/reverse/availability — pre-flight check whether a reverse
  shipment is allowed for a given order / route / tariff.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.modules.logistics.domain.value_objects import (
    PROVIDER_CDEK,
    ClientReturnRequest,
    ProviderCode,
    RefusalRequest,
    ReturnResult,
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
        body: dict[str, Any] = {"tariff_code": request.tariff_code}
        if request.comment:
            body["comment"] = request.comment
        async with self._client:
            try:
                data = await self._client.register_client_return(
                    request.order_provider_id, body
                )
            except ProviderHTTPError as exc:
                return ReturnResult(success=False, reason=str(exc))

        provider_return_id = ""
        if isinstance(data, dict):
            entity = data.get("entity")
            if isinstance(entity, dict):
                provider_return_id = str(entity.get("uuid") or "")
        return ReturnResult(
            success=True,
            provider_return_id=provider_return_id or None,
            raw_response=json.dumps(data, ensure_ascii=False, default=str),
        )

    async def register_refusal(self, request: RefusalRequest) -> ReturnResult:
        body: dict[str, Any] = {}
        if request.reason:
            body["comment"] = request.reason
        async with self._client:
            try:
                data = await self._client.register_refusal(
                    request.order_provider_id, body
                )
            except ProviderHTTPError as exc:
                return ReturnResult(success=False, reason=str(exc))

        return ReturnResult(
            success=True,
            raw_response=json.dumps(data, ensure_ascii=False, default=str),
        )

    async def check_reverse_availability(
        self, provider_shipment_id: str
    ) -> ReverseAvailabilityResult:
        body: dict[str, Any] = {"order_uuid": provider_shipment_id}
        async with self._client:
            try:
                data = await self._client.check_reverse_availability(body)
            except ProviderHTTPError as exc:
                return ReverseAvailabilityResult(
                    is_available=False,
                    reason=str(exc),
                )

        is_available = False
        reason: str | None = None
        if isinstance(data, dict):
            entity = data.get("entity") or data
            if isinstance(entity, dict):
                # CDEK signals availability with ``available`` (bool) on
                # the entity payload. Errors live at top level under
                # ``errors``. Be tolerant — the docs list both shapes.
                is_available = bool(entity.get("available", False))
            errors = data.get("errors")
            if isinstance(errors, list) and errors:
                reason = "; ".join(
                    f"{e.get('code', '?')}: {e.get('message', '?')}" for e in errors
                )

        return ReverseAvailabilityResult(
            is_available=is_available,
            reason=reason,
            raw_response=json.dumps(data, ensure_ascii=False, default=str),
        )
