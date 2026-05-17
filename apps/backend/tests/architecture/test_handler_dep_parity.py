"""Architecture fitness: Create/Update handler dependency parity.

Categorical defence against the drift class behind PR D: catalog
``CreateProductHandler`` validated ``supplier_id`` via the published
``ISupplierDirectory`` port, ``UpdateProductHandler`` did not — and the
asymmetry only surfaced in production as a 500 on a bad supplier UUID.

For every ``(create_cls, update_cls)`` pair below, the parameter
annotations of ``update_cls.__init__`` MUST be a superset of the
annotations on ``create_cls.__init__`` (modulo the ``_EXEMPT`` set
which covers legitimate update-only deps like ``cache`` /
``If-Match`` plumbing).

To add or relax a pair, edit ``_PAIRS`` / ``_EXEMPT_ON_UPDATE``
with a one-line "why".
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from src.modules.catalog.application.commands.create_product import (
    CreateProductHandler,
)
from src.modules.catalog.application.commands.update_product import (
    UpdateProductHandler,
)

pytestmark = pytest.mark.architecture


_PAIRS: list[tuple[type[Any], type[Any]]] = [
    (CreateProductHandler, UpdateProductHandler),
]

# Create-side deps that are *expected* to have no update-side counterpart.
# Keyed by create-handler class name; values are dependency *type repr*
# strings (compared as ``repr(annotation)``) so the entry survives module
# rename or moves.
_EXEMPT_ON_CREATE: dict[str, frozenset[str]] = {
    "CreateProductHandler": frozenset(
        {
            # Media attachment on create flows through ``CreateProductCommand.media``;
            # editing media on an existing product uses the dedicated
            # ``/products/{id}/media/*`` handlers (UpdateProductMedia,
            # AddProductMedia, DeleteProductMedia). Keeping a media-repo
            # branch on ``UpdateProductHandler`` would re-introduce the
            # dead-code drift that PR ``756ae4d7`` removed.
            "<class 'src.modules.catalog.domain.interfaces.IMediaAssetRepository'>",
        }
    ),
}

# Update-side deps that are *expected* to have no create-side counterpart.
_EXEMPT_ON_UPDATE: dict[str, frozenset[str]] = {
    "UpdateProductHandler": frozenset(
        {
            # Update bumps the storefront generation counter after every
            # commit — create populates a fresh row that is invisible to
            # the storefront until publishing, so no cache invalidation.
            "cache",
        }
    ),
}


def _ctor_param_types(cls: type[Any]) -> dict[str, type[Any]]:
    """Map of ``__init__`` parameter name → annotated type (sans ``self``)."""
    sig = inspect.signature(cls.__init__)
    return {
        name: param.annotation
        for name, param in sig.parameters.items()
        if name != "self"
    }


@pytest.mark.parametrize(
    ("create_cls", "update_cls"),
    _PAIRS,
    ids=[f"{c.__name__}↔{u.__name__}" for c, u in _PAIRS],
)
def test_update_handler_carries_all_create_handler_deps(
    create_cls: type[Any], update_cls: type[Any]
) -> None:
    """Update handler MUST take every type the create handler does.

    Asymmetric deps usually mean validation that ran at create time
    silently stops running at update time (PR D class of bug). The
    test compares by annotated *type* rather than parameter name, so
    a renamed parameter still matches as long as the type is the same.
    """
    create_types = {repr(t) for t in _ctor_param_types(create_cls).values()}
    update_params = _ctor_param_types(update_cls)
    update_types = {repr(t) for t in update_params.values()}

    exempt_create = _EXEMPT_ON_CREATE.get(create_cls.__name__, frozenset())
    missing = (create_types - update_types) - exempt_create
    assert not missing, (
        f"{update_cls.__name__} is missing dependency types that "
        f"{create_cls.__name__} consumes: {sorted(missing)}. "
        "Either inject them on the update side, or list them in "
        f"``_EXEMPT_ON_CREATE['{create_cls.__name__}']`` with a "
        "one-line reason explaining why the validation is one-sided."
    )

    # Surfaces the reverse direction as informational only — extra deps
    # on update are normal (cache, ETag, optimistic locking). We only
    # fail the test if a name on the update side is NOT in _EXEMPT and
    # NOT also present on create — that would be a silent expansion of
    # update-only surface area worth flagging.
    exempt = _EXEMPT_ON_UPDATE.get(update_cls.__name__, frozenset())
    create_param_names = set(_ctor_param_types(create_cls))
    unexplained_extras = set(update_params) - create_param_names - exempt
    assert not unexplained_extras, (
        f"{update_cls.__name__} introduces parameter(s) "
        f"{sorted(unexplained_extras)} that are absent on "
        f"{create_cls.__name__}. Either add them to the create handler "
        f"or list them in ``_EXEMPT_ON_UPDATE['{update_cls.__name__}']`` "
        "with a one-line reason."
    )
