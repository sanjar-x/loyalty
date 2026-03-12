# src\modules\catalog\presentation\router.py
import uuid
from typing import Any

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, status

from src.modules.catalog.application.commands.confirm_brand_logo import (
    ConfirmBrandLogoUploadCommand,
    ConfirmBrandLogoUploadHandler,
)
from src.modules.catalog.application.commands.create_brand import (
    CreateBrandCommand,
    CreateBrandHandler,
)
from src.modules.catalog.application.commands.create_category import (
    CreateCategoryCommand,
    CreateCategoryHandler,
)
from src.modules.catalog.application.queries.get_category_tree import (
    GetCategoryTreeHandler,
)
from src.modules.catalog.presentation.schemas import (
    BrandCreateRequest,
    BrandCreateResponse,
    CategoryCreateRequest,
    CategoryCreateResponse,
    CategoryTreeResponse,
)

category_router = APIRouter(prefix="/categories", tags=["Categories"])


@category_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CategoryCreateResponse,
    summary="Создать новую категорию",
    description="Создает категорию.",
)
@inject
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
@inject
async def get_category_tree(
    handler: FromDishka[GetCategoryTreeHandler],
) -> Any:
    roots = await handler.handle()
    return roots


brand_router = APIRouter(prefix="/brands", tags=["Brands"])


@brand_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=BrandCreateResponse,
    summary="Создать новый бренд",
)
@inject
async def create_brand(
    request: BrandCreateRequest,
    handler: FromDishka[CreateBrandHandler],
) -> BrandCreateResponse:
    command = CreateBrandCommand(
        name=request.name,
        slug=request.slug,
        logo_filename=request.logo_filename,
        logo_content_type=request.logo_content_type,
    )
    result = await handler.handle(command)
    return BrandCreateResponse(
        brand_id=result.brand_id,
        presigned_upload_url=result.presigned_upload_url,
        object_key=result.object_key,
    )


@brand_router.post(
    "/{brand_id}/logo/confirm",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Подтвердить загрузку логотипа",
)
@inject
async def confirm_logo_upload(
    brand_id: uuid.UUID,
    handler: FromDishka[ConfirmBrandLogoUploadHandler],
) -> dict:
    command = ConfirmBrandLogoUploadCommand(brand_id=brand_id)
    await handler.handle(command)
    return {"message": "Запрос на обработку логотипа принят"}
