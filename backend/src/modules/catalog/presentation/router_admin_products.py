"""
FastAPI router for Product CRUD and status transition endpoints.

All mutating endpoints require the ``catalog:manage`` permission.
Delegates to application-layer command/query handlers via Dishka DI.
"""

import asyncio
import uuid
from collections.abc import AsyncIterable
from datetime import datetime

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.sse import EventSourceResponse, ServerSentEvent
from sqlalchemy.ext.asyncio import AsyncSession

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
from src.modules.catalog.domain.value_objects import Money, ProductStatus
from src.modules.catalog.infrastructure.services.sku_pricing_pubsub import (
    SkuPricingPubsub,
)
from src.modules.catalog.presentation.mappers import to_variant_response
from src.modules.catalog.presentation.schemas import (
    BulkPurchasePriceItemError,
    BulkPurchasePriceRequest,
    BulkPurchasePriceResponse,
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
)
from src.modules.catalog.presentation.update_helpers import build_update_command
from src.modules.identity.presentation.dependencies import RequirePermission

# CAT-006 — SSE comment-frame interval (seconds). Must be shorter than
# every intermediary's idle timeout: undici default ~300 s, Vercel
# Serverless 30 s, Netlify Edge 30 s. 15 s gives a comfortable margin
# without burning meaningful bandwidth (comment frame = ~12 bytes).
_SSE_KEEPALIVE_INTERVAL_S = 15.0


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
    handler: FromDishka[UpdateProductHandler],
    get_handler: FromDishka[GetProductHandler],
) -> ProductResponse:
    """Update an existing product (full or partial fields)."""
    command = build_update_command(
        request,
        UpdateProductCommand,
        exclude_from_provided=frozenset({"version"}),
        product_id=product_id,
        version=request.version,
    )
    result: UpdateProductResult = await handler.handle(command)

    # Fetch the full product for response
    read_model: ProductReadModel = await get_handler.handle(result.id)
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
    async for event in pubsub.subscribe(product_id):
        if event is not None:
            yield ServerSentEvent(data=event, event="status")
            last_keepalive = asyncio.get_running_loop().time()
            continue

        now = asyncio.get_running_loop().time()
        if now - last_keepalive >= _SSE_KEEPALIVE_INTERVAL_S:
            yield ServerSentEvent(comment="keepalive")
            last_keepalive = now


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
