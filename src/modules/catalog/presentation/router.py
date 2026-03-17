# src/modules/catalog/presentation/router.py
import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, status

from src.modules.catalog.application.commands.confirm_brand_logo import (
    ConfirmBrandLogoUploadCommand,
    ConfirmBrandLogoUploadHandler,
)
from src.modules.catalog.application.commands.create_brand import (
    CreateBrandCommand,
    CreateBrandHandler,
    CreateBrandResult,
    LogoMetadata,
)
from src.modules.catalog.application.commands.create_category import (
    CreateCategoryCommand,
    CreateCategoryHandler,
    CreateCategoryResult,
)
from src.modules.catalog.application.commands.delete_brand import (
    DeleteBrandCommand,
    DeleteBrandHandler,
)
from src.modules.catalog.application.commands.delete_category import (
    DeleteCategoryCommand,
    DeleteCategoryHandler,
)
from src.modules.catalog.application.commands.update_brand import (
    UpdateBrandCommand,
    UpdateBrandHandler,
    UpdateBrandResult,
)
from src.modules.catalog.application.commands.update_category import (
    UpdateCategoryCommand,
    UpdateCategoryHandler,
    UpdateCategoryResult,
)
from src.modules.catalog.application.queries.get_brand import GetBrandHandler
from src.modules.catalog.application.queries.get_category import GetCategoryHandler
from src.modules.catalog.application.queries.get_category_tree import (
    GetCategoryTreeHandler,
)
from src.modules.catalog.application.queries.list_brands import (
    ListBrandsHandler,
    ListBrandsQuery,
)
from src.modules.catalog.application.queries.list_categories import (
    ListCategoriesHandler,
    ListCategoriesQuery,
)
from src.modules.catalog.application.queries.read_models import (
    BrandListReadModel,
    BrandReadModel,
    CategoryListReadModel,
    CategoryNode,
    CategoryReadModel,
)
from src.modules.catalog.presentation.schemas import (
    BrandCreateRequest,
    BrandCreateResponse,
    BrandListResponse,
    BrandResponse,
    BrandUpdateRequest,
    CategoryCreateRequest,
    CategoryCreateResponse,
    CategoryListResponse,
    CategoryResponse,
    CategoryTreeResponse,
    CategoryUpdateRequest,
)
from src.modules.identity.presentation.dependencies import RequirePermission

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
    dependencies=[Depends(dependency=RequirePermission(codename="catalog:manage"))],
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
    category: CreateCategoryResult = await handler.handle(command)
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
) -> list[CategoryTreeResponse]:
    roots: list[CategoryNode] = await handler.handle()
    return [CategoryTreeResponse.model_validate(r, from_attributes=True) for r in roots]


@category_router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=CategoryListResponse,
    summary="Получить список категорий",
)
async def list_categories(
    handler: FromDishka[ListCategoriesHandler],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> CategoryListResponse:
    query = ListCategoriesQuery(offset=offset, limit=limit)
    result: CategoryListReadModel = await handler.handle(query)
    return CategoryListResponse(
        items=[
            CategoryResponse(
                id=item.id,
                name=item.name,
                slug=item.slug,
                full_slug=item.full_slug,
                level=item.level,
                sort_order=item.sort_order,
                parent_id=item.parent_id,
            )
            for item in result.items
        ],
        total=result.total,
        offset=result.offset,
        limit=result.limit,
    )


@category_router.get(
    path="/{category_id}",
    status_code=status.HTTP_200_OK,
    response_model=CategoryResponse,
    summary="Получить категорию по ID",
)
async def get_category(
    category_id: uuid.UUID,
    handler: FromDishka[GetCategoryHandler],
) -> CategoryResponse:
    result: CategoryReadModel = await handler.handle(category_id)
    return CategoryResponse(
        id=result.id,
        name=result.name,
        slug=result.slug,
        full_slug=result.full_slug,
        level=result.level,
        sort_order=result.sort_order,
        parent_id=result.parent_id,
    )


@category_router.patch(
    "/{category_id}",
    status_code=status.HTTP_200_OK,
    response_model=CategoryResponse,
    summary="Обновить категорию",
    dependencies=[Depends(dependency=RequirePermission(codename="catalog:manage"))],
)
async def update_category(
    category_id: uuid.UUID,
    request: CategoryUpdateRequest,
    handler: FromDishka[UpdateCategoryHandler],
) -> CategoryResponse:
    command = UpdateCategoryCommand(
        category_id=category_id,
        name=request.name,
        slug=request.slug,
        sort_order=request.sort_order,
    )
    result: UpdateCategoryResult = await handler.handle(command)
    return CategoryResponse(
        id=result.id,
        name=result.name,
        slug=result.slug,
        full_slug=result.full_slug,
        level=result.level,
        sort_order=result.sort_order,
        parent_id=result.parent_id,
    )


@category_router.delete(
    path="/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить категорию",
    dependencies=[Depends(dependency=RequirePermission(codename="catalog:manage"))],
)
async def delete_category(
    category_id: uuid.UUID,
    handler: FromDishka[DeleteCategoryHandler],
) -> None:
    command = DeleteCategoryCommand(category_id=category_id)
    await handler.handle(command)


brand_router = APIRouter(
    prefix="/brands",
    tags=["Brands"],
    route_class=DishkaRoute,
)


@brand_router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=BrandCreateResponse,
    summary="Создать новый бренд",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
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
    result: CreateBrandResult = await handler.handle(command)
    return BrandCreateResponse(
        brand_id=result.brand_id,
        presigned_upload_url=result.presigned_upload_url,
        object_key=result.object_key,
    )


@brand_router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=BrandListResponse,
    summary="Получить список брендов",
)
async def list_brands(
    handler: FromDishka[ListBrandsHandler],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> BrandListResponse:
    query = ListBrandsQuery(offset=offset, limit=limit)
    result: BrandListReadModel = await handler.handle(query)
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
    path="/{brand_id}",
    status_code=status.HTTP_200_OK,
    response_model=BrandResponse,
    summary="Получить бренд по ID",
)
async def get_brand(
    brand_id: uuid.UUID,
    handler: FromDishka[GetBrandHandler],
) -> BrandResponse:
    result: BrandReadModel = await handler.handle(brand_id)
    return BrandResponse(
        id=result.id,
        name=result.name,
        slug=result.slug,
        logo_url=result.logo_url,
        logo_status=result.logo_status,
    )


@brand_router.patch(
    path="/{brand_id}",
    status_code=status.HTTP_200_OK,
    response_model=BrandResponse,
    summary="Обновить бренд",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
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
    result: UpdateBrandResult = await handler.handle(command)
    return BrandResponse(
        id=result.id,
        name=result.name,
        slug=result.slug,
        logo_url=result.logo_url,
        logo_status=result.logo_status,
    )


@brand_router.delete(
    path="/{brand_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить бренд",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def delete_brand(
    brand_id: uuid.UUID,
    handler: FromDishka[DeleteBrandHandler],
) -> None:
    command = DeleteBrandCommand(brand_id=brand_id)
    await handler.handle(command)


@brand_router.post(
    path="/{brand_id}/logo/confirm",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Подтвердить загрузку логотипа",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def confirm_logo_upload(
    brand_id: uuid.UUID,
    handler: FromDishka[ConfirmBrandLogoUploadHandler],
) -> dict:
    command = ConfirmBrandLogoUploadCommand(brand_id=brand_id)
    await handler.handle(command)
    return {"message": "Запрос на обработку логотипа принят"}
