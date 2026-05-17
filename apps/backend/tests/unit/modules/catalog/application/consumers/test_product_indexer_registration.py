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

This test calls the real bootstrap helper and then asserts the relay's
event-handler registry actually carries the keys the indexer claims to
subscribe to. If someone removes the entry from ``task_modules`` (or
renames the bridge function without updating the registration list),
this test fails loudly.
"""

from __future__ import annotations

import pytest

from src.bootstrap.module_registry import import_task_modules
from src.bootstrap.modules import MODULES
from src.infrastructure.outbox.relay import _EVENT_HANDLERS

pytestmark = pytest.mark.unit


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


def test_product_indexer_event_handlers_registered() -> None:
    """All 14 indexer events present in the outbox relay registry."""
    import_task_modules(MODULES)

    missing = [
        event_type
        for event_type in _EXPECTED_EVENT_TYPES
        if event_type not in _EVENT_HANDLERS
    ]
    assert not missing, (
        f"ProductIndexer outbox bridges missing for: {missing}. "
        "Likely cause: ``src.modules.catalog.application.consumers.product_indexer`` "
        "is not listed in CATALOG_MODULE.task_modules, or the bridge "
        "functions were removed without updating the registration list."
    )
