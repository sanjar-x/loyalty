# tests/architecture/test_boundaries.py
"""
Architectural Fitness Functions — pytest-archon boundary enforcement.
Spec reference: docs/superpowers/specs/testing-design-specification.md Section 5
"""

import pytest
from pytest_archon import archrule

pytestmark = pytest.mark.architecture

MODULES = [
    "catalog",
    "identity",
    "user",
    "cart",
    "logistics",
    "pricing",
    "activity",
    "geo",
    "supplier",
    "favorites",
    "order",
    "payment",
    "recipient",
    "referral",
]


# Rule 1: Domain Layer Purity (Clean Architecture)
def test_domain_layer_is_pure():
    """Domain MUST NOT import from any outer layer."""
    (
        archrule("domain_independence")
        .match("src.modules.*.domain.*")
        .should_not_import("src.modules.*.application.*")
        .should_not_import("src.modules.*.infrastructure.*")
        .should_not_import("src.modules.*.presentation.*")
        .should_not_import("src.api.*")
        .should_not_import("src.bootstrap.*")
        .check("src")
    )


# Rule 2: Domain Has Zero Framework Imports
@pytest.mark.parametrize("module", MODULES)
def test_domain_has_zero_framework_imports(module: str):
    """Domain entities use attrs and stdlib only."""
    (
        archrule(f"{module}_domain_no_frameworks")
        .match(f"src.modules.{module}.domain.*")
        .should_not_import("sqlalchemy.*")
        .should_not_import("fastapi.*")
        .should_not_import("dishka.*")
        .should_not_import("redis.*")
        .should_not_import("taskiq.*")
        .should_not_import("pydantic.*")
        .should_not_import("alembic.*")
        .check("src")
    )


# Rule 3: Application Layer Boundaries
# NOTE: CQRS queries intentionally import ORM models for read-side performance,
# and consumers wire infrastructure for event processing — both are legitimate
# architecture patterns excluded from this rule.  Commands are allowed to
# compose queries (read-your-writes), so ``may_import`` whitelists the
# transitive path through ``application.queries.*``.
def test_application_layer_boundaries():
    """Application may import Domain but NOT Infrastructure or Presentation.

    Excludes:
    - ``*.application.queries.*``  — CQRS read-side uses ORM models directly.
    - ``*.application.consumers.*`` — event consumers wire infrastructure.
    """
    (
        archrule("application_independence")
        .match("src.modules.*.application.*")
        .exclude("src.modules.*.application.queries.*")
        .exclude("src.modules.*.application.consumers.*")
        .exclude("src.modules.geo.application.commands.*")
        .should_not_import("src.modules.*.infrastructure.*")
        .should_not_import("src.modules.*.presentation.*")
        .should_not_import("src.api.*")
        .may_import("src.modules.*.application.queries.*")
        .check("src", only_direct_imports=True)
    )


# Rule 4: Infrastructure Does Not Import Presentation
def test_infrastructure_does_not_import_presentation():
    """Infrastructure MUST NOT depend on web routers."""
    (
        archrule("infrastructure_independence")
        .match("src.modules.*.infrastructure.*")
        .should_not_import("src.modules.*.presentation.*")
        .should_not_import("src.api.*")
        .check("src")
    )


# Rule 5: Modular Monolith Cross-Module Isolation
# Allowed cross-module presentation dependency:
#   user.presentation → identity.presentation  (profile router uses auth deps)
#   catalog.presentation → identity.presentation  (catalog router uses RequirePermission)
ALLOWED_CROSS_MODULE = {
    ("user", "identity"): {"src.modules.user.presentation.*"},
    ("catalog", "identity"): {"src.modules.catalog.presentation.*"},
    ("pricing", "identity"): {"src.modules.pricing.presentation.*"},
    ("activity", "identity"): {"src.modules.activity.presentation.*"},
    # Cart's catalog adapter (infrastructure-level) reads catalog ORM models
    # directly to validate SKUs during add-to-cart. This is an anti-corruption
    # adapter — the only legitimate cross-module infrastructure bridge.
    ("cart", "catalog"): {"src.modules.cart.infrastructure.adapters.catalog_adapter"},
    # Same adapter JOINs supplier ORM to surface supplier_type on cart lines
    # (cross-border / local policy). Same anti-corruption justification.
    ("cart", "supplier"): {"src.modules.cart.infrastructure.adapters.catalog_adapter"},
    # Storefront CQRS read-side projects ``supplier.type`` onto product cards
    # and PDPs (cross-border vs local policy). Read-only ORM JOIN — same
    # CQRS-read exemption that lets ``catalog.application.queries`` touch
    # the catalog ORM directly. Tightly enumerated (not ``queries.*``) so
    # a future query can't quietly pull in more of the supplier module.
    ("catalog", "supplier"): {
        "src.modules.catalog.application.queries.list_storefront_products",
        "src.modules.catalog.application.queries.get_storefront_product",
        "src.modules.catalog.application.queries.search_products",
        "src.modules.catalog.application.queries.get_storefront_cards_by_ids",
    },
    # ADR-005 / ADR-005a — pricing recompute reads SKU purchase price
    # from catalog through a read-only ACL adapter and writes the
    # selling price back through the catalog-side
    # ``IInternalSkuPricingApplyPort`` (declared in
    # ``catalog.domain.interfaces``, implemented in
    # ``catalog.application.commands.apply_sku_pricing_result``). The
    # writer adapter has been removed — pricing now imports only the
    # port type from catalog domain, plus the read-side adapters below
    # for inputs and scope:
    #   * ``sku_pricing_input_reader`` — JOINs SKU + Product +
    #     Supplier to materialise :class:`SkuPricingInputs` DTOs.
    # The pricing service additionally imports
    # ``catalog.domain.interfaces`` (port + DTOs); domain-only types
    # are intentionally allowed because that's the sanctioned
    # cross-module contract — the architecture rule should not see it
    # as a violation, but we whitelist the recompute service file
    # explicitly so any *new* file in pricing trying to reach into
    # catalog is rejected by default.
    ("pricing", "catalog"): {
        "src.modules.pricing.infrastructure.adapters.sku_pricing_input_reader",
        "src.modules.pricing.infrastructure.services.recompute_service",
    },
    # Same input reader resolves ``supplier.type`` for the per-type
    # pricing context mapping during SKU recompute.
    ("pricing", "supplier"): {
        "src.modules.pricing.infrastructure.adapters.sku_pricing_input_reader",
    },
    # Pricing reads ``CurrencyModel.minor_unit`` for kopecks ↔
    # major-unit conversion in both directions: input reader for
    # ``purchase_price``, scope reader for ``target_currency``
    # selling-price conversion (ADR-005a). The catalog-side
    # ``ApplySkuPricingResultHandler`` receives the converted
    # integer minor-unit value via :class:`SkuPricingApplyRequest`
    # and never imports the geo module itself.
    ("pricing", "geo"): {
        "src.modules.pricing.infrastructure.adapters.sku_pricing_input_reader",
        "src.modules.pricing.infrastructure.adapters.sku_pricing_scope_reader",
    },
    # Logistics builds Parcel weights from a category-level estimate
    # maintained in pricing (Product → Category → CategoryPricingSettings).
    # The marketplace dropships from China, so the actual SKU weight is
    # unknown until parcels reach the RF warehouse — see
    # logistics/infrastructure/adapters/pricing_weight_adapter.py.
    # Read-only ORM JOIN, narrowly scoped to that one adapter.
    ("logistics", "catalog"): {
        "src.modules.logistics.infrastructure.adapters.pricing_weight_adapter",
    },
    ("logistics", "pricing"): {
        "src.modules.logistics.infrastructure.adapters.pricing_weight_adapter",
    },
    ("logistics", "supplier"): {
        "src.modules.logistics.infrastructure.adapters.pricing_weight_adapter",
    },
    # Identity management CLI scripts (``create_admin``, ``sync_system_roles``)
    # reach into the full DI container for standalone bootstrap; they are
    # admin tooling, not production request paths.
    ("identity", "catalog"): {"src.modules.identity.management.*"},
    ("identity", "user"): {"src.modules.identity.management.*"},
    ("identity", "cart"): {"src.modules.identity.management.*"},
    ("identity", "logistics"): {"src.modules.identity.management.*"},
    ("identity", "pricing"): {"src.modules.identity.management.*"},
    ("identity", "activity"): {"src.modules.identity.management.*"},
    ("identity", "geo"): {"src.modules.identity.management.*"},
    ("identity", "supplier"): {"src.modules.identity.management.*"},
    # Favorites: the catalog ACL adapter validates target existence
    # (Product/Brand) before saving, and the read-side queries enrich
    # items with product/brand cards via direct ORM JOIN. Both are
    # narrowly scoped — same CQRS-read exemption as catalog→supplier.
    ("favorites", "catalog"): {
        "src.modules.favorites.infrastructure.adapters.catalog_target_validator",
        "src.modules.favorites.application.queries.get_list_items",
    },
    # Favorites router uses identity's Auth dependency.
    ("favorites", "identity"): {"src.modules.favorites.presentation.*"},
    # Order: read-side enrichment may JOIN catalog/supplier ORM via narrowly
    # scoped query files (same CQRS-read exemption as catalog→supplier).
    # Snapshot ingest from cart goes through a single ACL adapter so Order
    # never sees Cart's domain entities; the Cart ``order_adapter`` is
    # already whitelisted on the cart side as ``cart→order``.
    ("order", "catalog"): {
        "src.modules.order.application.queries.list_my_orders",
        "src.modules.order.application.queries.get_order",
    },
    ("order", "supplier"): {
        "src.modules.order.application.queries.list_my_orders",
        "src.modules.order.application.queries.get_order",
    },
    ("order", "cart"): {
        "src.modules.order.infrastructure.adapters.cart_snapshot_reader",
    },
    # Order ↔ Logistics: cross-border + last-mile shipments are created
    # through ACL gateway adapters that today are stubs (no logistics
    # imports). When the real integration lands, this whitelist becomes
    # the single allowed touch point for those two adapter files.
    ("order", "logistics"): set(),
    # Payment never imports Order: payment publishes domain events to
    # the outbox, and Order's consumers (PaymentCapturedConsumer /
    # PaymentFailedConsumer) reach back into the Order FSM.
    ("payment", "order"): set(),
    # Order initiates payment by invoking the public payment command
    # handler — single ACL adapter, no Payment ORM access.
    ("order", "payment"): {
        "src.modules.order.infrastructure.adapters.payment_gateway",
    },
    # Order routers use identity's Auth/RequirePermission deps.
    ("order", "identity"): {"src.modules.order.presentation.*"},
    # Payment routers use identity's Auth/RequirePermission deps.
    ("payment", "identity"): {"src.modules.payment.presentation.*"},
    # Recipient routers use identity's Auth dep.
    ("recipient", "identity"): {"src.modules.recipient.presentation.*"},
    # Order ↔ Recipient: order reads Recipient via a single ACL adapter
    # (read-side projection). Recipient never imports order.
    ("order", "recipient"): {
        "src.modules.order.infrastructure.adapters.recipient_lookup",
    },
    # Cart ↔ Recipient: ownership check before freezing the snapshot.
    ("cart", "recipient"): {
        "src.modules.cart.infrastructure.adapters.recipient_lookup",
    },
}


@pytest.mark.parametrize(
    "source,target",
    [(s, t) for s in MODULES for t in MODULES if s != t],
)
def test_module_isolation(source: str, target: str):
    """Modules MUST NOT directly import each other's internals."""
    excludes = ALLOWED_CROSS_MODULE.get((source, target), set())
    for layer in ["domain", "application", "infrastructure"]:
        rule = archrule(f"{source}_cannot_import_{target}_{layer}").match(
            f"src.modules.{source}.*"
        )
        for exc in excludes:
            rule = rule.exclude(exc)
        (
            rule.should_not_import(f"src.modules.{target}.{layer}.*").check(
                "src", only_direct_imports=True
            )
        )


# Rule 6: Shared Kernel Independence
def test_shared_kernel_is_independent():
    """src/shared/ MUST NOT import from any business module."""
    (
        archrule("shared_kernel_independence")
        .match("src.shared.*")
        .should_not_import("src.modules.*")
        .check("src")
    )


# Rule 6b: shared/ledger is part of the shared kernel and may not depend
# on any infrastructure implementation. It is a pure-domain abstraction
# consumed by every module that owns balances (referral, future cashback,
# supplier payouts, ...). SQLAlchemy / Dishka / Redis / TaskIQ touch it
# only through ports, never the other way around.
def test_shared_ledger_has_zero_framework_imports() -> None:
    """src/shared/ledger/ MUST stay free of framework imports."""
    (
        archrule("shared_ledger_no_frameworks")
        .match("src.shared.ledger.*")
        .should_not_import("sqlalchemy.*")
        .should_not_import("fastapi.*")
        .should_not_import("dishka.*")
        .should_not_import("redis.*")
        .should_not_import("taskiq.*")
        .should_not_import("pydantic.*")
        .should_not_import("alembic.*")
        .check("src")
    )


# Rule 7: No Reverse Layer Dependencies
@pytest.mark.parametrize("module", MODULES)
def test_no_reverse_layer_dependencies(module: str):
    """Within a module: Domain <- Application <- Infrastructure <- Presentation."""
    # Domain must not import Application
    (
        archrule(f"{module}_domain_not_import_application")
        .match(f"src.modules.{module}.domain.*")
        .should_not_import(f"src.modules.{module}.application.*")
        .check("src")
    )
    # Application must not import Infrastructure
    # (excluding CQRS queries and event consumers — see Rule 3 rationale;
    # commands may compose queries via may_import)
    (
        archrule(f"{module}_application_not_import_infrastructure")
        .match(f"src.modules.{module}.application.*")
        .exclude(f"src.modules.{module}.application.queries.*")
        .exclude(f"src.modules.{module}.application.consumers.*")
        .exclude("src.modules.geo.application.commands.*")
        .should_not_import(f"src.modules.{module}.infrastructure.*")
        .may_import(f"src.modules.{module}.application.queries.*")
        .check("src", only_direct_imports=True)
    )


# Rule 8: Module domain events must inherit ``ModuleDomainEvent``,
# not ``DomainEvent`` directly. Centralizing required-field validation
# and ``aggregate_id`` auto-fill on a single shared base prevents
# 30-line ``__init_subclass__`` boilerplate from re-appearing in every
# new module.
#
# Reference-data bounded contexts (``activity``, ``geo``, ``user``)
# do not declare any ``domain/events.py`` of their own — they are
# trivially compliant. ``user`` is included here because Customer /
# StaffMember PII updates are handled by direct Identity-event
# consumption rather than emitting new events; once that pattern
# changes, drop ``user`` from this set.
_MODULE_EVENT_BASE_OPT_OUT: frozenset[str] = frozenset({"activity", "geo", "user"})


@pytest.mark.parametrize(
    "module",
    [m for m in MODULES if m not in _MODULE_EVENT_BASE_OPT_OUT],
)
def test_module_events_use_shared_module_event_base(module: str) -> None:
    """``src/modules/<m>/domain/events.py`` must not import ``DomainEvent``
    directly — it must use :class:`ModuleDomainEvent` from the shared
    kernel so that validation, ``aggregate_id`` auto-fill, and the
    abstract-base flag are uniform across the codebase.
    """
    (
        archrule(f"{module}_events_use_module_domain_event")
        .match(f"src.modules.{module}.domain.events")
        .should_not_import("src.shared.interfaces.entities.DomainEvent")
        .check("src")
    )


# Rule 9: Aggregates with a directed FSM (``_ALLOWED_TRANSITIONS`` ClassVar)
# must inherit :class:`StateMachineMixin` from the shared kernel rather
# than reimplementing transition validation in module-local helpers.
#
# Source-level enforcement is approximate (pytest-archon operates on
# imports, not class graphs), so we lean on a textual check that the
# domain layer of every FSM-bearing module imports the shared mixin.
# Modules listed in the opt-out set use module-specific FSM mechanics
# (``cart`` declares ``_ALLOWED_TRANSITIONS`` but does not enforce it
# yet — see PR-0b followup; ``catalog/product`` overrides ``__setattr__``
# and embeds non-FSM business invariants inside ``transition_status``).
_FSM_MIXIN_OPT_OUT: frozenset[str] = frozenset({"cart", "catalog"})

_FSM_MODULES: frozenset[str] = frozenset({"order", "payment", "logistics"})


@pytest.mark.parametrize("module", sorted(_FSM_MODULES))
def test_fsm_aggregates_use_shared_state_machine_mixin(module: str) -> None:
    """FSM-bearing aggregates must use :class:`StateMachineMixin`."""
    (
        archrule(f"{module}_uses_shared_fsm_mixin")
        .match(f"src.modules.{module}.domain.entities*")
        .should_import("src.shared.interfaces.fsm")
        .check("src")
    )


# Rule 10: idempotency keys + consumer inbox are owned by the shared
# kernel. Modules MUST NOT declare their own ``IIdempotencyStore`` /
# ``IInboxStore`` interfaces or per-module copies of the SQL adapter —
# the contract lives in :mod:`src.shared.interfaces.idempotency` and
# the Postgres implementation lives in :mod:`src.infrastructure.idempotency`.
#
# Per-module discrimination is achieved through the ``scope`` /
# ``consumer`` columns on the shared tables (each module passes its own
# values), not through duplicate table layouts.
@pytest.mark.parametrize("module", MODULES)
def test_modules_do_not_declare_local_idempotency_or_inbox_interfaces(
    module: str,
) -> None:
    """Modules MUST NOT redefine ``IIdempotencyStore`` / ``IInboxStore``."""
    domain_path = f"src/modules/{module}/domain/interfaces.py"
    try:
        with open(domain_path, encoding="utf-8") as fh:
            source = fh.read()
    except FileNotFoundError:
        return  # module has no interfaces.py — trivially compliant
    forbidden_names = (
        "class IIdempotencyKeyStore",
        "class IIdempotencyStore",
        "class IInboxStore",
    )
    for name in forbidden_names:
        assert name not in source, (
            f"{domain_path} declares '{name}' — the interface lives in "
            "src.shared.interfaces.idempotency. Remove the local copy."
        )


# Rule 11: Every bounded-context module listed in :data:`MODULES` must
# expose a :class:`ModuleManifest` constant via
# ``src/modules/<name>/module.py``. This is what the bootstrap loop
# in :mod:`src.bootstrap.modules` aggregates — a missing manifest
# means the module is silently absent from the DI container, the
# aggregate router, and the worker / scheduler import chain.
@pytest.mark.parametrize("module", MODULES)
def test_every_module_has_a_bootstrap_manifest(module: str) -> None:
    """``src/modules/<name>/module.py`` MUST exist and declare a manifest."""
    import os

    manifest_path = f"src/modules/{module}/module.py"
    assert os.path.exists(manifest_path), (
        f"Missing bootstrap manifest: {manifest_path}. Every module in "
        "MODULES must declare a ModuleManifest constant so that the "
        "DI container, FastAPI router aggregation, and TaskIQ worker "
        "bootstrap can pick it up automatically."
    )
    with open(manifest_path, encoding="utf-8") as fh:
        source = fh.read()
    assert "ModuleManifest" in source, (
        f"{manifest_path} must declare a ModuleManifest constant."
    )
