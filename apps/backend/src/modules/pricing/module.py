"""Bootstrap manifest for the pricing bounded context.

Pricing exposes 9 admin sub-resources (variables, contexts, formulas,
preview, profiles, supplier settings, supplier-type → context mapping,
category settings, recompute) and emits SKU-pricing recompute events
to the outbox relay.
"""

from src.bootstrap.module_registry import ModuleManifest
from src.modules.pricing.infrastructure.provider import PricingProvider
from src.modules.pricing.presentation.router_admin_categories import (
    pricing_category_settings_router,
)
from src.modules.pricing.presentation.router_admin_contexts import (
    pricing_context_router,
)
from src.modules.pricing.presentation.router_admin_formulas import (
    pricing_formula_router,
)
from src.modules.pricing.presentation.router_admin_preview import (
    pricing_preview_router,
)
from src.modules.pricing.presentation.router_admin_products import (
    pricing_profile_router,
)
from src.modules.pricing.presentation.router_admin_recompute import (
    pricing_recompute_router,
)
from src.modules.pricing.presentation.router_admin_supplier_type_mapping import (
    pricing_supplier_type_mapping_router,
)
from src.modules.pricing.presentation.router_admin_suppliers import (
    pricing_supplier_settings_router,
)
from src.modules.pricing.presentation.router_admin_variables import (
    pricing_variable_router,
)

PRICING_MODULE = ModuleManifest(
    name="pricing",
    providers=(PricingProvider(),),
    admin_routers=(
        pricing_variable_router,
        pricing_context_router,
        pricing_formula_router,
        pricing_preview_router,
        pricing_profile_router,
        pricing_supplier_settings_router,
        pricing_supplier_type_mapping_router,
        pricing_category_settings_router,
        pricing_recompute_router,
    ),
    task_modules=("src.modules.pricing.infrastructure.tasks",),
)
