"""
FastAPI router for Product CRUD and status transition endpoints.

All mutating endpoints require the ``catalog:manage`` permission.
Delegates to application-layer command/query handlers via Dishka DI.
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, status

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
    _SENTINEL,
    UpdateProductCommand,
    UpdateProductHandler,
    UpdateProductResult,
)
from src.modules.catalog.application.queries.get_product import GetProductHandler
from src.modules.catalog.application.queries.list_products import (
    ListProductsHandler,
    ListProductsQuery,
)
from src.modules.catalog.application.queries.read_models import (
    ProductReadModel,
    SKUReadModel,
)
from src.modules.catalog.domain.value_objects import ProductStatus
from src.modules.catalog.presentation.schemas import (
    MoneySchema,
    ProductAttributeResponse,
    ProductCreateRequest,
    ProductCreateResponse,
    ProductListItemResponse,
    ProductListResponse,
    ProductResponse,
    ProductStatusChangeRequest,
    ProductUpdateRequest,
    SKUResponse,
    VariantAttributePairSchema,
)
from src.modules.identity.presentation.dependencies import RequirePermission

product_router = APIRouter(
    prefix="/products",
    tags=["Products"],
    route_class=DishkaRoute,
)


@product_router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=ProductCreateResponse,
    summary="Create a new product",
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
        country_of_origin=request.country_of_origin,
        tags=request.tags,
    )
    result: CreateProductResult = await handler.handle(command)
    return ProductCreateResponse(id=result.product_id, message="Product created")


@product_router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=ProductListResponse,
    summary="List products (paginated, filterable)",
)
async def list_products(
    handler: FromDishka[ListProductsHandler],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    product_status: str | None = Query(default=None, alias="status"),
    brand_id: uuid.UUID | None = Query(default=None),
) -> ProductListResponse:
    """Retrieve a paginated list of products with optional filters."""
    query = ListProductsQuery(
        offset=offset,
        limit=limit,
        status=product_status,
        brand_id=brand_id,
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
    path="/{product_id}",
    status_code=status.HTTP_200_OK,
    response_model=ProductResponse,
    summary="Get product detail by ID",
)
async def get_product(
    product_id: uuid.UUID,
    handler: FromDishka[GetProductHandler],
) -> ProductResponse:
    """Retrieve a single product with nested SKUs and attributes."""
    read_model: ProductReadModel = await handler.handle(product_id)
    return _to_product_response(read_model)


@product_router.put(
    path="/{product_id}",
    status_code=status.HTTP_200_OK,
    response_model=ProductResponse,
    summary="Update a product",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def update_product(
    product_id: uuid.UUID,
    request: ProductUpdateRequest,
    handler: FromDishka[UpdateProductHandler],
    get_handler: FromDishka[GetProductHandler],
) -> ProductResponse:
    """Update an existing product (full or partial fields)."""
    update_kwargs: dict[str, object] = {"product_id": product_id}

    if request.title_i18n is not None:
        update_kwargs["title_i18n"] = request.title_i18n
    if request.slug is not None:
        update_kwargs["slug"] = request.slug
    if request.description_i18n is not None:
        update_kwargs["description_i18n"] = request.description_i18n
    if request.brand_id is not None:
        update_kwargs["brand_id"] = request.brand_id
    if request.primary_category_id is not None:
        update_kwargs["primary_category_id"] = request.primary_category_id
    if request.tags is not None:
        update_kwargs["tags"] = request.tags
    if request.version is not None:
        update_kwargs["version"] = request.version

    # Sentinel fields: Pydantic uses ... (Ellipsis) as "not provided".
    # Map Pydantic Ellipsis -> command _SENTINEL, explicit None -> None.
    if request.supplier_id is not ...:
        update_kwargs["supplier_id"] = request.supplier_id
    else:
        update_kwargs["supplier_id"] = _SENTINEL

    if request.country_of_origin is not ...:
        update_kwargs["country_of_origin"] = request.country_of_origin
    else:
        update_kwargs["country_of_origin"] = _SENTINEL

    command = UpdateProductCommand(**update_kwargs)  # type: ignore[arg-type]
    result: UpdateProductResult = await handler.handle(command)

    # Fetch the full product for response
    read_model: ProductReadModel = await get_handler.handle(result.id)
    return _to_product_response(read_model)


@product_router.delete(
    path="/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a product",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def delete_product(
    product_id: uuid.UUID,
    handler: FromDishka[DeleteProductHandler],
) -> None:
    """Soft-delete a product by marking it as deleted."""
    command = DeleteProductCommand(product_id=product_id)
    await handler.handle(command)


@product_router.patch(
    path="/{product_id}/status",
    status_code=status.HTTP_200_OK,
    response_model=ProductResponse,
    summary="Change product status",
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


def _to_sku_response(sku: SKUReadModel) -> SKUResponse:
    """Convert a SKU read model to a SKU response schema."""
    compare_at: MoneySchema | None = None
    if sku.compare_at_price is not None:
        compare_at = MoneySchema(
            amount=sku.compare_at_price.amount,
            currency=sku.compare_at_price.currency,
        )
    return SKUResponse(
        id=sku.id,
        product_id=sku.product_id,
        sku_code=sku.sku_code,
        variant_hash=sku.variant_hash,
        price=MoneySchema(amount=sku.price.amount, currency=sku.price.currency),
        compare_at_price=compare_at,
        is_active=sku.is_active,
        version=sku.version,
        deleted_at=sku.deleted_at,
        created_at=sku.created_at,
        updated_at=sku.updated_at,
        variant_attributes=[
            VariantAttributePairSchema(
                attribute_id=va.attribute_id,
                attribute_value_id=va.attribute_value_id,
            )
            for va in sku.variant_attributes
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
        country_of_origin=model.country_of_origin,
        tags=model.tags,
        version=model.version,
        deleted_at=model.deleted_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
        published_at=model.published_at,
        min_price=model.min_price,
        max_price=model.max_price,
        skus=[_to_sku_response(s) for s in model.skus],
        attributes=[
            ProductAttributeResponse(
                id=a.id,
                product_id=a.product_id,
                attribute_id=a.attribute_id,
                attribute_value_id=a.attribute_value_id,
            )
            for a in model.attributes
        ],
    )
