"""Architecture fitness: ``Update*Command`` ↔ ``*UpdateRequest`` field parity.

Categorical defence against the bug class behind the "dead media branch"
in ``update_product.py``: a field declared on the command but never wired
into the corresponding request schema (or vice versa) sits unused, often
documented as live behaviour. The check below guarantees that for every
PATCH-style command in the catalog module the wire schema and the
application command expose the same field surface, modulo a small set of
system fields the router stitches in itself.

When this test fails, you have two honest options:

* the new field belongs in both → add it to whichever side is missing,
  or
* the new field belongs in only one → add it to ``_EXEMPT_*`` below
  with a one-line "why".
"""

from __future__ import annotations

from dataclasses import fields as dataclass_fields
from typing import Any

import pytest
from pydantic import BaseModel

from src.modules.catalog.application.commands.update_product import (
    UpdateProductCommand,
)
from src.modules.catalog.application.commands.update_sku import UpdateSKUCommand
from src.modules.catalog.application.commands.update_variant import UpdateVariantCommand
from src.modules.catalog.presentation.schemas import (
    ProductUpdateRequest,
    ProductVariantUpdateRequest,
    SKUUpdateRequest,
)

pytestmark = pytest.mark.architecture


# Server-stamped or routing-derived fields that legitimately exist on
# the command but never travel on the wire. Adding a name here is a
# conscious decision — the parity test will accept it.
_EXEMPT_COMMAND_FIELDS: dict[str, frozenset[str]] = {
    "UpdateProductCommand": frozenset(
        {
            "product_id",  # path param
            "_provided_fields",  # router-stitched (Pydantic ``model_fields_set``)
        }
    ),
    "UpdateSKUCommand": frozenset(
        {
            "product_id",  # path param
            "sku_id",  # path param
            "expected_version",  # If-Match header
            "_provided_fields",  # router-stitched
        }
    ),
    "UpdateVariantCommand": frozenset(
        {
            "product_id",  # path param
            "variant_id",  # path param
            "expected_version",  # If-Match header
            "_provided_fields",  # router-stitched
        }
    ),
}

# Schema-only fields (never reach the command). Keep empty unless there
# is a strong reason — most fields *should* round-trip.
_EXEMPT_SCHEMA_FIELDS: dict[str, frozenset[str]] = {
    "ProductUpdateRequest": frozenset(),
    "SKUUpdateRequest": frozenset(),
    "ProductVariantUpdateRequest": frozenset(),
}


_PAIRS: list[tuple[type[Any], type[BaseModel]]] = [
    (UpdateProductCommand, ProductUpdateRequest),
    (UpdateSKUCommand, SKUUpdateRequest),
    (UpdateVariantCommand, ProductVariantUpdateRequest),
]


@pytest.mark.parametrize(
    ("command_cls", "schema_cls"),
    _PAIRS,
    ids=[f"{c.__name__}↔{s.__name__}" for c, s in _PAIRS],
)
def test_update_command_and_request_schema_have_parity(
    command_cls: type[Any], schema_cls: type[BaseModel]
) -> None:
    """Field names on the command must match those on the request schema.

    The router uses ``build_update_command`` to bridge the two — any
    drift (field on one side only) either crashes at instantiation or,
    worse, silently ignores the field (the "dead media branch" failure
    mode that motivated this test).
    """
    command_fields = {f.name for f in dataclass_fields(command_cls)}
    schema_fields = set(schema_cls.model_fields)

    command_exempt = _EXEMPT_COMMAND_FIELDS.get(command_cls.__name__, frozenset())
    schema_exempt = _EXEMPT_SCHEMA_FIELDS.get(schema_cls.__name__, frozenset())

    command_visible = command_fields - command_exempt
    schema_visible = schema_fields - schema_exempt

    only_on_command = command_visible - schema_visible
    only_on_schema = schema_visible - command_visible

    assert not only_on_command and not only_on_schema, (
        f"{command_cls.__name__} and {schema_cls.__name__} drifted:\n"
        f"  only on command: {sorted(only_on_command) or '—'}\n"
        f"  only on schema : {sorted(only_on_schema) or '—'}\n"
        "Either align the two, or add the field to "
        "_EXEMPT_COMMAND_FIELDS / _EXEMPT_SCHEMA_FIELDS with a reason."
    )
