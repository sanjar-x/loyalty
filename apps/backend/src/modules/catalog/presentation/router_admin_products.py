"""
FastAPI router for Product CRUD and status transition endpoints.

All mutating endpoints require the ``catalog:manage`` permission.
Delegates to application-layer command/query handlers via Dishka DI.
"""

import asyncio
import uuid
from collections.abc import AsyncIterable
from datetime import datetime

import structlog
from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.sse import EventSourceResponse, ServerSentEvent
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.etag import attach_etag, parse_if_match
from src.modules.catalog.application.commands.bulk_set_purchase_price import (
    BulkSetPurchasePriceCommand,
    BulkSetPurchasePriceHandler,
    BulkSetPurchasePriceItem,
)
from src.modules.catalog.application.commands.change_product_status import (
    ChangeProductStatusCommand,
    ChangeProductStatusHandler,
)
from src.modules.catalog.application.commands.create_product import (
    CreateProductCommand,
    CreateProductHandler,
    CreateProductResult,
)
from src.modules.catalog.application.commands.delete_product import (
    DeleteProductCommand,
    DeleteProductHandler,
)
from src.modules.catalog.application.commands.update_product import (
    UpdateProductCommand,
    UpdateProductHandler,
    UpdateProductResult,
)
from src.modules.catalog.application.queries.get_product import GetProductHandler
from src.modules.catalog.application.queries.get_product_completeness import (
    GetProductCompletenessHandler,
    ProductCompletenessQuery,
)
from src.modules.catalog.application.queries.list_products import (
    ListProductsHandler,
    ListProductsQuery,
)
from src.modules.catalog.application.queries.read_models import (
    ProductReadModel,
)
from src.modules.catalog.application.queries.validate_product_publish import (
    ValidateProductPublishHandler,
    ValidateProductPublishQuery,
)
from src.modules.catalog.application.queries.validate_product_update import (
    ValidateProductUpdateHandler,
    ValidateProductUpdateQuery,
)
from src.modules.catalog.domain.exceptions import ConcurrencyError
from src.modules.catalog.domain.value_objects import Money, ProductStatus
from src.modules.catalog.infrastructure.services.sku_pricing_pubsub import (
    SkuPricingPubsub,
)
from src.modules.catalog.presentation.mappers import to_variant_response
from src.modules.catalog.presentation.schemas import (
    BulkPurchasePriceItemError,
    BulkPurchasePriceRequest,
    BulkPurchasePriceResponse,
    FieldDiffSchema,
    MissingAttributeItem,
    ProductAttributeResponse,
    ProductCompletenessResponse,
    ProductCreateRequest,
    ProductCreateResponse,
    ProductListItemResponse,
    ProductListResponse,
    ProductResponse,
    ProductStatusChangeRequest,
    ProductUpdateRequest,
    SkuPublishDiagnosticSchema,
    ValidatePublishGateFailureSchema,
    ValidatePublishResponse,
    ValidateUpdateResponse,
    ValidationErrorSchema,
    ValidationWarningSchema,
)
from src.modules.catalog.presentation.update_helpers import build_update_command
from src.modules.identity.presentation.dependencies import RequirePermission
from src.shared.exceptions import PreconditionFailedError

# CAT-006 — SSE comment-frame interval (seconds). Must be shorter than
# every intermediary's idle timeout: undici default ~300 s, Vercel
# Serverless 30 s, Netlify Edge 30 s. 15 s gives a comfortable margin
# without burning meaningful bandwidth (comment frame = ~12 bytes).
_SSE_KEEPALIVE_INTERVAL_S = 15.0

logger = structlog.get_logger(__name__)


product_router = APIRouter(
    prefix="/admin/catalog/products",
    tags=["Admin / Catalog / Products"],
    route_class=DishkaRoute,
)


@product_router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=ProductCreateResponse,
    summary="Create a new product",
    description="Create a new product in DRAFT status with required fields.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def create_product(
    request: ProductCreateRequest,
    handler: FromDishka[CreateProductHandler],
) -> ProductCreateResponse:
    """Create a new product in DRAFT status."""
    command = CreateProductCommand(
        title_i18n=request.title_i18n,
        slug=request.slug,
        brand_id=request.brand_id,
        primary_category_id=request.primary_category_id,
        description_i18n=request.description_i18n,
        supplier_id=request.supplier_id,
        source_url=request.source_url,
        country_of_origin=request.country_of_origin,
        tags=request.tags,
    )
    result: CreateProductResult = await handler.handle(command)
    return ProductCreateResponse(
        id=result.product_id,
        default_variant_id=result.default_variant_id,
        message="Product created",
    )


@product_router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=ProductListResponse,
    summary="List products (paginated, filterable)",
    description="Retrieve a paginated list of products with optional filters.",
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def list_products(
    response: Response,
    handler: FromDishka[ListProductsHandler],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    product_status: str | None = Query(default=None, alias="status"),
    brand_id: uuid.UUID | None = None,
    sort_by: str | None = Query(
        default=None,
        pattern="^(newest|oldest|popularity|name_asc|name_desc)$",
        description="Sort order: newest, oldest, popularity, name_asc, name_desc",
    ),
    published_after: datetime | None = Query(
        default=None,
        description="Only include products published on or after this timestamp",
    ),
) -> ProductListResponse:
    """Retrieve a paginated list of products with optional filters."""
    response.headers["Cache-Control"] = "no-store"
    query = ListProductsQuery(
        offset=offset,
        limit=limit,
        status=product_status,
        brand_id=brand_id,
        sort_by=sort_by,
        published_after=published_after,
    )
    result = await handler.handle(query)
    return ProductListResponse(
        items=[
            ProductListItemResponse(
                id=item.id,
                slug=item.slug,
                title_i18n=item.title_i18n,
                status=item.status,
                brand_id=item.brand_id,
                primary_category_id=item.primary_category_id,
                version=item.version,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in result.items
        ],
        total=result.total,
        offset=result.offset,
        limit=result.limit,
    )


@product_router.get(
    path="/{product_id}/completeness",
    status_code=status.HTTP_200_OK,
    response_model=ProductCompletenessResponse,
    summary="Check product attribute completeness",
    description="Check product attribute completeness against template requirements.",
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def get_product_completeness(
    product_id: uuid.UUID,
    response: Response,
    handler: FromDishka[GetProductCompletenessHandler],
) -> ProductCompletenessResponse:
    """Check product attribute completeness against template requirements."""
    response.headers["Cache-Control"] = "no-store"
    query = ProductCompletenessQuery(product_id=product_id)
    result = await handler.handle(query)
    return ProductCompletenessResponse(
        is_complete=result.is_complete,
        total_required=result.total_required,
        filled_required=result.filled_required,
        total_recommended=result.total_recommended,
        filled_recommended=result.filled_recommended,
        missing_required=[
            MissingAttributeItem(
                attribute_id=m["attribute_id"],
                code=m["code"],
                name_i18n=m["name_i18n"],
            )
            for m in result.missing_required
        ],
        missing_recommended=[
            MissingAttributeItem(
                attribute_id=m["attribute_id"],
                code=m["code"],
                name_i18n=m["name_i18n"],
            )
            for m in result.missing_recommended
        ],
    )


@product_router.get(
    path="/{product_id}",
    status_code=status.HTTP_200_OK,
    response_model=ProductResponse,
    summary="Get product detail by ID",
    description="Retrieve a single product with nested SKUs and attributes.",
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def get_product(
    product_id: uuid.UUID,
    response: Response,
    handler: FromDishka[GetProductHandler],
) -> ProductResponse:
    """Retrieve a single product with nested SKUs and attributes."""
    response.headers["Cache-Control"] = "no-store"
    read_model: ProductReadModel = await handler.handle(product_id)
    # C4.1 — strong ETag based on the aggregate's optimistic-lock
    # version. Frontend echoes this back as ``If-Match`` on the next
    # PATCH/DELETE so concurrent edits land a 412 instead of silently
    # clobbering each other.
    attach_etag(response, read_model.version)
    return _to_product_response(read_model)


@product_router.patch(
    path="/{product_id}",
    status_code=status.HTTP_200_OK,
    response_model=ProductResponse,
    summary="Update a product",
    description="Partially update product fields. Only provided fields are modified.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def update_product(
    product_id: uuid.UUID,
    request: ProductUpdateRequest,
    response: Response,
    handler: FromDishka[UpdateProductHandler],
    get_handler: FromDishka[GetProductHandler],
    if_match_version: int | None = Depends(parse_if_match),
) -> ProductResponse:
    """Update an existing product (full or partial fields).

    C4.1 — accepts ``If-Match: "v{N}"`` header. When present, the
    expected version takes precedence over any ``version`` field in
    the request body. Mismatch → 412 ``PRECONDITION_FAILED``.
    Header absent → fall back to legacy ``request.version`` optimistic
    locking (kept for backward compat through M+1).
    """
    expected_version = (
        if_match_version if if_match_version is not None else request.version
    )
    command = build_update_command(
        request,
        UpdateProductCommand,
        exclude_from_provided=frozenset({"version"}),
        product_id=product_id,
        version=expected_version,
    )
    try:
        result: UpdateProductResult = await handler.handle(command)
    except ConcurrencyError as exc:
        # If-Match was used → upgrade 409 to 412 with the expected /
        # current version in the envelope. Without If-Match we keep
        # the legacy 409 surface so frontend interceptors that haven't
        # been upgraded yet don't break.
        if if_match_version is not None:
            raise PreconditionFailedError(
                entity_type="Product",
                entity_id=product_id,
                expected_version=if_match_version,
                current_version=exc.details.get("actual_version"),
            ) from exc
        raise

    # Fetch the full product for response
    read_model: ProductReadModel = await get_handler.handle(result.id)
    attach_etag(response, read_model.version)
    return _to_product_response(read_model)


@product_router.delete(
    path="/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a product",
    description="Mark a product as deleted without removing it from the database.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def delete_product(
    product_id: uuid.UUID,
    handler: FromDishka[DeleteProductHandler],
) -> None:
    """Soft-delete a product by marking it as deleted."""
    command = DeleteProductCommand(product_id=product_id)
    await handler.handle(command)


@product_router.get(
    path="/{product_id}/skus/pricing-events",
    response_class=EventSourceResponse,
    # Stream endpoints return ``AsyncIterable[ServerSentEvent]``; Pydantic
    # cannot resolve that forward reference into a JSON Schema, which crashes
    # ``GET /openapi.json``. ``response_model=None`` tells FastAPI to skip
    # response-schema introspection on this route (CAT-007).
    response_model=None,
    summary="SSE stream of SKU pricing recompute events for one product",
    description=(
        "Server-Sent Events stream pushing live recompute outcomes for every "
        "SKU of the given product. Replaces admin polling. Each event payload "
        "carries ``skuId`` / ``pricingStatus`` / ``sellingPrice`` / ``pricedAt`` "
        "/ ``pricedFailureReason``. Backed by Redis pub/sub on channel "
        "``catalog:sku-pricing:{product_id}`` — the outbox-driven consumer "
        "publishes here when ``SKUPricedEvent`` / ``SKUPricingFailedEvent`` "
        "are dispatched (CAT-005)."
    ),
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def stream_sku_pricing_events(
    product_id: uuid.UUID,
    pubsub: FromDishka[SkuPricingPubsub],
    session: FromDishka[AsyncSession],
) -> AsyncIterable[ServerSentEvent]:
    """Stream pricing recompute events as they land for ``product_id``.

    A ``:keepalive`` SSE comment is emitted every
    :data:`_SSE_KEEPALIVE_INTERVAL_S` seconds of channel-idle so that
    intermediaries (BFF ``fetch`` in Next.js / Vercel / Netlify edge,
    proxies, load balancers) don't drop the long-lived connection on
    ``bodyTimeout`` (~5 min in undici / 30 s on some hosts). Comment
    frames are ignored by ``EventSource`` clients per the SSE spec.
    """
    # The pub/sub loop holds an idle Postgres session for up to 10 minutes
    # (see ``SkuPricingPubsub.subscribe`` timeout). Postgres'
    # idle_in_transaction_session_timeout would kill the connection mid-
    # stream, so release it before entering the long poll. Same pattern as
    # the image module's status SSE.
    await session.close()

    last_keepalive = asyncio.get_running_loop().time()
    try:
        async for event in pubsub.subscribe(product_id):
            if event is not None:
                yield ServerSentEvent(data=event, event="status")
                last_keepalive = asyncio.get_running_loop().time()
                continue

            now = asyncio.get_running_loop().time()
            if now - last_keepalive >= _SSE_KEEPALIVE_INTERVAL_S:
                yield ServerSentEvent(comment="keepalive")
                last_keepalive = now
    except RedisError, OSError:
        # Pub/sub backbone went down mid-stream — emit an explicit
        # ``error`` SSE frame so the client knows it should reconnect
        # rather than silently rendering a stale "OK" state. Browser
        # ``EventSource`` auto-reconnects on close, the explicit frame
        # gives the admin UI a hook to surface a transient banner.
        logger.exception(
            "sse_pricing_stream_pubsub_unavailable",
            product_id=str(product_id),
        )
        yield ServerSentEvent(
            data={"reason": "pubsub_unavailable"},
            event="error",
        )


@product_router.post(
    path="/{product_id}/skus/bulk-purchase-price",
    status_code=status.HTTP_200_OK,
    response_model=BulkPurchasePriceResponse,
    summary="Bulk-set purchase_price across many SKUs of one product",
    description=(
        "Apply ``purchasePrice`` updates to many SKUs in a single transaction. "
        "Each item is validated independently (currency, ownership); per-SKU "
        "failures are returned in the ``errors`` list without aborting the batch."
    ),
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def bulk_set_purchase_price(
    product_id: uuid.UUID,
    request: BulkPurchasePriceRequest,
    handler: FromDishka[BulkSetPurchasePriceHandler],
) -> BulkPurchasePriceResponse:
    """Bulk update SKU purchase prices for one product."""
    command = BulkSetPurchasePriceCommand(
        product_id=product_id,
        items=[
            BulkSetPurchasePriceItem(
                sku_id=item.sku_id,
                purchase_price=Money(
                    amount=item.purchase_price.amount,
                    currency=item.purchase_price.currency,
                ),
            )
            for item in request.items
        ],
    )
    result = await handler.handle(command)
    return BulkPurchasePriceResponse(
        updated_count=result.updated_count,
        unchanged_count=result.unchanged_count,
        errors=[
            BulkPurchasePriceItemError(
                sku_id=err.sku_id,
                error_code=err.error_code,
                message=err.message,
            )
            for err in result.errors
        ],
    )


@product_router.patch(
    path="/{product_id}/status",
    status_code=status.HTTP_200_OK,
    response_model=ProductResponse,
    summary="Change product status",
    description="Transition a product to a new lifecycle status.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def change_product_status(
    product_id: uuid.UUID,
    request: ProductStatusChangeRequest,
    handler: FromDishka[ChangeProductStatusHandler],
    get_handler: FromDishka[GetProductHandler],
) -> ProductResponse:
    """Transition a product to a new lifecycle status."""
    new_status = ProductStatus(request.status)
    command = ChangeProductStatusCommand(
        product_id=product_id,
        new_status=new_status,
    )
    await handler.handle(command)

    # Fetch updated product for response
    read_model: ProductReadModel = await get_handler.handle(product_id)
    return _to_product_response(read_model)


# ---------------------------------------------------------------------------
# C1.1 — Publish-gate preview (read-only, no side effects)
# ---------------------------------------------------------------------------


@product_router.post(
    path="/{product_id}/_validate-update",
    status_code=status.HTTP_200_OK,
    response_model=ValidateUpdateResponse,
    summary="Preview a product PATCH without committing",
    description=(
        "Read-only validator. Accepts the same body shape as "
        "``PATCH /admin/catalog/products/{id}`` and returns a verdict "
        "containing the field-level diff, advisory warnings, and any "
        "validation errors that the real PATCH would raise. "
        "``ok=true`` means the next PATCH will succeed; ``warnings`` "
        "are advisory and do not close the gate (e.g. supplier change "
        "triggers a per-SKU recompute fan-out — the operator should "
        "know but it's still allowed)."
    ),
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def validate_product_update(
    product_id: uuid.UUID,
    body: ProductUpdateRequest,
    handler: FromDishka[ValidateProductUpdateHandler],
) -> ValidateUpdateResponse:
    """Compute the validate-update verdict for a single product."""
    # Mirror the router-level "_provided_fields" detection used by the
    # real PATCH endpoint: only fields present in the parsed body are
    # validated. ``model_fields_set`` exposes that exact set on Pydantic.
    provided = frozenset(body.model_fields_set)
    query = ValidateProductUpdateQuery(
        product_id=product_id,
        title_i18n=body.title_i18n,
        description_i18n=body.description_i18n,
        slug=body.slug,
        brand_id=body.brand_id,
        primary_category_id=body.primary_category_id,
        supplier_id=body.supplier_id,
        country_of_origin=body.country_of_origin,
        tags=body.tags,
        _provided_fields=provided,
    )
    result = await handler.handle(query)
    return ValidateUpdateResponse(
        ok=result.ok,
        diff=[
            FieldDiffSchema(field=d.field, from_value=d.from_value, to_value=d.to_value)
            for d in result.diff
        ],
        warnings=[
            ValidationWarningSchema(code=w.code, message=w.message, details=w.details)
            for w in result.warnings
        ],
        validation_errors=[
            ValidationErrorSchema(code=e.code, message=e.message, field=e.field)
            for e in result.validation_errors
        ],
    )


@product_router.post(
    path="/{product_id}/_validate-publish",
    status_code=status.HTTP_200_OK,
    response_model=ValidatePublishResponse,
    summary="Preview the PUBLISHED transition without committing",
    description=(
        "Read-only validator that mirrors the gate enforced by "
        "``Product.transition_status(PUBLISHED)``. Returns the same "
        "per-SKU diagnostics + structured failure codes the front-end "
        "uses to render its publish-gate panel — without mutating the "
        "aggregate or emitting events. ``ok=true`` means the next "
        "PATCH ``/status`` to ``published`` will succeed; ``ok=false`` "
        "with a non-empty ``gateFailures`` list means the operator has "
        "fixes to make first. The endpoint never returns an HTTP 4xx "
        "for a 'cannot publish yet' verdict — that's a valid preview."
    ),
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def validate_product_publish(
    product_id: uuid.UUID,
    handler: FromDishka[ValidateProductPublishHandler],
) -> ValidatePublishResponse:
    """Compute the publish-gate verdict for a single product."""
    result = await handler.handle(ValidateProductPublishQuery(product_id=product_id))
    return ValidatePublishResponse(
        ok=result.ok,
        current_status=result.current_status,
        next_status=result.next_status,
        sku_diagnostics=[
            SkuPublishDiagnosticSchema(**d) for d in result.sku_diagnostics
        ],
        gate_failures=[
            ValidatePublishGateFailureSchema(code=f.code, message=f.message)  # ty: ignore[invalid-argument-type]
            for f in result.gate_failures
        ],
    )


def _to_product_response(model: ProductReadModel) -> ProductResponse:
    """Convert a full product read model to a product response schema."""
    return ProductResponse(
        id=model.id,
        slug=model.slug,
        title_i18n=model.title_i18n,
        description_i18n=model.description_i18n,
        status=model.status,
        brand_id=model.brand_id,
        primary_category_id=model.primary_category_id,
        supplier_id=model.supplier_id,
        source_url=model.source_url,
        country_of_origin=model.country_of_origin,
        tags=model.tags,
        version=model.version,
        created_at=model.created_at,
        updated_at=model.updated_at,
        published_at=model.published_at,
        min_price=model.min_price,
        max_price=model.max_price,
        price_currency=model.price_currency,
        variants=[to_variant_response(v) for v in model.variants],
        attributes=[
            ProductAttributeResponse(
                id=a.id,
                product_id=a.product_id,
                attribute_id=a.attribute_id,
                attribute_value_id=a.attribute_value_id,
                attribute_code=a.attribute_code,
                attribute_name_i18n=a.attribute_name_i18n,
                attribute_value_code=getattr(a, "attribute_value_code", ""),
                attribute_value_name_i18n=getattr(a, "attribute_value_name_i18n", {}),
            )
            for a in model.attributes
        ],
    )
