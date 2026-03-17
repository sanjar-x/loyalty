# src/modules/catalog/presentation/router.py
import uuid
from typing import Any

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, status

from src.modules.catalog.application.commands.confirm_brand_logo import (
    ConfirmBrandLogoUploadCommand,
    ConfirmBrandLogoUploadHandler,
)
from src.modules.catalog.application.commands.create_brand import (
    CreateBrandCommand,
    CreateBrandHandler,
    LogoMetadata,
)
from src.modules.catalog.application.commands.create_category import (
    CreateCategoryCommand,
    CreateCategoryHandler,
)
from src.modules.catalog.application.commands.delete_brand import (
    DeleteBrandCommand,
    DeleteBrandHandler,
)
from src.modules.catalog.application.commands.update_brand import (
    UpdateBrandCommand,
    UpdateBrandHandler,
)
from src.modules.catalog.application.queries.get_brand import GetBrandHandler
from src.modules.catalog.application.queries.get_category_tree import (
    GetCategoryTreeHandler,
)
from src.modules.catalog.application.queries.list_brands import (
    ListBrandsHandler,
    ListBrandsQuery,
)
from src.modules.catalog.presentation.schemas import (
    BrandCreateRequest,
    BrandCreateResponse,
    BrandListResponse,
    BrandResponse,
    BrandUpdateRequest,
    CategoryCreateRequest,
    CategoryCreateResponse,
    CategoryTreeResponse,
    ConfirmLogoRequest,
)

category_router = APIRouter(
    prefix="/categories",
    tags=["Categories"],
    route_class=DishkaRoute,
)


@category_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CategoryCreateResponse,
    summary="Создать новую категорию",
    description="Создает категорию.",
)
async def create_category(
    request: CategoryCreateRequest,
    handler: FromDishka[CreateCategoryHandler],
) -> CategoryCreateResponse:
    command = CreateCategoryCommand(
        name=request.name,
        slug=request.slug,
        parent_id=request.parent_id,
        sort_order=request.sort_order,
    )
    category = await handler.handle(command)
    return CategoryCreateResponse(id=category.id, message="Категория успешно создана")


@category_router.get(
    "/tree",
    status_code=status.HTTP_200_OK,
    response_model=list[CategoryTreeResponse],
    summary="Получить дерево категорий",
    description="Возвращает полный каталог в виде вложенного дерева",
)
async def get_category_tree(
    handler: FromDishka[GetCategoryTreeHandler],
) -> Any:
    roots = await handler.handle()
    return roots


brand_router = APIRouter(
    prefix="/brands",
    tags=["Brands"],
    route_class=DishkaRoute,
)


@brand_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=BrandCreateResponse,
    summary="Создать новый бренд",
)
async def create_brand(
    request: BrandCreateRequest,
    handler: FromDishka[CreateBrandHandler],
) -> BrandCreateResponse:
    logo_meta = None
    if request.logo:
        logo_meta = LogoMetadata(
            filename=request.logo.filename,
            content_type=request.logo.content_type,
            size=request.logo.size,
        )

    command = CreateBrandCommand(
        name=request.name,
        slug=request.slug,
        logo=logo_meta,
    )
    result = await handler.handle(command)
    return BrandCreateResponse(
        brand_id=result.brand_id,
        presigned_upload_url=result.presigned_upload_url,
        object_key=result.object_key,
    )


@brand_router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=BrandListResponse,
    summary="Получить список брендов",
)
async def list_brands(
    handler: FromDishka[ListBrandsHandler],
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> BrandListResponse:
    query = ListBrandsQuery(offset=offset, limit=limit)
    result = await handler.handle(query)
    return BrandListResponse(
        items=[
            BrandResponse(
                id=item.id,
                name=item.name,
                slug=item.slug,
                logo_url=item.logo_url,
                logo_status=item.logo_status,
            )
            for item in result.items
        ],
        total=result.total,
        offset=result.offset,
        limit=result.limit,
    )


@brand_router.get(
    "/{brand_id}",
    status_code=status.HTTP_200_OK,
    response_model=BrandResponse,
    summary="Получить бренд по ID",
)
async def get_brand(
    brand_id: uuid.UUID,
    handler: FromDishka[GetBrandHandler],
) -> BrandResponse:
    result = await handler.handle(brand_id)
    return BrandResponse(
        id=result.id,
        name=result.name,
        slug=result.slug,
        logo_url=result.logo_url,
        logo_status=result.logo_status,
    )


@brand_router.patch(
    "/{brand_id}",
    status_code=status.HTTP_200_OK,
    response_model=BrandResponse,
    summary="Обновить бренд",
)
async def update_brand(
    brand_id: uuid.UUID,
    request: BrandUpdateRequest,
    handler: FromDishka[UpdateBrandHandler],
) -> BrandResponse:
    command = UpdateBrandCommand(
        brand_id=brand_id,
        name=request.name,
        slug=request.slug,
    )
    result = await handler.handle(command)
    return BrandResponse(
        id=result.id,
        name=result.name,
        slug=result.slug,
        logo_url=result.logo_url,
        logo_status=result.logo_status,
    )


@brand_router.delete(
    "/{brand_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить бренд",
)
async def delete_brand(
    brand_id: uuid.UUID,
    handler: FromDishka[DeleteBrandHandler],
) -> None:
    command = DeleteBrandCommand(brand_id=brand_id)
    await handler.handle(command)


@brand_router.post(
    "/{brand_id}/logo/confirm",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Подтвердить загрузку логотипа",
)
async def confirm_logo_upload(
    brand_id: uuid.UUID,
    request: ConfirmLogoRequest,
    handler: FromDishka[ConfirmBrandLogoUploadHandler],
) -> dict:
    command = ConfirmBrandLogoUploadCommand(brand_id=brand_id)
    await handler.handle(command)
    return {"message": "Запрос на обработку логотипа принят"}
