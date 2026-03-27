"""
Dishka IoC providers for the Catalog bounded context.

Registers repository implementations, command/query handlers, and
application services into the request-scoped DI container.  These
providers are consumed by the FastAPI router layer via ``FromDishka``.
"""

from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource

from src.bootstrap.config import Settings
from src.modules.catalog.application.commands.add_attribute_value import (
    AddAttributeValueHandler,
)
from src.modules.catalog.application.commands.add_sku import AddSKUHandler
from src.modules.catalog.application.commands.add_variant import AddVariantHandler
from src.modules.catalog.application.commands.assign_product_attribute import (
    AssignProductAttributeHandler,
)
from src.modules.catalog.application.commands.bind_attribute_to_template import (
    BindAttributeToTemplateHandler,
)
from src.modules.catalog.application.commands.bulk_add_attribute_values import (
    BulkAddAttributeValuesHandler,
)
from src.modules.catalog.application.commands.bulk_assign_product_attributes import (
    BulkAssignProductAttributesHandler,
)
from src.modules.catalog.application.commands.bulk_create_attributes import (
    BulkCreateAttributesHandler,
)
from src.modules.catalog.application.commands.bulk_create_brands import (
    BulkCreateBrandsHandler,
)
from src.modules.catalog.application.commands.bulk_create_categories import (
    BulkCreateCategoriesHandler,
)
from src.modules.catalog.application.commands.change_product_status import (
    ChangeProductStatusHandler,
)
from src.modules.catalog.application.commands.clone_attribute_template import (
    CloneAttributeTemplateHandler,
)
from src.modules.catalog.application.commands.create_attribute import (
    CreateAttributeHandler,
)
from src.modules.catalog.application.commands.create_attribute_template import (
    CreateAttributeTemplateHandler,
)
from src.modules.catalog.application.commands.create_brand import CreateBrandHandler
from src.modules.catalog.application.commands.create_category import (
    CreateCategoryHandler,
)
from src.modules.catalog.application.commands.create_product import CreateProductHandler
from src.modules.catalog.application.commands.delete_attribute import (
    DeleteAttributeHandler,
)
from src.modules.catalog.application.commands.delete_attribute_template import (
    DeleteAttributeTemplateHandler,
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
from src.modules.catalog.application.commands.generate_sku_matrix import (
    GenerateSKUMatrixHandler,
)
from src.modules.catalog.application.commands.reorder_attribute_values import (
    ReorderAttributeValuesHandler,
)
from src.modules.catalog.application.commands.reorder_template_bindings import (
    ReorderTemplateBindingsHandler,
)
from src.modules.catalog.application.commands.set_attribute_value_active import (
    SetAttributeValueActiveHandler,
)
from src.modules.catalog.application.commands.unbind_attribute_from_template import (
    UnbindAttributeFromTemplateHandler,
)
from src.modules.catalog.application.commands.update_attribute import (
    UpdateAttributeHandler,
)
from src.modules.catalog.application.commands.update_attribute_template import (
    UpdateAttributeTemplateHandler,
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
from src.modules.catalog.application.commands.update_template_attribute_binding import (
    UpdateTemplateAttributeBindingHandler,
)
from src.modules.catalog.application.commands.update_variant import UpdateVariantHandler
from src.modules.catalog.application.queries.get_attribute import GetAttributeHandler
from src.modules.catalog.application.queries.get_attribute_usage import (
    GetAttributeUsageHandler,
)
from src.modules.catalog.application.queries.get_attribute_value import (
    GetAttributeValueHandler,
)
from src.modules.catalog.application.queries.get_brand import GetBrandHandler
from src.modules.catalog.application.queries.get_category import GetCategoryHandler
from src.modules.catalog.application.queries.get_category_tree import (
    GetCategoryTreeHandler,
)
from src.modules.catalog.application.queries.get_product import GetProductHandler
from src.modules.catalog.application.queries.get_product_completeness import (
    GetProductCompletenessHandler,
)
from src.modules.catalog.application.queries.list_attribute_templates import (
    GetAttributeTemplateHandler,
    ListAttributeTemplatesHandler,
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
from src.modules.catalog.application.queries.list_template_bindings import (
    ListTemplateBindingsHandler,
)
from src.modules.catalog.application.queries.list_variants import ListVariantsHandler
from src.modules.catalog.application.queries.resolve_template_attributes import (
    ResolveTemplateAttributesHandler,
)
from src.modules.catalog.application.queries.storefront import (
    StorefrontCardAttributesHandler,
    StorefrontComparisonAttributesHandler,
    StorefrontFilterableAttributesHandler,
    StorefrontFormAttributesHandler,
)
from src.modules.catalog.domain.interfaces import (
    IAttributeGroupRepository,
    IAttributeRepository,
    IAttributeTemplateRepository,
    IAttributeValueRepository,
    IBrandRepository,
    ICategoryRepository,
    IImageBackendClient,
    IMediaAssetRepository,
    IProductAttributeValueRepository,
    IProductRepository,
    ITemplateAttributeBindingRepository,
)
from src.modules.catalog.infrastructure.image_backend_client import ImageBackendClient
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
from src.modules.catalog.infrastructure.repositories.attribute_template import (
    AttributeTemplateRepository,
)
from src.modules.catalog.infrastructure.repositories.template_attribute_binding import (
    TemplateAttributeBindingRepository,
)


class CategoryProvider(Provider):
    """DI provider for category-related repositories and handlers."""

    category_repo: CompositeDependencySource = provide(
        CategoryRepository, scope=Scope.REQUEST, provides=ICategoryRepository
    )
    create_category_handler: CompositeDependencySource = provide(
        CreateCategoryHandler, scope=Scope.REQUEST
    )
    bulk_create_categories_handler: CompositeDependencySource = provide(
        BulkCreateCategoriesHandler, scope=Scope.REQUEST
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
    bulk_create_brands_handler: CompositeDependencySource = provide(
        BulkCreateBrandsHandler, scope=Scope.REQUEST
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


class AttributeGroupProvider(Provider):
    """DI provider for attribute group repository.

    Handlers were removed — groups are seed-only reference data.
    The repository is still needed by delete_attribute (orphan→general).
    """

    attribute_group_repo: CompositeDependencySource = provide(
        AttributeGroupRepository,
        scope=Scope.REQUEST,
        provides=IAttributeGroupRepository,
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
    bulk_create_attributes_handler: CompositeDependencySource = provide(
        BulkCreateAttributesHandler, scope=Scope.REQUEST
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
    get_attribute_usage_handler: CompositeDependencySource = provide(
        GetAttributeUsageHandler, scope=Scope.REQUEST
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
    bulk_add_attribute_values_handler: CompositeDependencySource = provide(
        BulkAddAttributeValuesHandler, scope=Scope.REQUEST
    )
    update_attribute_value_handler: CompositeDependencySource = provide(
        UpdateAttributeValueHandler, scope=Scope.REQUEST
    )
    delete_attribute_value_handler: CompositeDependencySource = provide(
        DeleteAttributeValueHandler, scope=Scope.REQUEST
    )
    set_attribute_value_active_handler: CompositeDependencySource = provide(
        SetAttributeValueActiveHandler, scope=Scope.REQUEST
    )
    reorder_attribute_values_handler: CompositeDependencySource = provide(
        ReorderAttributeValuesHandler, scope=Scope.REQUEST
    )
    list_attribute_values_handler: CompositeDependencySource = provide(
        ListAttributeValuesHandler, scope=Scope.REQUEST
    )
    get_attribute_value_handler: CompositeDependencySource = provide(
        GetAttributeValueHandler, scope=Scope.REQUEST
    )


class AttributeTemplateProvider(Provider):
    """DI provider for attribute template repositories, command handlers, and query handlers."""

    # Repositories
    template_repo: CompositeDependencySource = provide(
        AttributeTemplateRepository,
        scope=Scope.REQUEST,
        provides=IAttributeTemplateRepository,
    )
    binding_repo: CompositeDependencySource = provide(
        TemplateAttributeBindingRepository,
        scope=Scope.REQUEST,
        provides=ITemplateAttributeBindingRepository,
    )
    # Command handlers
    clone_attribute_template_handler: CompositeDependencySource = provide(
        CloneAttributeTemplateHandler, scope=Scope.REQUEST
    )
    create_attribute_template_handler: CompositeDependencySource = provide(
        CreateAttributeTemplateHandler, scope=Scope.REQUEST
    )
    update_attribute_template_handler: CompositeDependencySource = provide(
        UpdateAttributeTemplateHandler, scope=Scope.REQUEST
    )
    delete_attribute_template_handler: CompositeDependencySource = provide(
        DeleteAttributeTemplateHandler, scope=Scope.REQUEST
    )
    bind_attribute_to_template_handler: CompositeDependencySource = provide(
        BindAttributeToTemplateHandler, scope=Scope.REQUEST
    )
    unbind_attribute_from_template_handler: CompositeDependencySource = provide(
        UnbindAttributeFromTemplateHandler, scope=Scope.REQUEST
    )
    update_template_attribute_binding_handler: CompositeDependencySource = provide(
        UpdateTemplateAttributeBindingHandler, scope=Scope.REQUEST
    )
    reorder_template_bindings_handler: CompositeDependencySource = provide(
        ReorderTemplateBindingsHandler, scope=Scope.REQUEST
    )
    # Query handlers
    resolve_template_attributes_handler: CompositeDependencySource = provide(
        ResolveTemplateAttributesHandler, scope=Scope.REQUEST
    )
    list_attribute_templates_handler: CompositeDependencySource = provide(
        ListAttributeTemplatesHandler, scope=Scope.REQUEST
    )
    get_attribute_template_handler: CompositeDependencySource = provide(
        GetAttributeTemplateHandler, scope=Scope.REQUEST
    )
    list_template_bindings_handler: CompositeDependencySource = provide(
        ListTemplateBindingsHandler, scope=Scope.REQUEST
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
    generate_sku_matrix_handler: CompositeDependencySource = provide(
        GenerateSKUMatrixHandler, scope=Scope.REQUEST
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
    bulk_assign_product_attributes_handler: CompositeDependencySource = provide(
        BulkAssignProductAttributesHandler, scope=Scope.REQUEST
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
    get_product_completeness_handler: CompositeDependencySource = provide(
        GetProductCompletenessHandler, scope=Scope.REQUEST
    )


class MediaAssetProvider(Provider):
    """DI provider for product media asset repositories and handlers."""

    media_asset_repo: CompositeDependencySource = provide(
        MediaAssetRepository, scope=Scope.REQUEST, provides=IMediaAssetRepository
    )

    @provide(scope=Scope.APP)
    def image_backend_client(self, s: Settings) -> IImageBackendClient:
        """Provide the ImageBackendClient singleton."""
        return ImageBackendClient(
            base_url=s.IMAGE_BACKEND_URL,
            api_key=s.IMAGE_BACKEND_API_KEY.get_secret_value(),
        )

    # Command handlers
    delete_product_media_handler: CompositeDependencySource = provide(
        DeleteProductMediaHandler, scope=Scope.REQUEST
    )

    # Query handlers
    list_product_media_handler: CompositeDependencySource = provide(
        ListProductMediaHandler, scope=Scope.REQUEST
    )
