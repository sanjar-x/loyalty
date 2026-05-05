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
    # writer adapter has been removed -- pricing now imports only the
    # port type from catalog domain, plus the read-side adapter for
    # pricing inputs.
    ("pricing", "catalog"): {
        "src.modules.pricing.infrastructure.adapters.sku_pricing_input_reader",
        "src.modules.pricing.infrastructure.services.recompute_service",
    },
    # Same input reader resolves ``supplier.type`` for the per-type
    # pricing context mapping during SKU recompute.
    ("pricing", "supplier"): {
        "src.modules.pricing.infrastructure.adapters.sku_pricing_input_reader",
    },
    # Pricing reads ``CurrencyModel.minor_unit`` for kopecks <->
    # major-unit conversion in both directions: input reader for
    # ``purchase_price``, scope reader for ``target_currency``
    # selling-price conversion (ADR-005a). The catalog-side
    # ``ApplySkuPricingResultHandler`` receives the converted integer
    # minor-unit value via :class:`SkuPricingApplyRequest` and never
    # imports the geo module itself.
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


# Rule 6 (FSM mixin purity): src/shared/interfaces/fsm.py MUST be pure
# stdlib -- the mixin will be imported by Order / PaymentIntent /
# Shipment in PR-1b'' and any framework leak (sqlalchemy, dishka, fastapi,
# pydantic, redis, taskiq, alembic, structlog) would pollute the domain
# layers consuming it. Enforced as a focused test rather than an archrule
# pattern because we want to whitelist stdlib + ``src.shared`` self-imports
# but reject any third-party / framework module by name.
_FSM_ALLOWED_IMPORT_PREFIXES = (
    "collections",
    "datetime",
    "enum",
    "typing",
    "abc",
    "uuid",
    "decimal",
    "src.shared",
)


def test_fsm_mixin_is_framework_free():
    """src/shared/interfaces/fsm.py imports stdlib + src.shared only."""
    import ast
    import pathlib

    fsm_path = (
        pathlib.Path(__file__).resolve().parents[2]
        / "src"
        / "shared"
        / "interfaces"
        / "fsm.py"
    )
    source = fsm_path.read_text()
    tree = ast.parse(source)
    forbidden: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not alias.name.startswith(_FSM_ALLOWED_IMPORT_PREFIXES):
                    forbidden.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "__future__":
                continue
            if not module.startswith(_FSM_ALLOWED_IMPORT_PREFIXES):
                forbidden.append(module)
    assert not forbidden, (
        f"src/shared/interfaces/fsm.py must remain pure-domain "
        f"(stdlib + src.shared only). Forbidden imports: {sorted(set(forbidden))}. "
        f"Adding a framework dependency here pollutes every domain "
        f"layer that consumes the mixin (REFACT-001 Rule 6 / FSM mixin)."
    )


# Rule 9: FSM aggregates inherit StateMachineMixin (REFACT-001 PR-1b'')
# Order / PaymentIntent / Shipment own optimistic-locked status FSMs and
# MUST consume the shared StateMachineMixin from
# ``src.shared.interfaces.fsm`` rather than re-implementing terminal
# checks, edge validation, and exception construction inline. The mixin
# centralises mechanical contract (terminal-first, then allowed-edge;
# kwargs-only ``current=``/``target=``/``status=`` exception signatures;
# ``is_terminal`` property; ``updated_at`` advancement) so a future
# fourth FSM aggregate gets the same semantics without copy-paste drift.
_FSM_AGGREGATE_MODULES: tuple[tuple[str, str], ...] = (
    ("order", "Order"),
    ("payment", "PaymentIntent"),
    ("logistics", "Shipment"),
)


# Rule 8: Module domain events inherit ModuleDomainEvent (REFACT-001 PR-4)
# Concrete domain events MUST inherit ``ModuleDomainEvent`` from
# ``src.shared.interfaces.entities`` (typically through a per-module
# abstract base like ``OrderEvent`` / ``PaymentEvent`` / ``IdentityEvent``)
# so every event picks up the canonical machinery: required-field
# validation on ``__post_init__``, ``aggregate_id`` auto-fill from a
# named field, and the abstract / required_fields / aggregate_id_field
# class-keyword API. Modules without aggregate-bound events (activity,
# geo, user) are opted out -- they emit no domain events of their own.
#
# CC-001 (CEO directive 2026-05-09) -- canonical convention enforced by
# the same test: a concrete event's class name MUST equal its
# ``event_type`` string. PascalCase format is the standard for every
# event_type in the outbox; legacy snake_case / dotted forms are
# transitional shims removed by REFACT-008 (7 days post-PR-4 merge).
_RULE_8_OPT_OUT_MODULES: frozenset[str] = frozenset({"activity", "geo", "user"})


@pytest.mark.parametrize(
    "module", [m for m in MODULES if m not in _RULE_8_OPT_OUT_MODULES]
)
def test_module_events_inherit_module_domain_event_and_match_cc001(
    module: str,
) -> None:
    """Every concrete event in the module inherits ``ModuleDomainEvent``
    AND its class name equals its ``event_type`` (CC-001)."""
    import importlib

    from src.shared.interfaces.entities import DomainEvent, ModuleDomainEvent

    events = importlib.import_module(f"src.modules.{module}.domain.events")
    violations: list[str] = []
    for name, obj in vars(events).items():
        if not (isinstance(obj, type) and issubclass(obj, DomainEvent)):
            continue
        if obj is DomainEvent or obj is ModuleDomainEvent:
            continue
        # Skip per-module abstract bases (``__abstract_event__`` is the
        # marker propagated by ``DomainEvent.__init_subclass__``).
        if getattr(obj, "__abstract_event__", False):
            continue
        if not issubclass(obj, ModuleDomainEvent):
            violations.append(f"{name}: must inherit ModuleDomainEvent (Rule 8)")
            continue
        # CC-001 -- class name must equal event_type string.
        event_type = getattr(obj, "event_type", "")
        if obj.__name__ != event_type:
            violations.append(
                f"{name}: class name != event_type='{event_type}' (CC-001)"
            )
    assert not violations, (
        f"Module '{module}' has event violations:\n  - "
        + "\n  - ".join(violations)
        + "\n(REFACT-001 PR-4 Rule 8 / CC-001)"
    )


@pytest.mark.parametrize(("module", "aggregate"), _FSM_AGGREGATE_MODULES)
def test_fsm_aggregate_inherits_state_machine_mixin(
    module: str, aggregate: str
) -> None:
    """FSM aggregates MUST inherit ``StateMachineMixin``."""
    import importlib

    from src.shared.interfaces.fsm import StateMachineMixin

    entities = importlib.import_module(f"src.modules.{module}.domain.entities")
    cls = getattr(entities, aggregate, None)
    assert cls is not None, (
        f"Module '{module}' does not expose aggregate '{aggregate}' in "
        f"domain.entities -- Rule 9 cannot verify mixin inheritance."
    )
    assert issubclass(cls, StateMachineMixin), (
        f"{aggregate} ({module}) must inherit "
        f"src.shared.interfaces.fsm.StateMachineMixin -- declare four "
        f"ClassVars (_ALLOWED_TRANSITIONS, _TERMINAL_STATES, "
        f"_invalid_transition_exc, _already_terminal_exc) and apply the "
        f"mixin (REFACT-001 PR-1b'' Rule 9). Inlined FSM logic is "
        f"forbidden."
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


# Rule 10: No module-local idempotency interfaces (REFACT-001 PR-3b)
# Modules MUST NOT redefine ``IIdempotencyStore`` / ``IInboxStore`` (or
# legacy aliases like ``IIdempotencyKeyStore``) inside their own domain
# layer -- the canonical ports live in ``src.shared.interfaces.idempotency``
# and the framework-shared ``IdempotencyProvider`` (in
# ``src.bootstrap.container``) wires the SqlIdempotencyStore /
# SqlInboxStore implementations across every bounded context. Module
# code must import from the shared kernel; local re-definitions cause
# DI graph fragmentation and re-introduce the duplication that
# REFACT-001 PR-3a / PR-3b consolidated away.
_FORBIDDEN_IDEMPOTENCY_PORT_NAMES = frozenset(
    {"IIdempotencyStore", "IIdempotencyKeyStore", "IInboxStore"}
)


@pytest.mark.parametrize("module", MODULES)
def test_no_module_local_idempotency_interfaces(module: str):
    """Module ``domain.interfaces`` must not redefine idempotency ports."""
    import importlib

    try:
        mod = importlib.import_module(f"src.modules.{module}.domain.interfaces")
    except ModuleNotFoundError:
        return  # module without domain.interfaces is allowed
    found = _FORBIDDEN_IDEMPOTENCY_PORT_NAMES.intersection(vars(mod).keys())
    assert not found, (
        f"Module '{module}' defines forbidden idempotency port(s) "
        f"{sorted(found)} in its domain.interfaces -- consume the "
        f"shared-kernel ports from src.shared.interfaces.idempotency "
        f"instead (REFACT-001 PR-3b Rule 10)."
    )
