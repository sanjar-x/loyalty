"""FastAPI router for the favorites bounded context.

All endpoints require an authenticated user (``Auth`` dependency from
the identity module). Anonymous access is intentionally not supported —
favorites are tied to a real Identity, so guest carts have no analogue
here.
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, status

from src.modules.favorites.application.commands.add_item import (
    AddFavoriteItemCommand,
    AddFavoriteItemHandler,
)
from src.modules.favorites.application.commands.create_list import (
    CreateFavoriteListCommand,
    CreateFavoriteListHandler,
)
from src.modules.favorites.application.commands.delete_list import (
    DeleteFavoriteListCommand,
    DeleteFavoriteListHandler,
)
from src.modules.favorites.application.commands.move_item import (
    MoveFavoriteItemCommand,
    MoveFavoriteItemHandler,
)
from src.modules.favorites.application.commands.remove_item import (
    RemoveFavoriteItemCommand,
    RemoveFavoriteItemHandler,
)
from src.modules.favorites.application.commands.rename_list import (
    RenameFavoriteListCommand,
    RenameFavoriteListHandler,
)
from src.modules.favorites.application.queries.check_favorited_batch import (
    CheckFavoritedBatchHandler,
    CheckFavoritedBatchQuery,
)
from src.modules.favorites.application.queries.get_list_items import (
    GetFavoriteListItemsHandler,
    GetFavoriteListItemsQuery,
)
from src.modules.favorites.application.queries.list_lists import (
    ListFavoriteListsHandler,
    ListFavoriteListsQuery,
)
from src.modules.favorites.domain.value_objects import FavoriteTargetType
from src.modules.favorites.presentation.schemas import (
    AddFavoriteItemRequest,
    AddFavoriteItemResponse,
    CheckFavoritedRequest,
    CheckFavoritedResponse,
    CreateFavoriteListRequest,
    CreateFavoriteListResponse,
    FavoriteBrandCardResponse,
    FavoriteItemResponse,
    FavoriteItemsPageResponse,
    FavoriteListResponse,
    FavoriteListsResponse,
    FavoriteProductCardResponse,
    MoveFavoriteItemRequest,
    RenameFavoriteListRequest,
)
from src.modules.identity.presentation.dependencies import Auth

favorite_router = APIRouter(
    prefix="/favorites",
    tags=["Favorites"],
    route_class=DishkaRoute,
)


# ---------------------------------------------------------------------------
# Lists
# ---------------------------------------------------------------------------


@favorite_router.get(
    "/lists",
    response_model=FavoriteListsResponse,
    summary="List the caller's favorite collections",
)
async def list_favorite_lists(
    auth: Auth,
    handler: FromDishka[ListFavoriteListsHandler],
) -> FavoriteListsResponse:
    summaries = await handler.handle(
        ListFavoriteListsQuery(identity_id=auth.identity_id)
    )
    return FavoriteListsResponse(
        items=[
            FavoriteListResponse(
                id=summary.list_id,
                name=summary.name,
                is_default=summary.is_default,
                sort_order=summary.sort_order,
                item_count=summary.item_count,
                created_at=summary.created_at,
                updated_at=summary.updated_at,
            )
            for summary in summaries
        ]
    )


@favorite_router.post(
    "/lists",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateFavoriteListResponse,
    summary="Create a new favorite list",
)
async def create_favorite_list(
    body: CreateFavoriteListRequest,
    auth: Auth,
    handler: FromDishka[CreateFavoriteListHandler],
) -> CreateFavoriteListResponse:
    result = await handler.handle(
        CreateFavoriteListCommand(identity_id=auth.identity_id, name=body.name)
    )
    return CreateFavoriteListResponse(id=result.list_id)


@favorite_router.patch(
    "/lists/{list_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Rename a favorite list",
)
async def rename_favorite_list(
    list_id: uuid.UUID,
    body: RenameFavoriteListRequest,
    auth: Auth,
    handler: FromDishka[RenameFavoriteListHandler],
) -> None:
    await handler.handle(
        RenameFavoriteListCommand(
            identity_id=auth.identity_id,
            list_id=list_id,
            new_name=body.name,
        )
    )


@favorite_router.delete(
    "/lists/{list_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a favorite list (cascades to items)",
)
async def delete_favorite_list(
    list_id: uuid.UUID,
    auth: Auth,
    handler: FromDishka[DeleteFavoriteListHandler],
) -> None:
    await handler.handle(
        DeleteFavoriteListCommand(identity_id=auth.identity_id, list_id=list_id)
    )


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------


@favorite_router.get(
    "/lists/{list_id}/items",
    response_model=FavoriteItemsPageResponse,
    summary="Get items in a favorite list (cursor-paginated)",
)
async def list_favorite_items(
    list_id: uuid.UUID,
    auth: Auth,
    handler: FromDishka[GetFavoriteListItemsHandler],
    target_type: FavoriteTargetType | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> FavoriteItemsPageResponse:
    page = await handler.handle(
        GetFavoriteListItemsQuery(
            identity_id=auth.identity_id,
            list_id=list_id,
            target_type=target_type,
            cursor=cursor,
            limit=limit,
        )
    )
    return FavoriteItemsPageResponse(
        items=[
            FavoriteItemResponse(
                id=item.item_id,
                list_id=item.list_id,
                target_type=FavoriteTargetType(item.target_type),
                target_id=item.target_id,
                added_at=item.added_at,
                product=(
                    FavoriteProductCardResponse(
                        id=item.product.target_id,
                        slug=item.product.slug,
                        title_i18n=item.product.title_i18n,
                        main_image_url=item.product.main_image_url,
                    )
                    if item.product is not None
                    else None
                ),
                brand=(
                    FavoriteBrandCardResponse(
                        id=item.brand.target_id,
                        slug=item.brand.slug,
                        name=item.brand.name,
                        logo_url=item.brand.logo_url,
                    )
                    if item.brand is not None
                    else None
                ),
            )
            for item in page.items
        ],
        next_cursor=page.next_cursor,
    )


@favorite_router.post(
    "/items",
    status_code=status.HTTP_201_CREATED,
    response_model=AddFavoriteItemResponse,
    summary="Add a target (product/brand) to a favorite list",
)
async def add_favorite_item(
    body: AddFavoriteItemRequest,
    auth: Auth,
    handler: FromDishka[AddFavoriteItemHandler],
) -> AddFavoriteItemResponse:
    result = await handler.handle(
        AddFavoriteItemCommand(
            identity_id=auth.identity_id,
            target_type=body.target_type,
            target_id=body.target_id,
            list_id=body.list_id,
        )
    )
    return AddFavoriteItemResponse(
        list_id=result.list_id,
        item_id=result.item_id,
        created=result.created,
    )


@favorite_router.delete(
    "/lists/{list_id}/items/{target_type}/{target_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a favorite item (idempotent)",
)
async def remove_favorite_item(
    list_id: uuid.UUID,
    target_type: FavoriteTargetType,
    target_id: uuid.UUID,
    auth: Auth,
    handler: FromDishka[RemoveFavoriteItemHandler],
) -> None:
    await handler.handle(
        RemoveFavoriteItemCommand(
            identity_id=auth.identity_id,
            list_id=list_id,
            target_type=target_type,
            target_id=target_id,
        )
    )


@favorite_router.post(
    "/items/move",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Move a favorite item between two of the caller's lists",
)
async def move_favorite_item(
    body: MoveFavoriteItemRequest,
    auth: Auth,
    handler: FromDishka[MoveFavoriteItemHandler],
) -> None:
    await handler.handle(
        MoveFavoriteItemCommand(
            identity_id=auth.identity_id,
            src_list_id=body.src_list_id,
            dst_list_id=body.dst_list_id,
            target_type=body.target_type,
            target_id=body.target_id,
        )
    )


# ---------------------------------------------------------------------------
# Batch check
# ---------------------------------------------------------------------------


@favorite_router.post(
    "/check",
    response_model=CheckFavoritedResponse,
    summary="Batch-check whether targets are favorited by the caller",
)
async def check_favorited(
    body: CheckFavoritedRequest,
    auth: Auth,
    handler: FromDishka[CheckFavoritedBatchHandler],
) -> CheckFavoritedResponse:
    mapping = await handler.handle(
        CheckFavoritedBatchQuery(
            identity_id=auth.identity_id,
            target_type=body.target_type,
            target_ids=body.target_ids,
        )
    )
    return CheckFavoritedResponse(favorited={str(k): v for k, v in mapping.items()})
