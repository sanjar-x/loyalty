"""Guard test: the ProductIndexer's outbox handlers must be registered.

This test exists because Phase 2.6/2.7 of the ES integration shipped
once already with ``catalog/module.py:task_modules`` missing the
``product_indexer`` entry — the consumer code existed, the TaskIQ
decorators existed, the outbox bridge functions existed, but
``import_task_modules`` never touched the file at bootstrap, so the
module-level ``@broker.task`` decorators and the 14
``register_event_handler(...)`` calls were never executed. Result:
every Product / SKU / Variant / Media / Brand / Category event went
into the outbox, the relay marked them ``unknown event_type``, and ES
silently fell behind PG with no alarm.

Two checks:

1. ``test_product_indexer_listed_in_catalog_task_modules`` — pure
   manifest assertion; does not trigger any registrations, so it
   cannot perturb the shared ``_EVENT_HANDLERS`` state that the
   identity / supplier dual-registration tests pin separately.
2. ``test_product_indexer_event_handlers_registered`` — imports the
   indexer module directly (not via ``import_task_modules`` on the
   full MODULES tuple) and asserts every expected event_type is
   bound. Isolated to the catalog file so the test cannot collide
   with other modules' registrations.
"""

from __future__ import annotations

import importlib

import pytest

from src.bootstrap.modules import MODULES
from src.infrastructure.outbox.relay import _EVENT_HANDLERS

pytestmark = pytest.mark.unit

_INDEXER_MODULE = "src.modules.catalog.application.consumers.product_indexer"

_EXPECTED_EVENT_TYPES: tuple[str, ...] = (
    # Product lifecycle
    "ProductCreatedEvent",
    "ProductStatusChangedEvent",
    "ProductUpdatedEvent",
    "ProductDeletedEvent",
    # SKU lifecycle (denormalised price / in_stock / sku_count)
    "SKUAddedEvent",
    "SKUDeletedEvent",
    "SKUPricedEvent",
    "SKUPricingFailedEvent",
    # Variant / media (denormalised variant_count / image_url / titles)
    "VariantAddedEvent",
    "VariantDeletedEvent",
    "MediaAssetAttachedEvent",
    "MediaAssetDetachedEvent",
    # Brand / Category rename fan-out
    "BrandUpdatedEvent",
    "CategoryUpdatedEvent",
)


def test_product_indexer_listed_in_catalog_task_modules() -> None:
    """``CATALOG_MODULE.task_modules`` must reference the indexer module.

    Pure manifest check — does not import the module, so cannot
    pollute the global ``_EVENT_HANDLERS`` dict.
    """
    catalog_manifest = next(m for m in MODULES if m.name == "catalog")
    assert _INDEXER_MODULE in catalog_manifest.task_modules, (
        f"{_INDEXER_MODULE!r} missing from CATALOG_MODULE.task_modules — "
        "runtime bootstrap will skip the file, no @broker.task / "
        "register_event_handler() side-effects will fire, and the ES "
        "indexer pipeline silently dies."
    )


def test_product_indexer_event_handlers_registered() -> None:
    """All expected event_types resolved in the outbox relay registry.

    Imports ONLY the indexer module (not the full MODULES manifest)
    to avoid perturbing the dual-registration state of other modules
    (identity / supplier) — those have their own pinned tests in
    ``tests/unit/infrastructure/outbox/test_dual_registration.py``.
    """
    importlib.import_module(_INDEXER_MODULE)

    missing = [
        event_type
        for event_type in _EXPECTED_EVENT_TYPES
        if event_type not in _EVENT_HANDLERS
    ]
    assert not missing, (
        f"ProductIndexer outbox bridges missing for: {missing}. "
        "Likely cause: the bridge functions were removed without "
        f"updating the registration list at the bottom of {_INDEXER_MODULE}."
    )
