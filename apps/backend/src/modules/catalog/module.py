"""Bootstrap manifest for the catalog bounded context.

Catalog is the largest module: 11 admin routers (one per editable
resource — brands, categories, attributes, attribute values, attribute
groups, attribute templates, products, variants, SKUs, product
attributes, media) and 6 storefront read-routers.
"""

from src.bootstrap.module_registry import ModuleManifest
from src.modules.catalog.infrastructure.provider import (
    AttributeGroupProvider,
    AttributeProvider,
    AttributeTemplateProvider,
    AttributeValueProvider,
    BrandProvider,
    CategoryProvider,
    MediaAssetProvider,
    ProductProvider,
    StorefrontCatalogProvider,
)
from src.modules.catalog.presentation.router_admin_attribute_groups import (
    attribute_group_router,
)
from src.modules.catalog.presentation.router_admin_attribute_templates import (
    attribute_template_router,
)
from src.modules.catalog.presentation.router_admin_attribute_values import (
    attribute_value_router,
)
from src.modules.catalog.presentation.router_admin_attributes import attribute_router
from src.modules.catalog.presentation.router_admin_brands import brand_router
from src.modules.catalog.presentation.router_admin_categories import category_router
from src.modules.catalog.presentation.router_admin_media import media_router
from src.modules.catalog.presentation.router_admin_product_attributes import (
    product_attribute_router,
)
from src.modules.catalog.presentation.router_admin_products import product_router
from src.modules.catalog.presentation.router_admin_skus import sku_router
from src.modules.catalog.presentation.router_admin_variants import variant_router
from src.modules.catalog.presentation.router_storefront import storefront_router
from src.modules.catalog.presentation.router_storefront_for_you import (
    storefront_for_you_router,
)
from src.modules.catalog.presentation.router_storefront_products import (
    storefront_products_router,
)
from src.modules.catalog.presentation.router_storefront_search import (
    storefront_search_router,
)
from src.modules.catalog.presentation.router_storefront_taxonomy import (
    storefront_taxonomy_router,
)
from src.modules.catalog.presentation.router_storefront_trending import (
    storefront_trending_router,
)

CATALOG_MODULE = ModuleManifest(
    name="catalog",
    providers=(
        CategoryProvider(),
        BrandProvider(),
        AttributeGroupProvider(),
        AttributeProvider(),
        AttributeValueProvider(),
        AttributeTemplateProvider(),
        StorefrontCatalogProvider(),
        ProductProvider(),
        MediaAssetProvider(),
    ),
    customer_routers=(
        storefront_router,
        storefront_taxonomy_router,
        storefront_products_router,
        storefront_search_router,
        storefront_trending_router,
        storefront_for_you_router,
    ),
    admin_routers=(
        brand_router,
        category_router,
        attribute_router,
        attribute_group_router,
        attribute_value_router,
        attribute_template_router,
        product_router,
        variant_router,
        sku_router,
        product_attribute_router,
        media_router,
    ),
    # CAT-005 — bridges outbox-delivered SKUPricedEvent / SKUPricingFailedEvent
    # to the per-product Redis pub/sub channel that admin SSE streams to UI.
    # IMG-004 — bridges StorageObjectProcessedEvent into the catalog
    # media-sync consumer so reuploads keep ``media_assets.url`` fresh.
    # IMG-005 — bridges MediaAssetDetachedEvent into a TaskIQ cleanup
    # job so storage objects are dropped asynchronously after the
    # catalog row commit (atomicity + retry vs. best-effort post-commit).
    task_modules=(
        "src.modules.catalog.application.consumers.sku_pricing_events",
        "src.modules.catalog.application.consumers.storage_object_processed",
        "src.modules.catalog.application.consumers.media_asset_detached",
    ),
)
