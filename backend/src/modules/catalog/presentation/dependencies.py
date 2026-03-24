"""
Dishka IoC providers for the Catalog bounded context.

Registers repository implementations, command/query handlers, and
application services into the request-scoped DI container.  These
providers are consumed by the FastAPI router layer via ``FromDishka``.
"""

from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource

from src.modules.catalog.application.commands.add_attribute_value import (
    AddAttributeValueHandler,
)
from src.modules.catalog.application.commands.add_external_product_media import (
    AddExternalProductMediaHandler,
)
from src.modules.catalog.application.commands.add_product_media import (
    AddProductMediaHandler,
)
from src.modules.catalog.application.commands.add_sku import AddSKUHandler
from src.modules.catalog.application.commands.add_variant import AddVariantHandler
from src.modules.catalog.application.commands.assign_product_attribute import (
    AssignProductAttributeHandler,
)
from src.modules.catalog.application.commands.change_product_status import (
    ChangeProductStatusHandler,
)
from src.modules.catalog.application.commands.complete_product_media import (
    CompleteProductMediaHandler,
    FailProductMediaHandler,
)
from src.modules.catalog.application.commands.confirm_brand_logo import (
    ConfirmBrandLogoUploadHandler,
)
from src.modules.catalog.application.commands.confirm_product_media import (
    ConfirmProductMediaUploadHandler,
)
from src.modules.catalog.application.commands.create_attribute import (
    CreateAttributeHandler,
)
from src.modules.catalog.application.commands.create_attribute_group import (
    CreateAttributeGroupHandler,
)
from src.modules.catalog.application.commands.create_brand import CreateBrandHandler
from src.modules.catalog.application.commands.create_category import (
    CreateCategoryHandler,
)
from src.modules.catalog.application.commands.create_product import CreateProductHandler
from src.modules.catalog.application.commands.delete_attribute import (
    DeleteAttributeHandler,
)
from src.modules.catalog.application.commands.delete_attribute_group import (
    DeleteAttributeGroupHandler,
)
from src.modules.catalog.application.commands.delete_attribute_value import (
    DeleteAttributeValueHandler,
)
from src.modules.catalog.application.commands.delete_brand import DeleteBrandHandler
from src.modules.catalog.application.commands.delete_category import (
    DeleteCategoryHandler,
)
from src.modules.catalog.application.commands.delete_product import DeleteProductHandler
from src.modules.catalog.application.commands.delete_product_attribute import (
    DeleteProductAttributeHandler,
)
from src.modules.catalog.application.commands.delete_product_media import (
    DeleteProductMediaHandler,
)
from src.modules.catalog.application.commands.delete_sku import DeleteSKUHandler
from src.modules.catalog.application.commands.delete_variant import DeleteVariantHandler
from src.modules.catalog.application.commands.reorder_attribute_values import (
    ReorderAttributeValuesHandler,
)
from src.modules.catalog.application.commands.update_attribute import (
    UpdateAttributeHandler,
)
from src.modules.catalog.application.commands.update_attribute_group import (
    UpdateAttributeGroupHandler,
)
from src.modules.catalog.application.commands.update_attribute_value import (
    UpdateAttributeValueHandler,
)
from src.modules.catalog.application.commands.update_brand import UpdateBrandHandler
from src.modules.catalog.application.commands.update_category import (
    UpdateCategoryHandler,
)
from src.modules.catalog.application.commands.update_product import UpdateProductHandler
from src.modules.catalog.application.commands.update_sku import UpdateSKUHandler
from src.modules.catalog.application.commands.update_variant import UpdateVariantHandler
from src.modules.catalog.application.queries.get_attribute import GetAttributeHandler
from src.modules.catalog.application.queries.get_attribute_group import (
    GetAttributeGroupHandler,
)
from src.modules.catalog.application.queries.get_brand import GetBrandHandler
from src.modules.catalog.application.queries.get_category import GetCategoryHandler
from src.modules.catalog.application.queries.get_category_tree import (
    GetCategoryTreeHandler,
)
from src.modules.catalog.application.queries.get_product import GetProductHandler
from src.modules.catalog.application.queries.list_attribute_groups import (
    ListAttributeGroupsHandler,
)
from src.modules.catalog.application.queries.list_attribute_values import (
    ListAttributeValuesHandler,
)
from src.modules.catalog.application.queries.list_attributes import (
    ListAttributesHandler,
)
from src.modules.catalog.application.queries.list_brands import ListBrandsHandler
from src.modules.catalog.application.queries.list_categories import (
    ListCategoriesHandler,
)
from src.modules.catalog.application.queries.list_product_attributes import (
    ListProductAttributesHandler,
)
from src.modules.catalog.application.queries.list_product_media import (
    ListProductMediaHandler,
)
from src.modules.catalog.application.queries.list_products import ListProductsHandler
from src.modules.catalog.application.queries.list_skus import ListSKUsHandler
from src.modules.catalog.application.queries.list_variants import ListVariantsHandler
from src.modules.catalog.application.queries.storefront import (
    StorefrontCardAttributesHandler,
    StorefrontComparisonAttributesHandler,
    StorefrontFilterableAttributesHandler,
    StorefrontFormAttributesHandler,
)
from src.modules.catalog.application.services.media_processor import BrandLogoProcessor
from src.modules.catalog.domain.interfaces import (
    IAttributeGroupRepository,
    IAttributeRepository,
    IAttributeValueRepository,
    IBrandRepository,
    ICategoryRepository,
    IMediaAssetRepository,
    IProductAttributeValueRepository,
    IProductRepository,
)
from src.modules.catalog.infrastructure.repositories import (
    AttributeGroupRepository,
    AttributeRepository,
    AttributeValueRepository,
    BrandRepository,
    CategoryRepository,
    MediaAssetRepository,
    ProductAttributeValueRepository,
    ProductRepository,
)


class CategoryProvider(Provider):
    """DI provider for category-related repositories and handlers."""

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
    """DI provider for brand-related repositories, handlers, and services."""

    brand_repo: CompositeDependencySource = provide(
        BrandRepository, scope=Scope.REQUEST, provides=IBrandRepository
    )
    create_brand_handler: CompositeDependencySource = provide(
        CreateBrandHandler, scope=Scope.REQUEST
    )
    confirm_brand_logo_handler: CompositeDependencySource = provide(
        ConfirmBrandLogoUploadHandler, scope=Scope.REQUEST
    )
    get_brand_handler: CompositeDependencySource = provide(
        GetBrandHandler, scope=Scope.REQUEST
    )
    list_brands_handler: CompositeDependencySource = provide(
        ListBrandsHandler, scope=Scope.REQUEST
    )
    update_brand_handler: CompositeDependencySource = provide(
        UpdateBrandHandler, scope=Scope.REQUEST
    )
    delete_brand_handler: CompositeDependencySource = provide(
        DeleteBrandHandler, scope=Scope.REQUEST
    )
    brand_logo_processor: CompositeDependencySource = provide(
        BrandLogoProcessor, scope=Scope.REQUEST
    )


class AttributeGroupProvider(Provider):
    """DI provider for attribute group repositories and handlers."""

    attribute_group_repo: CompositeDependencySource = provide(
        AttributeGroupRepository,
        scope=Scope.REQUEST,
        provides=IAttributeGroupRepository,
    )
    create_attribute_group_handler: CompositeDependencySource = provide(
        CreateAttributeGroupHandler, scope=Scope.REQUEST
    )
    update_attribute_group_handler: CompositeDependencySource = provide(
        UpdateAttributeGroupHandler, scope=Scope.REQUEST
    )
    delete_attribute_group_handler: CompositeDependencySource = provide(
        DeleteAttributeGroupHandler, scope=Scope.REQUEST
    )
    get_attribute_group_handler: CompositeDependencySource = provide(
        GetAttributeGroupHandler, scope=Scope.REQUEST
    )
    list_attribute_groups_handler: CompositeDependencySource = provide(
        ListAttributeGroupsHandler, scope=Scope.REQUEST
    )


class AttributeProvider(Provider):
    """DI provider for attribute repositories and handlers."""

    attribute_repo: CompositeDependencySource = provide(
        AttributeRepository,
        scope=Scope.REQUEST,
        provides=IAttributeRepository,
    )
    create_attribute_handler: CompositeDependencySource = provide(
        CreateAttributeHandler, scope=Scope.REQUEST
    )
    update_attribute_handler: CompositeDependencySource = provide(
        UpdateAttributeHandler, scope=Scope.REQUEST
    )
    delete_attribute_handler: CompositeDependencySource = provide(
        DeleteAttributeHandler, scope=Scope.REQUEST
    )
    get_attribute_handler: CompositeDependencySource = provide(
        GetAttributeHandler, scope=Scope.REQUEST
    )
    list_attributes_handler: CompositeDependencySource = provide(
        ListAttributesHandler, scope=Scope.REQUEST
    )


class AttributeValueProvider(Provider):
    """DI provider for attribute value repositories and handlers."""

    attribute_value_repo: CompositeDependencySource = provide(
        AttributeValueRepository,
        scope=Scope.REQUEST,
        provides=IAttributeValueRepository,
    )
    add_attribute_value_handler: CompositeDependencySource = provide(
        AddAttributeValueHandler, scope=Scope.REQUEST
    )
    update_attribute_value_handler: CompositeDependencySource = provide(
        UpdateAttributeValueHandler, scope=Scope.REQUEST
    )
    delete_attribute_value_handler: CompositeDependencySource = provide(
        DeleteAttributeValueHandler, scope=Scope.REQUEST
    )
    reorder_attribute_values_handler: CompositeDependencySource = provide(
        ReorderAttributeValuesHandler, scope=Scope.REQUEST
    )
    list_attribute_values_handler: CompositeDependencySource = provide(
        ListAttributeValuesHandler, scope=Scope.REQUEST
    )


class StorefrontCatalogProvider(Provider):
    """DI provider for storefront query handlers."""

    filterable_handler: CompositeDependencySource = provide(
        StorefrontFilterableAttributesHandler, scope=Scope.REQUEST
    )
    card_handler: CompositeDependencySource = provide(
        StorefrontCardAttributesHandler, scope=Scope.REQUEST
    )
    comparison_handler: CompositeDependencySource = provide(
        StorefrontComparisonAttributesHandler, scope=Scope.REQUEST
    )
    form_handler: CompositeDependencySource = provide(
        StorefrontFormAttributesHandler, scope=Scope.REQUEST
    )


class ProductProvider(Provider):
    """DI provider for product-related repositories, command handlers, and query handlers."""

    product_repo: CompositeDependencySource = provide(
        ProductRepository, scope=Scope.REQUEST, provides=IProductRepository
    )
    product_attribute_value_repo: CompositeDependencySource = provide(
        ProductAttributeValueRepository,
        scope=Scope.REQUEST,
        provides=IProductAttributeValueRepository,
    )

    # Command handlers
    create_product_handler: CompositeDependencySource = provide(
        CreateProductHandler, scope=Scope.REQUEST
    )
    update_product_handler: CompositeDependencySource = provide(
        UpdateProductHandler, scope=Scope.REQUEST
    )
    delete_product_handler: CompositeDependencySource = provide(
        DeleteProductHandler, scope=Scope.REQUEST
    )
    change_product_status_handler: CompositeDependencySource = provide(
        ChangeProductStatusHandler, scope=Scope.REQUEST
    )
    add_variant_handler: CompositeDependencySource = provide(
        AddVariantHandler, scope=Scope.REQUEST
    )
    update_variant_handler: CompositeDependencySource = provide(
        UpdateVariantHandler, scope=Scope.REQUEST
    )
    delete_variant_handler: CompositeDependencySource = provide(
        DeleteVariantHandler, scope=Scope.REQUEST
    )
    add_sku_handler: CompositeDependencySource = provide(
        AddSKUHandler, scope=Scope.REQUEST
    )
    update_sku_handler: CompositeDependencySource = provide(
        UpdateSKUHandler, scope=Scope.REQUEST
    )
    delete_sku_handler: CompositeDependencySource = provide(
        DeleteSKUHandler, scope=Scope.REQUEST
    )
    assign_product_attribute_handler: CompositeDependencySource = provide(
        AssignProductAttributeHandler, scope=Scope.REQUEST
    )
    delete_product_attribute_handler: CompositeDependencySource = provide(
        DeleteProductAttributeHandler, scope=Scope.REQUEST
    )

    # Query handlers
    get_product_handler: CompositeDependencySource = provide(
        GetProductHandler, scope=Scope.REQUEST
    )
    list_products_handler: CompositeDependencySource = provide(
        ListProductsHandler, scope=Scope.REQUEST
    )
    list_skus_handler: CompositeDependencySource = provide(
        ListSKUsHandler, scope=Scope.REQUEST
    )
    list_variants_handler: CompositeDependencySource = provide(
        ListVariantsHandler, scope=Scope.REQUEST
    )
    list_product_attributes_handler: CompositeDependencySource = provide(
        ListProductAttributesHandler, scope=Scope.REQUEST
    )


class MediaAssetProvider(Provider):
    """DI provider for product media asset repositories and handlers."""

    media_asset_repo: CompositeDependencySource = provide(
        MediaAssetRepository, scope=Scope.REQUEST, provides=IMediaAssetRepository
    )

    # Command handlers
    add_product_media_handler: CompositeDependencySource = provide(
        AddProductMediaHandler, scope=Scope.REQUEST
    )
    confirm_product_media_handler: CompositeDependencySource = provide(
        ConfirmProductMediaUploadHandler, scope=Scope.REQUEST
    )
    complete_product_media_handler: CompositeDependencySource = provide(
        CompleteProductMediaHandler, scope=Scope.REQUEST
    )
    fail_product_media_handler: CompositeDependencySource = provide(
        FailProductMediaHandler, scope=Scope.REQUEST
    )
    delete_product_media_handler: CompositeDependencySource = provide(
        DeleteProductMediaHandler, scope=Scope.REQUEST
    )
    add_external_product_media_handler: CompositeDependencySource = provide(
        AddExternalProductMediaHandler, scope=Scope.REQUEST
    )

    # Query handlers
    list_product_media_handler: CompositeDependencySource = provide(
        ListProductMediaHandler, scope=Scope.REQUEST
    )
