"""DobroPost booking provider — implements ``IBookingProvider``.

Wraps ``POST /api/shipment``: synchronous booking — DobroPost returns
the full shipment object (including ``id`` and ``dptrackNumber``) in a
single response, no polling needed.

Cancellation is **not supported in production**: Loyality treats
post-procurement cancellation as Order ``CANCELLED + REFUND`` rather
than calling ``DELETE /api/shipment/{id}`` (operator coordinates with
DobroPost CS for partial-refund / customs return). The method returns
``CancelResult(success=False)`` so ``CancelShipmentHandler`` reverts
the local FSM via ``mark_cancellation_failed``.

Error mapping:

* ``400/422`` from DobroPost (bad passport, malformed phone, etc.) →
  ``ValidationError`` — operator-correctable. Caller surfaces the
  400 to the admin UI without flipping the shipment to FAILED.
* ``5xx`` / transport / unknown → ``ProviderUnavailableError`` —
  caller treats as transient, can retry.
* Missing ``id`` in 200-OK body → ``ProviderHTTPError`` 502 (provider
  contract violation; do NOT silently treat as success).
"""

from __future__ import annotations

import json
import logging

from src.modules.logistics.application.commands.dobropost_payload import (
    DobroPostShipmentPayload,
)
from src.modules.logistics.domain.exceptions import (
    ProviderUnavailableError,
)
from src.modules.logistics.domain.value_objects import (
    PROVIDER_DOBROPOST,
    BookingRequest,
    BookingResult,
    CancelResult,
    ProviderCode,
)
from src.modules.logistics.infrastructure.providers.dobropost.client import (
    DobroPostClient,
)
from src.modules.logistics.infrastructure.providers.dobropost.mappers import (
    build_create_shipment_request,
    parse_create_shipment_response,
)
from src.modules.logistics.infrastructure.providers.errors import (
    ProviderAuthError,
    ProviderHTTPError,
    ProviderTimeoutError,
)
from src.shared.exceptions import ValidationError

logger = logging.getLogger(__name__)


class DobroPostBookingProvider:
    """DobroPost implementation of ``IBookingProvider``."""

    def __init__(self, client: DobroPostClient) -> None:
        self._client = client

    def provider_code(self) -> ProviderCode:
        return PROVIDER_DOBROPOST

    async def book_shipment(self, request: BookingRequest) -> BookingResult:
        """Create a shipment in DobroPost.

        ``BookingRequest.provider_payload`` MUST be a JSON serialisation
        of ``DobroPostShipmentPayload`` — produced by the admin command
        (``CreateCrossBorderShipmentHandler``). Other ``BookingRequest``
        fields (origin, destination, sender, recipient, parcels) are
        ignored: DobroPost takes everything from the typed payload.
        """
        if not request.provider_payload:
            # Programming error from the caller — not a provider problem.
            raise ValidationError(
                message=(
                    "DobroPost booking requires provider_payload "
                    "(DobroPostShipmentPayload JSON)"
                ),
                error_code="DOBROPOST_PAYLOAD_MISSING",
            )

        try:
            payload = DobroPostShipmentPayload.from_json(request.provider_payload)
        except (KeyError, ValueError, TypeError) as exc:
            raise ValidationError(
                message=f"Malformed DobroPost provider_payload: {exc}",
                error_code="DOBROPOST_PAYLOAD_MALFORMED",
                details={"payload_excerpt": request.provider_payload[:512]},
            ) from exc

        body = build_create_shipment_request(payload)

        try:
            data = await self._client.create_shipment(body)
        except ProviderHTTPError as exc:
            # 4xx → operator-correctable input (bad passport, phone,
            # incomingDeclaration > 16 chars, etc). 5xx / transport →
            # transient carrier failure.
            if 400 <= exc.status_code < 500:
                raise ValidationError(
                    message=f"DobroPost rejected booking: {exc.message}",
                    error_code="DOBROPOST_BOOKING_REJECTED",
                    details={
                        "provider_status_code": exc.status_code,
                        "provider_response": (exc.response_body or "")[:1024],
                    },
                ) from exc
            raise ProviderUnavailableError(
                message=f"DobroPost booking failed: HTTP {exc.status_code}",
                details={
                    "provider_status_code": exc.status_code,
                    "provider_response": (exc.response_body or "")[:1024],
                },
            ) from exc
        except (ProviderTimeoutError, ProviderAuthError) as exc:
            raise ProviderUnavailableError(
                message=f"DobroPost unavailable: {exc}",
            ) from exc

        try:
            result = parse_create_shipment_response(data)
        except ValueError as exc:
            # 200 OK without ``id`` is a contract violation by the
            # provider — surface as 502 (bad gateway-style), NOT 4xx
            # (operator can't fix this).
            raise ProviderHTTPError(
                status_code=502,
                message=str(exc),
                response_body=json.dumps(data, ensure_ascii=False)[:2000],
            ) from exc

        logger.info(
            "DobroPost shipment created",
            extra={
                "dp_id": result.provider_shipment_id,
                "dp_track": result.tracking_number,
                "incoming_declaration": payload.incoming_declaration,
            },
        )
        return result

    async def cancel_shipment(self, provider_shipment_id: str) -> CancelResult:
        """Cancel = no-op on DobroPost side; refund handled by Order module.

        Returning ``success=False`` makes ``CancelShipmentHandler`` revert
        the FSM via ``mark_cancellation_failed`` and surface a clear
        ``CancellationError`` to the operator. Manual coordination with
        DobroPost customer service is required to actually stop the
        cross-border parcel.
        """
        logger.warning(
            "DobroPost cancel rejected — coordinate refund manually",
            extra={"dp_id": provider_shipment_id},
        )
        return CancelResult(
            success=False,
            reason=(
                "DobroPost shipment cancellation is not automated; "
                "coordinate refund with DobroPost CS and proceed via "
                "Order CANCELLED + REFUND flow."
            ),
        )
