"""Dishka IoC provider for the pricing bounded context."""

from __future__ import annotations

from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource

from src.modules.pricing.application.commands.create_context import (
    CreateContextHandler,
)
from src.modules.pricing.application.commands.create_variable import (
    CreateVariableHandler,
)
from src.modules.pricing.application.commands.deactivate_context import (
    DeactivateContextHandler,
)
from src.modules.pricing.application.commands.delete_category_pricing_settings import (
    DeleteCategoryPricingSettingsHandler,
)
from src.modules.pricing.application.commands.delete_product_pricing_profile import (
    DeleteProductPricingProfileHandler,
)
from src.modules.pricing.application.commands.delete_supplier_type_context_mapping import (
    DeleteSupplierTypeContextMappingHandler,
)
from src.modules.pricing.application.commands.delete_variable import (
    DeleteVariableHandler,
)
from src.modules.pricing.application.commands.discard_formula_draft import (
    DiscardFormulaDraftHandler,
)
from src.modules.pricing.application.commands.freeze_context import (
    FreezeContextHandler,
)
from src.modules.pricing.application.commands.publish_formula_draft import (
    PublishFormulaDraftHandler,
)
from src.modules.pricing.application.commands.rollback_formula import (
    RollbackFormulaHandler,
)
from src.modules.pricing.application.commands.set_context_global_value import (
    SetContextGlobalValueHandler,
)
from src.modules.pricing.application.commands.unfreeze_context import (
    UnfreezeContextHandler,
)
from src.modules.pricing.application.commands.update_context import (
    UpdateContextHandler,
)
from src.modules.pricing.application.commands.update_variable import (
    UpdateVariableHandler,
)
from src.modules.pricing.application.commands.upsert_category_pricing_settings import (
    UpsertCategoryPricingSettingsHandler,
)
from src.modules.pricing.application.commands.upsert_formula_draft import (
    UpsertFormulaDraftHandler,
)
from src.modules.pricing.application.commands.upsert_product_pricing_profile import (
    UpsertProductPricingProfileHandler,
)
from src.modules.pricing.application.commands.upsert_supplier_pricing_settings import (
    UpsertSupplierPricingSettingsHandler,
)
from src.modules.pricing.application.commands.upsert_supplier_type_context_mapping import (
    UpsertSupplierTypeContextMappingHandler,
)
from src.modules.pricing.application.queries.category_pricing_settings import (
    GetCategoryPricingSettingsHandler,
)
from src.modules.pricing.application.queries.context_global_values import (
    GetContextGlobalValuesHandler,
)
from src.modules.pricing.application.queries.contexts import (
    GetContextHandler,
    ListContextsHandler,
)
from src.modules.pricing.application.queries.formulas import (
    GetFormulaDraftHandler,
    GetFormulaVersionHandler,
    ListFormulaVersionsHandler,
)
from src.modules.pricing.application.queries.get_product_pricing_profile import (
    GetProductPricingProfileHandler,
)
from src.modules.pricing.application.queries.preview_price import (
    PreviewPriceHandler,
)
from src.modules.pricing.application.queries.required_variables import (
    GetRequiredVariablesHandler,
)
from src.modules.pricing.application.queries.supplier_pricing_settings import (
    GetSupplierPricingSettingsHandler,
)
from src.modules.pricing.application.queries.supplier_type_context_mappings import (
    GetSupplierTypeContextMappingHandler,
    ListSupplierTypeContextMappingsHandler,
)
from src.modules.pricing.application.queries.variables import (
    GetVariableHandler,
    ListVariablesHandler,
)
from src.modules.pricing.domain.interfaces import (
    ICategoryPricingSettingsRepository,
    IFormulaVersionRepository,
    IPricingContextRepository,
    IProductPricingProfileRepository,
    ISupplierPricingSettingsRepository,
    ISupplierTypeContextMappingRepository,
    IVariableRepository,
)
from src.modules.pricing.infrastructure.repositories.category_pricing_settings import (
    CategoryPricingSettingsRepository,
)
from src.modules.pricing.infrastructure.repositories.formula_version import (
    FormulaVersionRepository,
)
from src.modules.pricing.infrastructure.repositories.pricing_context import (
    PricingContextRepository,
)
from src.modules.pricing.infrastructure.repositories.product_pricing_profile import (
    ProductPricingProfileRepository,
)
from src.modules.pricing.infrastructure.repositories.supplier_pricing_settings import (
    SupplierPricingSettingsRepository,
)
from src.modules.pricing.infrastructure.repositories.supplier_type_context_mapping import (
    SupplierTypeContextMappingRepository,
)
from src.modules.pricing.infrastructure.repositories.variable import (
    VariableRepository,
)


class PricingProvider(Provider):
    """DI provider for pricing repositories and command/query handlers."""

    # --- Repositories ---
    profile_repo: CompositeDependencySource = provide(
        ProductPricingProfileRepository,
        scope=Scope.REQUEST,
        provides=IProductPricingProfileRepository,
    )
    variable_repo: CompositeDependencySource = provide(
        VariableRepository,
        scope=Scope.REQUEST,
        provides=IVariableRepository,
    )
    context_repo: CompositeDependencySource = provide(
        PricingContextRepository,
        scope=Scope.REQUEST,
        provides=IPricingContextRepository,
    )
    formula_repo: CompositeDependencySource = provide(
        FormulaVersionRepository,
        scope=Scope.REQUEST,
        provides=IFormulaVersionRepository,
    )
    category_settings_repo: CompositeDependencySource = provide(
        CategoryPricingSettingsRepository,
        scope=Scope.REQUEST,
        provides=ICategoryPricingSettingsRepository,
    )
    supplier_type_mapping_repo: CompositeDependencySource = provide(
        SupplierTypeContextMappingRepository,
        scope=Scope.REQUEST,
        provides=ISupplierTypeContextMappingRepository,
    )
    supplier_settings_repo: CompositeDependencySource = provide(
        SupplierPricingSettingsRepository,
        scope=Scope.REQUEST,
        provides=ISupplierPricingSettingsRepository,
    )

    # --- Command handlers ---
    upsert_profile_handler: CompositeDependencySource = provide(
        UpsertProductPricingProfileHandler, scope=Scope.REQUEST
    )
    delete_profile_handler: CompositeDependencySource = provide(
        DeleteProductPricingProfileHandler, scope=Scope.REQUEST
    )
    create_variable_handler: CompositeDependencySource = provide(
        CreateVariableHandler, scope=Scope.REQUEST
    )
    update_variable_handler: CompositeDependencySource = provide(
        UpdateVariableHandler, scope=Scope.REQUEST
    )
    delete_variable_handler: CompositeDependencySource = provide(
        DeleteVariableHandler, scope=Scope.REQUEST
    )
    create_context_handler: CompositeDependencySource = provide(
        CreateContextHandler, scope=Scope.REQUEST
    )
    update_context_handler: CompositeDependencySource = provide(
        UpdateContextHandler, scope=Scope.REQUEST
    )
    deactivate_context_handler: CompositeDependencySource = provide(
        DeactivateContextHandler, scope=Scope.REQUEST
    )
    freeze_context_handler: CompositeDependencySource = provide(
        FreezeContextHandler, scope=Scope.REQUEST
    )
    unfreeze_context_handler: CompositeDependencySource = provide(
        UnfreezeContextHandler, scope=Scope.REQUEST
    )
    upsert_formula_draft_handler: CompositeDependencySource = provide(
        UpsertFormulaDraftHandler, scope=Scope.REQUEST
    )
    discard_formula_draft_handler: CompositeDependencySource = provide(
        DiscardFormulaDraftHandler, scope=Scope.REQUEST
    )
    publish_formula_draft_handler: CompositeDependencySource = provide(
        PublishFormulaDraftHandler, scope=Scope.REQUEST
    )
    rollback_formula_handler: CompositeDependencySource = provide(
        RollbackFormulaHandler, scope=Scope.REQUEST
    )
    upsert_category_settings_handler: CompositeDependencySource = provide(
        UpsertCategoryPricingSettingsHandler, scope=Scope.REQUEST
    )
    delete_category_settings_handler: CompositeDependencySource = provide(
        DeleteCategoryPricingSettingsHandler, scope=Scope.REQUEST
    )
    upsert_supplier_type_mapping_handler: CompositeDependencySource = provide(
        UpsertSupplierTypeContextMappingHandler, scope=Scope.REQUEST
    )
    upsert_supplier_settings_handler: CompositeDependencySource = provide(
        UpsertSupplierPricingSettingsHandler, scope=Scope.REQUEST
    )
    delete_supplier_type_mapping_handler: CompositeDependencySource = provide(
        DeleteSupplierTypeContextMappingHandler, scope=Scope.REQUEST
    )

    # --- Query handlers ---
    get_profile_handler: CompositeDependencySource = provide(
        GetProductPricingProfileHandler, scope=Scope.REQUEST
    )
    preview_price_handler: CompositeDependencySource = provide(
        PreviewPriceHandler, scope=Scope.REQUEST
    )
    get_variable_handler: CompositeDependencySource = provide(
        GetVariableHandler, scope=Scope.REQUEST
    )
    list_variables_handler: CompositeDependencySource = provide(
        ListVariablesHandler, scope=Scope.REQUEST
    )
    get_context_handler: CompositeDependencySource = provide(
        GetContextHandler, scope=Scope.REQUEST
    )
    list_contexts_handler: CompositeDependencySource = provide(
        ListContextsHandler, scope=Scope.REQUEST
    )
    get_formula_version_handler: CompositeDependencySource = provide(
        GetFormulaVersionHandler, scope=Scope.REQUEST
    )
    list_formula_versions_handler: CompositeDependencySource = provide(
        ListFormulaVersionsHandler, scope=Scope.REQUEST
    )
    get_formula_draft_handler: CompositeDependencySource = provide(
        GetFormulaDraftHandler, scope=Scope.REQUEST
    )
    get_category_settings_handler: CompositeDependencySource = provide(
        GetCategoryPricingSettingsHandler, scope=Scope.REQUEST
    )
    get_supplier_type_mapping_handler: CompositeDependencySource = provide(
        GetSupplierTypeContextMappingHandler, scope=Scope.REQUEST
    )
    get_supplier_settings_handler: CompositeDependencySource = provide(
        GetSupplierPricingSettingsHandler, scope=Scope.REQUEST
    )
    list_supplier_type_mappings_handler: CompositeDependencySource = provide(
        ListSupplierTypeContextMappingsHandler, scope=Scope.REQUEST
    )
    set_context_global_value_handler: CompositeDependencySource = provide(
        SetContextGlobalValueHandler, scope=Scope.REQUEST
    )
    get_context_global_values_handler: CompositeDependencySource = provide(
        GetContextGlobalValuesHandler, scope=Scope.REQUEST
    )
    get_required_variables_handler: CompositeDependencySource = provide(
        GetRequiredVariablesHandler, scope=Scope.REQUEST
    )
