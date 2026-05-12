"""Supplier domain events for the Transactional Outbox.

Validation and ``aggregate_id`` auto-fill come from
:class:`src.shared.interfaces.entities.ModuleDomainEvent`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.shared.interfaces.entities import ModuleDomainEvent


@dataclass(frozen=True)
class SupplierEvent(ModuleDomainEvent, abstract=True):
    """Intermediate base for all supplier domain events."""

    aggregate_type: str = "Supplier"


@dataclass(frozen=True)
class SupplierCreatedEvent(
    SupplierEvent,
    required_fields=("supplier_id",),
    aggregate_id_field="supplier_id",
):
    """Emitted when a supplier is registered in the catalogue."""

    supplier_id: uuid.UUID | None = None
    supplier_name: str = ""
    supplier_type: str = ""
    country_code: str = ""
    event_type: str = "SupplierCreatedEvent"


@dataclass(frozen=True)
class SupplierUpdatedEvent(
    SupplierEvent,
    required_fields=("supplier_id",),
    aggregate_id_field="supplier_id",
):
    """Emitted when a supplier's mutable attributes change."""

    supplier_id: uuid.UUID | None = None
    event_type: str = "SupplierUpdatedEvent"


@dataclass(frozen=True)
class SupplierDeactivatedEvent(
    SupplierEvent,
    required_fields=("supplier_id",),
    aggregate_id_field="supplier_id",
):
    """Emitted when a supplier is taken offline (no new orders accepted)."""

    supplier_id: uuid.UUID | None = None
    event_type: str = "SupplierDeactivatedEvent"


@dataclass(frozen=True)
class SupplierActivatedEvent(
    SupplierEvent,
    required_fields=("supplier_id",),
    aggregate_id_field="supplier_id",
):
    """Emitted when a previously deactivated supplier is reactivated."""

    supplier_id: uuid.UUID | None = None
    event_type: str = "SupplierActivatedEvent"
