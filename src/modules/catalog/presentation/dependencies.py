# src/modules/catalog/presentation/dependencies.py
from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource

from src.modules.catalog.application.commands.confirm_brand_logo import (
    ConfirmBrandLogoUploadHandler,
)
from src.modules.catalog.application.commands.create_brand import CreateBrandHandler
from src.modules.catalog.application.commands.create_category import (
    CreateCategoryHandler,
)
from src.modules.catalog.application.commands.delete_brand import DeleteBrandHandler
from src.modules.catalog.application.commands.delete_category import (
    DeleteCategoryHandler,
)
from src.modules.catalog.application.commands.update_brand import UpdateBrandHandler
from src.modules.catalog.application.commands.update_category import (
    UpdateCategoryHandler,
)
from src.modules.catalog.application.queries.get_brand import GetBrandHandler
from src.modules.catalog.application.queries.get_category import GetCategoryHandler
from src.modules.catalog.application.queries.get_category_tree import (
    GetCategoryTreeHandler,
)
from src.modules.catalog.application.queries.list_brands import ListBrandsHandler
from src.modules.catalog.application.queries.list_categories import (
    ListCategoriesHandler,
)
from src.modules.catalog.application.services.media_processor import BrandLogoProcessor
from src.modules.catalog.domain.interfaces import IBrandRepository, ICategoryRepository
from src.modules.catalog.infrastructure.repositories import (
    BrandRepository,
    CategoryRepository,
)


class CategoryProvider(Provider):
    category_repo: CompositeDependencySource = provide(
        CategoryRepository, scope=Scope.REQUEST, provides=ICategoryRepository
    )
    create_category_handler: CompositeDependencySource = provide(
        CreateCategoryHandler, scope=Scope.REQUEST
    )
    get_category_tree_handler: CompositeDependencySource = provide(
        GetCategoryTreeHandler, scope=Scope.REQUEST
    )
    get_category_handler: CompositeDependencySource = provide(
        GetCategoryHandler, scope=Scope.REQUEST
    )
    list_categories_handler: CompositeDependencySource = provide(
        ListCategoriesHandler, scope=Scope.REQUEST
    )
    update_category_handler: CompositeDependencySource = provide(
        UpdateCategoryHandler, scope=Scope.REQUEST
    )
    delete_category_handler: CompositeDependencySource = provide(
        DeleteCategoryHandler, scope=Scope.REQUEST
    )


class BrandProvider(Provider):
    brand_repo: CompositeDependencySource = provide(
        BrandRepository, scope=Scope.REQUEST, provides=IBrandRepository
    )
    create_brand_handler: CompositeDependencySource = provide(
        CreateBrandHandler, scope=Scope.REQUEST
    )
    confirm_brand_logo_handler: CompositeDependencySource = provide(
        ConfirmBrandLogoUploadHandler, scope=Scope.REQUEST
    )
    get_brand_handler: CompositeDependencySource = provide(GetBrandHandler, scope=Scope.REQUEST)
    list_brands_handler: CompositeDependencySource = provide(ListBrandsHandler, scope=Scope.REQUEST)
    update_brand_handler: CompositeDependencySource = provide(
        UpdateBrandHandler, scope=Scope.REQUEST
    )
    delete_brand_handler: CompositeDependencySource = provide(
        DeleteBrandHandler, scope=Scope.REQUEST
    )
    brand_logo_processor: CompositeDependencySource = provide(
        BrandLogoProcessor, scope=Scope.REQUEST
    )
