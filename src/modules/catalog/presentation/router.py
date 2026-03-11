# src\modules\catalog\presentation\router.py
from typing import Any

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, status

from src.modules.catalog.application.commands.create_category import (
    CreateCategoryCommand,
    CreateCategoryHandler,
)
from src.modules.catalog.application.queries.get_category_tree import (
    GetCategoryTreeHandler,
)
from src.modules.catalog.presentation.schemas import (
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
