"""Supplier domain events for the Transactional Outbox."""

from dataclasses import dataclass

from src.shared.interfaces.entities import DomainEvent


@dataclass
class SupplierCreatedEvent(DomainEvent):
    aggregate_type: str = "Supplier"
    event_type: str = "supplier.created"
    supplier_name: str = ""
    supplier_type: str = ""
    country_code: str = ""


@dataclass
class SupplierUpdatedEvent(DomainEvent):
    aggregate_type: str = "Supplier"
    event_type: str = "supplier.updated"


@dataclass
class SupplierDeactivatedEvent(DomainEvent):
    aggregate_type: str = "Supplier"
    event_type: str = "supplier.deactivated"


@dataclass
class SupplierActivatedEvent(DomainEvent):
    aggregate_type: str = "Supplier"
    event_type: str = "supplier.activated"
