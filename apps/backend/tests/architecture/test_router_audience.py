"""Architectural fitness functions for the router audience invariant.

Convention is documented in `backend/CLAUDE.md` (section "Router naming
convention") and `docs/api/router-restructure-2026-05.md`. The three
namespaces are mutually exclusive at the URL level:

* ``/admin/...``    — staff-only (`router_admin*.py`)
* ``/webhooks/...`` — server-to-server (`router_webhooks*.py`)
* anything else     — customer / public (`router_<audience>.py`)

These tests verify that the wiring matches the convention so a future
contributor can't quietly publish an admin-only endpoint without ``/admin``
in front of it (or vice versa).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

PRESENTATION_GLOB = "src/modules/*/presentation/router_*.py"
_PREFIX_RE = re.compile(r'prefix\s*=\s*"([^"]+)"')


def _collect_routers() -> list[tuple[Path, str]]:
    """Read every router file once, return (path, prefix) tuples."""
    backend_root = Path(__file__).resolve().parents[2]
    out: list[tuple[Path, str]] = []
    for path in backend_root.glob(PRESENTATION_GLOB):
        text = path.read_text(encoding="utf-8")
        match = _PREFIX_RE.search(text)
        if match is None:
            # Routers without an explicit prefix exist for tiny utility
            # endpoints; skip — they show up at app-level mounting.
            continue
        out.append((path, match.group(1)))
    return out


# ---------------------------------------------------------------------------
# Rule 1: file `router_admin*.py` ⇒ prefix begins with `/admin/`
# ---------------------------------------------------------------------------


def test_router_admin_files_have_admin_prefix() -> None:
    """Every file matching ``router_admin*.py`` must mount under `/admin/`."""
    violations: list[str] = []
    for path, prefix in _collect_routers():
        if path.name.startswith("router_admin") and not prefix.startswith("/admin"):
            violations.append(f"{path.relative_to(path.parents[4])}: prefix={prefix!r}")
    assert not violations, (
        "router_admin*.py files must mount under /admin/. Violations:\n"
        + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# Rule 2: file `router_webhooks*.py` ⇒ prefix begins with `/webhooks/`
# ---------------------------------------------------------------------------


def test_router_webhooks_files_have_webhooks_prefix() -> None:
    """Every file matching ``router_webhooks*.py`` must mount under `/webhooks/`."""
    violations: list[str] = []
    for path, prefix in _collect_routers():
        if path.name.startswith("router_webhooks") and not prefix.startswith(
            "/webhooks"
        ):
            violations.append(f"{path.relative_to(path.parents[4])}: prefix={prefix!r}")
    assert not violations, (
        "router_webhooks*.py files must mount under /webhooks/. Violations:\n"
        + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# Rule 3: prefix `/admin/...` ⇒ file name signals admin audience
# ---------------------------------------------------------------------------
# Some non-admin-named files (logistics router_admin_shipments.py,
# identity router_customers.py, identity router_staff.py) all use
# `/admin/...`. They are admin by intent — the convention requires that
# admin-prefixed routers live in files containing `admin` in the name OR
# in identity's customers/staff routers (whitelisted by name).

_ADMIN_FILE_TOKENS = ("admin", "customers", "staff")


def test_admin_prefix_routers_live_in_admin_files() -> None:
    """Routers with `/admin/` prefix must be in *admin-signalling* files."""
    violations: list[str] = []
    for path, prefix in _collect_routers():
        if not prefix.startswith("/admin"):
            continue
        if not any(token in path.stem for token in _ADMIN_FILE_TOKENS):
            violations.append(
                f"{path.relative_to(path.parents[4])}: prefix={prefix!r} "
                f"(rename file to router_admin*.py for clarity)"
            )
    assert not violations, (
        "Routers under /admin/ should live in router_admin*.py files (or "
        "identity router_customers/router_staff). Violations:\n" + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# Rule 4: no orphan namespaces — every prefix matches one of the three
# documented audiences (or the special-case identity ones).
# ---------------------------------------------------------------------------


_ALLOWED_PREFIX_ROOTS = (
    "/admin",
    "/webhooks",
    "/storefront",
    "/auth",
    "/profile",
    "/invitations",
    "/cart",
    "/favorites",
    "/orders",
    "/passports",
    "/payments",
    "/recipients",
    "/geo",
)


def test_every_router_prefix_uses_known_root() -> None:
    """No router should mount to a private namespace not listed above.

    Adding a new top-level prefix is a documentation event — extend
    ``_ALLOWED_PREFIX_ROOTS`` here AND update
    ``docs/api/router-restructure-2026-05.md`` in the same PR.
    """
    violations: list[str] = []
    for path, prefix in _collect_routers():
        if not any(prefix.startswith(root) for root in _ALLOWED_PREFIX_ROOTS):
            violations.append(f"{path.relative_to(path.parents[4])}: prefix={prefix!r}")
    assert not violations, (
        "Unknown URL namespace. Expected one of "
        f"{_ALLOWED_PREFIX_ROOTS}. Violations:\n" + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# Rule 5: at least one router per module is reachable through src/api/router.py
# ---------------------------------------------------------------------------


def test_aggregate_router_imports_every_module_router() -> None:
    """Each ``router_*.py`` file's exported symbol must be wired into the
    aggregate via its module's :class:`ModuleManifest` (REFACT-001 PR-5).

    Before PR-5 the aggregate `src/api/router.py` listed every router
    explicitly; after PR-5 it iterates ``src.bootstrap.modules.MODULES``
    and pulls each manifest's ``routers`` property. The contract here
    moves accordingly: a router file is "wired" iff its exported
    ``APIRouter`` instance is referenced by some manifest's
    ``customer_routers`` / ``admin_routers`` / ``webhook_routers``
    tuple. Catches dead routers that would otherwise silently 404.
    """
    import importlib

    from src.bootstrap.modules import MODULES

    aggregate_routers = {
        id(r)
        for manifest in MODULES
        for r in (
            *manifest.customer_routers,
            *manifest.admin_routers,
            *manifest.webhook_routers,
        )
    }

    missing: list[str] = []
    for path, _prefix in _collect_routers():
        text = path.read_text(encoding="utf-8")
        var_match = re.search(r"^(\w+)\s*=\s*APIRouter\(", text, flags=re.M)
        if var_match is None:
            continue
        var_name = var_match.group(1)
        # Build dotted module path from filesystem path, then import
        # and resolve the variable.
        rel = path.relative_to(path.parents[4])
        dotted = ".".join(rel.with_suffix("").parts)
        try:
            module = importlib.import_module(dotted)
        except Exception:  # pragma: no cover -- import-time errors
            missing.append(f"{rel}: failed to import module")
            continue
        router_obj = getattr(module, var_name, None)
        if router_obj is None:
            missing.append(f"{rel}: export {var_name!r} not found")
            continue
        if id(router_obj) not in aggregate_routers:
            missing.append(
                f"{rel}: export {var_name!r} is not wired into any "
                "ModuleManifest in src.bootstrap.modules.MODULES"
            )
    assert not missing, (
        "Every router must be wired into a ModuleManifest. Missing:\n"
        + "\n".join(missing)
    )


# ---------------------------------------------------------------------------
# Rule 6: every router with prefix `/admin/...` must carry RequireStaffRole
# as a router-level Depends, so customer accounts holding a permission
# codename that happens to be granted to staff (e.g. `logistics:read`)
# cannot reach `/api/v1/admin/...` URLs through the URL bypass.
# ---------------------------------------------------------------------------


def test_admin_routers_carry_require_staff_role_baseline() -> None:
    """Every `/admin/...` router needs ``RequireStaffRole`` at router level.

    Router-level — not per-endpoint — because the convention is set by
    URL prefix: a customer who somehow arrives at ``/admin/...`` should
    be rejected before per-endpoint permission checks fire, regardless
    of which permission codename they hold. Catches the regression where
    the documented baseline existed only in CLAUDE.md while the symbol
    itself did not.
    """
    import importlib

    from fastapi.params import Depends

    from src.modules.identity.presentation.dependencies import RequireStaffRole

    missing: list[str] = []
    for path, prefix in _collect_routers():
        if not prefix.startswith("/admin"):
            continue
        text = path.read_text(encoding="utf-8")
        var_match = re.search(r"^(\w+)\s*=\s*APIRouter\(", text, flags=re.M)
        if var_match is None:
            continue
        rel = path.relative_to(path.parents[4])
        dotted = ".".join(rel.with_suffix("").parts)
        try:
            module = importlib.import_module(dotted)
        except Exception:  # pragma: no cover -- import-time errors
            missing.append(f"{rel}: failed to import module")
            continue
        router = getattr(module, var_match.group(1), None)
        if router is None:
            continue
        guard_present = any(
            isinstance(dep, Depends) and dep.dependency is RequireStaffRole
            for dep in (router.dependencies or [])
        )
        if not guard_present:
            missing.append(
                f"{rel}: APIRouter(prefix={prefix!r}) missing "
                "router-level Depends(RequireStaffRole)"
            )
    assert not missing, (
        "Admin routers must include Depends(RequireStaffRole) at the "
        "router-level dependencies= argument. Missing:\n" + "\n".join(missing)
    )
