"""Dishka IoC provider for the Favorites bounded context."""

from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource

from src.modules.favorites.application.commands.add_item import (
    AddFavoriteItemHandler,
)
from src.modules.favorites.application.commands.create_list import (
    CreateFavoriteListHandler,
)
from src.modules.favorites.application.commands.delete_list import (
    DeleteFavoriteListHandler,
)
from src.modules.favorites.application.commands.move_item import (
    MoveFavoriteItemHandler,
)
from src.modules.favorites.application.commands.remove_item import (
    RemoveFavoriteItemHandler,
)
from src.modules.favorites.application.commands.rename_list import (
    RenameFavoriteListHandler,
)
from src.modules.favorites.application.queries.check_favorited_batch import (
    CheckFavoritedBatchHandler,
)
from src.modules.favorites.application.queries.get_list_items import (
    GetFavoriteListItemsHandler,
)
from src.modules.favorites.application.queries.list_lists import (
    ListFavoriteListsHandler,
)
from src.modules.favorites.domain.interfaces import (
    IFavoriteItemRepository,
    IFavoriteListRepository,
    IFavoriteTargetValidator,
)
from src.modules.favorites.infrastructure.adapters.catalog_target_validator import (
    CatalogTargetValidator,
)
from src.modules.favorites.infrastructure.repositories.favorite_item_repository import (
    FavoriteItemRepository,
)
from src.modules.favorites.infrastructure.repositories.favorite_list_repository import (
    FavoriteListRepository,
)


class FavoritesProvider(Provider):
    """Wires repositories, ACL validator and command/query handlers."""

    # --- Repositories ---
    list_repo: CompositeDependencySource = provide(
        FavoriteListRepository,
        scope=Scope.REQUEST,
        provides=IFavoriteListRepository,
    )
    item_repo: CompositeDependencySource = provide(
        FavoriteItemRepository,
        scope=Scope.REQUEST,
        provides=IFavoriteItemRepository,
    )

    # --- ACL adapters ---
    target_validator: CompositeDependencySource = provide(
        CatalogTargetValidator,
        scope=Scope.REQUEST,
        provides=IFavoriteTargetValidator,
    )

    # --- Command handlers ---
    create_list_handler: CompositeDependencySource = provide(
        CreateFavoriteListHandler, scope=Scope.REQUEST
    )
    rename_list_handler: CompositeDependencySource = provide(
        RenameFavoriteListHandler, scope=Scope.REQUEST
    )
    delete_list_handler: CompositeDependencySource = provide(
        DeleteFavoriteListHandler, scope=Scope.REQUEST
    )
    add_item_handler: CompositeDependencySource = provide(
        AddFavoriteItemHandler, scope=Scope.REQUEST
    )
    remove_item_handler: CompositeDependencySource = provide(
        RemoveFavoriteItemHandler, scope=Scope.REQUEST
    )
    move_item_handler: CompositeDependencySource = provide(
        MoveFavoriteItemHandler, scope=Scope.REQUEST
    )

    # --- Query handlers ---
    list_lists_handler: CompositeDependencySource = provide(
        ListFavoriteListsHandler, scope=Scope.REQUEST
    )
    get_list_items_handler: CompositeDependencySource = provide(
        GetFavoriteListItemsHandler, scope=Scope.REQUEST
    )
    check_favorited_batch_handler: CompositeDependencySource = provide(
        CheckFavoritedBatchHandler, scope=Scope.REQUEST
    )
