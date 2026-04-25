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
