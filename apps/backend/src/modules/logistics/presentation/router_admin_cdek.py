"""
Admin REST router for CDEK-specific operations — ``/admin/logistics/cdek``.

CDEK exposes a large surface that has no carrier-agnostic capability
protocol: order editing, delivery agreements, prealerts, fiscal
receipts, COD registries, international restriction hints, photo
documents, the tariff catalogue, location lookups and order-intake
inspection. Rather than widen the shared ``logistics`` domain ports for
one carrier, those operations live here as a CDEK-local admin surface
backed by :class:`CdekAdminService` (built per request from the active
CDEK provider account).

These endpoints are a thin operator-facing proxy: request bodies are
forwarded to CDEK verbatim under a ``payload`` envelope and responses
are wrapped in :class:`CdekJsonResponse` with CDEK's ``errors`` /
``warnings`` lifted out. Provider HTTP failures are translated into the
standard error envelope — a CDEK 4xx becomes a 422, a 5xx / timeout /
auth failure becomes a 503.

Permissions mirror ``router_admin_shipments.py``: ``logistics:read`` for
lookups, ``logistics:write`` for mutations.
"""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Path, Query, Response, status

from src.modules.identity.presentation.dependencies import (
    RequirePermission,
    RequireStaffRole,
)
from src.modules.logistics.domain.exceptions import ProviderUnavailableError
from src.modules.logistics.infrastructure.providers.cdek.admin_service import (
    CdekAdminService,
)
from src.modules.logistics.infrastructure.providers.cdek.constants import (
    CDEK_WEBHOOK_TYPES,
)
from src.modules.logistics.infrastructure.providers.errors import (
    ProviderAuthError,
    ProviderHTTPError,
    ProviderTimeoutError,
)
from src.modules.logistics.presentation.schemas_cdek_admin import (
    CdekEditOrderResponse,
    CdekJsonResponse,
    CdekRawPayloadRequest,
    CdekWebhookSubscriptionRequest,
    CdekWebhookSyncRequest,
    CdekWebhookSyncResponse,
)
from src.shared.exceptions import (
    NotFoundError,
    UnprocessableEntityError,
    ValidationError,
)

_CDEK_READ = Depends(RequirePermission(codename="logistics:read"))
_CDEK_WRITE = Depends(RequirePermission(codename="logistics:write"))

cdek_admin_router = APIRouter(
    prefix="/admin/logistics/cdek",
    tags=["Admin / Logistics / CDEK"],
    route_class=DishkaRoute,
    dependencies=[Depends(RequireStaffRole)],
)


# ---------------------------------------------------------------------------
# Provider-error translation
# ---------------------------------------------------------------------------


async def _cdek_call[T](awaitable: Awaitable[T]) -> T:
    """Await a CDEK call, translating provider failures into AppExceptions.

    The CDEK client raises bare ``Exception`` subclasses
    (``ProviderHTTPError`` / ``ProviderTimeoutError`` / ``ProviderAuthError``)
    that would otherwise surface as a generic 500. Map them onto the
    shared error hierarchy so the admin UI gets the uniform envelope:

    * CDEK 4xx — the request was rejected → ``422``.
    * CDEK 5xx / status 0 / timeout / auth failure → ``503``.
    """
    try:
        return await awaitable
    except ProviderHTTPError as exc:
        details = {
            "provider": "cdek",
            "provider_status": exc.status_code,
            "provider_body": exc.response_body,
        }
        if exc.status_code == 0 or exc.status_code >= 500:
            raise ProviderUnavailableError(
                message=f"CDEK is unavailable: {exc.message}",
                details=details,
            ) from exc
        raise UnprocessableEntityError(
            message=f"CDEK rejected the request: {exc.message}",
            details=details,
        ) from exc
    except (ProviderTimeoutError, ProviderAuthError) as exc:
        raise ProviderUnavailableError(
            message=f"CDEK is unavailable: {exc}",
            details={"provider": "cdek"},
        ) from exc


def _params(**kwargs: object) -> dict:
    """Drop ``None`` values — CDEK query endpoints reject empty params."""
    return {k: v for k, v in kwargs.items() if v is not None}


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


@cdek_admin_router.post(
    "/orders/edit",
    response_model=CdekEditOrderResponse,
    summary="Edit a CDEK order (PATCH /v2/orders)",
    dependencies=[_CDEK_WRITE],
)
async def edit_cdek_order(
    body: CdekRawPayloadRequest,
    service: FromDishka[CdekAdminService],
) -> CdekEditOrderResponse:
    """Apply a partial update to a CDEK order.

    ``payload`` is a CDEK ``OrderUpdateRequestDto`` — it must carry the
    order identifier (``uuid`` / ``cdek_number``) plus the always-required
    ``type`` and ``recipient`` blocks. CDEK only accepts edits while the
    order is still in «Создан» / «Принят».
    """
    try:
        result = await service.edit_order(body.payload)
    except ValueError as exc:
        raise ValidationError(message=str(exc)) from exc
    return CdekEditOrderResponse(
        success=result.success,
        state=result.state,
        request_uuid=result.request_uuid,
        reason=result.reason,
    )


@cdek_admin_router.get(
    "/orders/lookup",
    response_model=CdekJsonResponse,
    summary="Look up a CDEK order by CDEK / IM number",
    dependencies=[_CDEK_READ],
)
async def lookup_cdek_order(
    service: FromDishka[CdekAdminService],
    cdek_number: str | None = Query(default=None, alias="cdekNumber"),
    im_number: str | None = Query(default=None, alias="imNumber"),
) -> CdekJsonResponse:
    if cdek_number is None and im_number is None:
        raise ValidationError(
            message="Provide either 'cdekNumber' or 'imNumber'.",
        )
    raw = await _cdek_call(
        service.get_order_by_params(
            _params(cdek_number=cdek_number, im_number=im_number)
        )
    )
    return CdekJsonResponse.from_raw(raw)


@cdek_admin_router.get(
    "/orders/{orderUuid}/intakes",
    response_model=CdekJsonResponse,
    summary="List intakes registered against a CDEK order",
    dependencies=[_CDEK_READ],
)
async def list_cdek_order_intakes(
    order_uuid: Annotated[str, Path(alias="orderUuid")],
    service: FromDishka[CdekAdminService],
) -> CdekJsonResponse:
    raw = await _cdek_call(service.get_order_intakes(order_uuid))
    return CdekJsonResponse.from_raw(raw)


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


@cdek_admin_router.get(
    "/shipments/{shipmentId}/barcode",
    summary="Download the CDEK barcode label (ШК места) PDF",
    dependencies=[_CDEK_READ],
    response_class=Response,
    # ``Response`` is not a Pydantic model — explicit ``response_model=None``
    # prevents FastAPI from building a TypeAdapter from the ``-> Response``
    # return annotation, which under ``from __future__ import annotations``
    # becomes ``ForwardRef('Response')`` and crashes OpenAPI schema
    # generation with ``PydanticUserError: ... is not fully defined``.
    response_model=None,
)
async def download_cdek_barcode(
    shipment_id: Annotated[str, Path(alias="shipmentId")],
    service: FromDishka[CdekAdminService],
) -> Response:
    result = await _cdek_call(service.get_barcode_label(shipment_id))
    if not result.document_bytes:
        raise NotFoundError(
            message="CDEK barcode label is not available for this shipment.",
            details={"shipment_id": shipment_id},
        )
    return Response(
        content=result.document_bytes,
        media_type=result.content_type or "application/pdf",
    )


# ---------------------------------------------------------------------------
# Delivery agreements (договорённость о доставке)
# ---------------------------------------------------------------------------


@cdek_admin_router.post(
    "/delivery-agreements",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=CdekJsonResponse,
    summary="Register a delivery agreement (POST /v2/delivery)",
    dependencies=[_CDEK_WRITE],
)
async def register_cdek_delivery_agreement(
    body: CdekRawPayloadRequest,
    service: FromDishka[CdekAdminService],
) -> CdekJsonResponse:
    raw = await _cdek_call(service.register_delivery_agreement(body.payload))
    return CdekJsonResponse.from_raw(raw)


@cdek_admin_router.get(
    "/delivery-agreements/{agreementUuid}",
    response_model=CdekJsonResponse,
    summary="Read a delivery agreement",
    dependencies=[_CDEK_READ],
)
async def get_cdek_delivery_agreement(
    agreement_uuid: Annotated[str, Path(alias="agreementUuid")],
    service: FromDishka[CdekAdminService],
) -> CdekJsonResponse:
    raw = await _cdek_call(service.get_delivery_agreement(agreement_uuid))
    return CdekJsonResponse.from_raw(raw)


# ---------------------------------------------------------------------------
# Prealerts
# ---------------------------------------------------------------------------


@cdek_admin_router.post(
    "/prealerts",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=CdekJsonResponse,
    summary="Register a prealert (POST /v2/prealert)",
    dependencies=[_CDEK_WRITE],
)
async def create_cdek_prealert(
    body: CdekRawPayloadRequest,
    service: FromDishka[CdekAdminService],
) -> CdekJsonResponse:
    raw = await _cdek_call(service.create_prealert(body.payload))
    return CdekJsonResponse.from_raw(raw)


@cdek_admin_router.get(
    "/prealerts/{prealertUuid}",
    response_model=CdekJsonResponse,
    summary="Read a prealert",
    dependencies=[_CDEK_READ],
)
async def get_cdek_prealert(
    prealert_uuid: Annotated[str, Path(alias="prealertUuid")],
    service: FromDishka[CdekAdminService],
) -> CdekJsonResponse:
    raw = await _cdek_call(service.get_prealert(prealert_uuid))
    return CdekJsonResponse.from_raw(raw)


# ---------------------------------------------------------------------------
# Fiscal receipts / COD registries
# ---------------------------------------------------------------------------


@cdek_admin_router.get(
    "/checks",
    response_model=CdekJsonResponse,
    summary="Read fiscal receipts (GET /v2/check)",
    dependencies=[_CDEK_READ],
)
async def get_cdek_checks(
    service: FromDishka[CdekAdminService],
    order_uuid: str | None = Query(default=None, alias="orderUuid"),
    cdek_number: str | None = Query(default=None, alias="cdekNumber"),
    date: str | None = Query(default=None),
) -> CdekJsonResponse:
    if order_uuid is None and cdek_number is None and date is None:
        raise ValidationError(
            message="Provide at least one of 'orderUuid', 'cdekNumber', 'date'.",
        )
    raw = await _cdek_call(
        service.get_checks(
            _params(order_uuid=order_uuid, cdek_number=cdek_number, date=date)
        )
    )
    return CdekJsonResponse.from_raw(raw)


@cdek_admin_router.get(
    "/registries",
    response_model=CdekJsonResponse,
    summary="Read COD payment registries (GET /v2/registries)",
    dependencies=[_CDEK_READ],
)
async def get_cdek_registries(
    service: FromDishka[CdekAdminService],
    date: str = Query(description="Registry date, YYYY-MM-DD."),
) -> CdekJsonResponse:
    raw = await _cdek_call(service.get_registries(_params(date=date)))
    return CdekJsonResponse.from_raw(raw)


# ---------------------------------------------------------------------------
# International restriction hints / photo documents
# ---------------------------------------------------------------------------


@cdek_admin_router.post(
    "/restrictions",
    response_model=CdekJsonResponse,
    summary="Check international order restrictions",
    dependencies=[_CDEK_READ],
)
async def check_cdek_restrictions(
    body: CdekRawPayloadRequest,
    service: FromDishka[CdekAdminService],
) -> CdekJsonResponse:
    raw = await _cdek_call(service.check_package_restrictions(body.payload))
    return CdekJsonResponse.from_raw(raw)


@cdek_admin_router.post(
    "/photos",
    response_model=CdekJsonResponse,
    summary="List orders with ready-to-download photos",
    dependencies=[_CDEK_READ],
)
async def get_cdek_ready_photos(
    body: CdekRawPayloadRequest,
    service: FromDishka[CdekAdminService],
) -> CdekJsonResponse:
    raw = await _cdek_call(service.get_ready_photos(body.payload))
    return CdekJsonResponse.from_raw(raw)


# ---------------------------------------------------------------------------
# Intakes
# ---------------------------------------------------------------------------


@cdek_admin_router.patch(
    "/intakes/status",
    response_model=CdekJsonResponse,
    summary="Change an intake status (PATCH /v2/intakes)",
    dependencies=[_CDEK_WRITE],
)
async def change_cdek_intake_status(
    body: CdekRawPayloadRequest,
    service: FromDishka[CdekAdminService],
) -> CdekJsonResponse:
    raw = await _cdek_call(service.change_intake_status(body.payload))
    return CdekJsonResponse.from_raw(raw)


# ---------------------------------------------------------------------------
# Tariff catalogue
# ---------------------------------------------------------------------------


@cdek_admin_router.get(
    "/tariffs",
    response_model=CdekJsonResponse,
    summary="List tariffs available for the contract",
    dependencies=[_CDEK_READ],
)
async def list_cdek_tariffs(
    service: FromDishka[CdekAdminService],
) -> CdekJsonResponse:
    raw = await _cdek_call(service.list_available_tariffs())
    return CdekJsonResponse.from_raw(raw)


# ---------------------------------------------------------------------------
# Location lookups
# ---------------------------------------------------------------------------


@cdek_admin_router.get(
    "/locations/suggest",
    response_model=CdekJsonResponse,
    summary="City-name autocomplete",
    dependencies=[_CDEK_READ],
)
async def suggest_cdek_cities(
    service: FromDishka[CdekAdminService],
    name: str = Query(min_length=1, description="City name fragment."),
    country_code: str | None = Query(default=None, alias="countryCode"),
) -> CdekJsonResponse:
    raw = await _cdek_call(
        service.suggest_cities(_params(name=name, country_code=country_code))
    )
    return CdekJsonResponse.from_raw(raw)


@cdek_admin_router.get(
    "/locations/cities",
    response_model=CdekJsonResponse,
    summary="Search CDEK cities",
    dependencies=[_CDEK_READ],
)
async def list_cdek_cities(
    service: FromDishka[CdekAdminService],
    city: str | None = Query(default=None),
    country_codes: str | None = Query(default=None, alias="countryCodes"),
    postal_code: str | None = Query(default=None, alias="postalCode"),
    code: int | None = Query(default=None),
) -> CdekJsonResponse:
    raw = await _cdek_call(
        service.list_cities(
            _params(
                city=city,
                country_codes=country_codes,
                postal_code=postal_code,
                code=code,
            )
        )
    )
    return CdekJsonResponse.from_raw(raw)


@cdek_admin_router.get(
    "/locations/regions",
    response_model=CdekJsonResponse,
    summary="Search CDEK regions",
    dependencies=[_CDEK_READ],
)
async def list_cdek_regions(
    service: FromDishka[CdekAdminService],
    country_codes: str | None = Query(default=None, alias="countryCodes"),
) -> CdekJsonResponse:
    raw = await _cdek_call(service.list_regions(_params(country_codes=country_codes)))
    return CdekJsonResponse.from_raw(raw)


@cdek_admin_router.get(
    "/locations/postal-codes",
    response_model=CdekJsonResponse,
    summary="List postal codes for a CDEK city",
    dependencies=[_CDEK_READ],
)
async def list_cdek_postal_codes(
    service: FromDishka[CdekAdminService],
    city_code: int = Query(alias="cityCode", description="CDEK city code."),
) -> CdekJsonResponse:
    raw = await _cdek_call(service.get_postal_codes(_params(city_code=city_code)))
    return CdekJsonResponse.from_raw(raw)


@cdek_admin_router.get(
    "/locations/by-coordinates",
    response_model=CdekJsonResponse,
    summary="Resolve a CDEK location from coordinates",
    dependencies=[_CDEK_READ],
)
async def resolve_cdek_location_by_coordinates(
    service: FromDishka[CdekAdminService],
    latitude: float = Query(),
    longitude: float = Query(),
) -> CdekJsonResponse:
    raw = await _cdek_call(
        service.get_location_by_coordinates(
            _params(latitude=latitude, longitude=longitude)
        )
    )
    return CdekJsonResponse.from_raw(raw)


# ---------------------------------------------------------------------------
# Webhook subscriptions
# ---------------------------------------------------------------------------


@cdek_admin_router.get(
    "/webhooks",
    response_model=CdekJsonResponse,
    summary="List CDEK webhook subscriptions",
    dependencies=[_CDEK_READ],
)
async def list_cdek_webhooks(
    service: FromDishka[CdekAdminService],
) -> CdekJsonResponse:
    raw = await _cdek_call(service.list_webhook_subscriptions())
    return CdekJsonResponse.from_raw(raw)


@cdek_admin_router.post(
    "/webhooks",
    status_code=status.HTTP_201_CREATED,
    response_model=CdekJsonResponse,
    summary="Register a CDEK webhook subscription",
    dependencies=[_CDEK_WRITE],
)
async def create_cdek_webhook(
    body: CdekWebhookSubscriptionRequest,
    service: FromDishka[CdekAdminService],
) -> CdekJsonResponse:
    if body.type not in CDEK_WEBHOOK_TYPES:
        raise ValidationError(
            message=f"Unknown CDEK webhook type {body.type!r}.",
            details={"allowed": sorted(CDEK_WEBHOOK_TYPES)},
        )
    raw = await _cdek_call(service.create_webhook_subscription(body.url, body.type))
    return CdekJsonResponse.from_raw(raw)


@cdek_admin_router.post(
    "/webhooks/sync",
    response_model=CdekWebhookSyncResponse,
    summary="Idempotently sync CDEK webhook subscriptions",
    dependencies=[_CDEK_WRITE],
)
async def sync_cdek_webhooks(
    body: CdekWebhookSyncRequest,
    service: FromDishka[CdekAdminService],
) -> CdekWebhookSyncResponse:
    """Ensure ORDER_STATUS + ORDER_MODIFIED are subscribed for ``url``.

    Idempotent — lists current subscriptions, creates only the missing
    ``(type, url)`` pairs, and never exceeds CDEK's 2-subscription cap.
    Same operation the registry bootstrap runs when the CDEK account
    config carries a ``webhook_url``.
    """
    result = await _cdek_call(service.sync_webhook_subscriptions(body.url))
    return CdekWebhookSyncResponse(
        existing=result.existing,
        created=list(result.created),
        already_present=list(result.already_present),
        not_created=list(result.not_created),
    )


@cdek_admin_router.delete(
    "/webhooks/{subscriptionUuid}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a CDEK webhook subscription",
    dependencies=[_CDEK_WRITE],
)
async def delete_cdek_webhook(
    subscription_uuid: Annotated[str, Path(alias="subscriptionUuid")],
    service: FromDishka[CdekAdminService],
) -> None:
    await _cdek_call(service.delete_webhook_subscription(subscription_uuid))
