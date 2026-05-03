"""DobroPost webhook receiver.

Path-token + IP-whitelist authentication (research §10.5.3 — DobroPost
does not publish a signing scheme). The receiver normalises the two
DobroPost payload shapes into a single canonical event, persists the
event into ``outbox_messages``, and returns 204. The outbox relay
picks it up and dispatches to the matching consumer through TaskIQ;
``order_inbox_events`` deduplicates retries on the consumer side.

Endpoints:
* ``POST /api/v1/orders/webhooks/dobropost/{token}`` — accepts both
  ``passportValidationStatus`` payloads and ``status``/``DPTrackNumber``
  payloads. Returns 204 on success, 401 on bad token, 403 on bad IP.
"""

from __future__ import annotations

import hmac
import json
import uuid
from typing import Any

import structlog
from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Body, HTTPException, Path, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.bootstrap.config import settings
from src.infrastructure.database.models.outbox import OutboxMessage
from src.modules.order.infrastructure.dobropost_status_map import (
    name_to_status_id,
)

logger = structlog.get_logger(__name__)

dobropost_webhook_router = APIRouter(
    prefix="/webhooks/dobropost",
    tags=["Webhooks / DobroPost"],
    route_class=DishkaRoute,
)

# UUID5 namespace for deterministic event_id derivation. Same payload
# from a DobroPost retry yields the same event_id → inbox dedup works
# without DobroPost having to send an explicit event_id.
_DOBROPOST_NS = uuid.UUID("8b6a3f50-e9b2-4d28-a26a-26b16f5dee20")


def _check_token(token: str) -> None:
    expected = settings.DOBROPOST_WEBHOOK_TOKEN.get_secret_value()
    if not expected or not hmac.compare_digest(token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook token",
        )


def _check_source_ip(request: Request) -> None:
    allowed = settings.DOBROPOST_ALLOWED_IPS
    if not allowed:
        return  # whitelist disabled — accept all
    client_host = request.client.host if request.client else ""
    if client_host not in allowed:
        logger.warning("dobropost.webhook.ip_rejected", client_host=client_host)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Source IP not allowed",
        )


def _coerce_int(value: Any) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except TypeError, ValueError:
        return None


def _resolve_status_id(payload: dict) -> int | None:
    """Pick the most specific numeric status_id available in payload."""
    raw = payload.get("status_id") or payload.get("statusId")
    sid = _coerce_int(raw)
    if sid is not None:
        return sid
    text = payload.get("status")
    if isinstance(text, str):
        return name_to_status_id(text)
    return None


def _enqueue(
    session: AsyncSession,
    *,
    event_type: str,
    dp_shipment_id: int | None,
    payload: dict[str, Any],
    correlation_id: str | None,
) -> None:
    """Insert an outbox row in the request transaction.

    The relay's at-least-once delivery + the consumer-side inbox dedup
    table together provide effectively-exactly-once semantics.
    """
    aggregate_id = str(dp_shipment_id) if dp_shipment_id is not None else "unknown"
    seed = json.dumps(
        {"event_type": event_type, "agg": aggregate_id, "payload": payload},
        sort_keys=True,
        default=str,
    )
    event_id = uuid.uuid5(_DOBROPOST_NS, seed)
    enriched = {**payload, "event_id": str(event_id)}
    session.add(
        OutboxMessage(
            aggregate_type="DobroPostShipment",
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=enriched,
            correlation_id=correlation_id,
        )
    )


@dobropost_webhook_router.post("/{token}", status_code=status.HTTP_204_NO_CONTENT)
async def dobropost_webhook(
    request: Request,
    session: FromDishka[AsyncSession],
    payload: dict[str, Any] = Body(...),
    token: str = Path(..., min_length=8, max_length=128),
) -> None:
    _check_token(token)
    _check_source_ip(request)

    correlation_id = request.headers.get("x-request-id") or request.headers.get(
        "x-correlation-id"
    )
    dp_shipment_id = _coerce_int(
        payload.get("shipmentId")
        or payload.get("dpShipmentId")
        or payload.get("dp_shipment_id")
    )

    # ---- Passport-validation payload ----
    if "passportValidationStatus" in payload:
        valid = payload.get("passportValidationStatus")
        normalized = {
            "dp_shipment_id": dp_shipment_id,
            "passport_validation_status": valid,
        }
        _enqueue(
            session,
            event_type="DobroPostPassportInvalidEvent",
            dp_shipment_id=dp_shipment_id,
            payload=normalized,
            correlation_id=correlation_id,
        )
        await session.commit()
        logger.info(
            "dobropost.webhook.passport_payload",
            dp_shipment_id=dp_shipment_id,
            valid=valid,
        )
        return None

    # ---- Status update payload ----
    if (
        "DPTrackNumber" in payload
        or "dpTrackNumber" in payload
        or "status" in payload
        or "statusId" in payload
        or "status_id" in payload
    ):
        status_id = _resolve_status_id(payload)
        track = payload.get("DPTrackNumber") or payload.get("dpTrackNumber")
        normalized = {
            "dp_shipment_id": dp_shipment_id,
            "status_id": status_id,
            "status_label": payload.get("status"),
            "dp_track_number": track,
        }
        _enqueue(
            session,
            event_type="DobroPostStatusUpdatedEvent",
            dp_shipment_id=dp_shipment_id,
            payload=normalized,
            correlation_id=correlation_id,
        )
        await session.commit()
        logger.info(
            "dobropost.webhook.status_payload",
            dp_shipment_id=dp_shipment_id,
            status_id=status_id,
            track=track,
        )
        return None

    logger.warning("dobropost.webhook.unknown_shape", keys=list(payload.keys()))
    return None


__all__ = ["dobropost_webhook_router"]
