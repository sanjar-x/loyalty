"""Supplier aggregate root."""

import uuid
from datetime import UTC, datetime
from typing import Any, ClassVar

from attr import dataclass, field

from src.modules.supplier.domain.events import (
    SupplierActivatedEvent,
    SupplierCreatedEvent,
    SupplierDeactivatedEvent,
    SupplierUpdatedEvent,
)
from src.modules.supplier.domain.exceptions import (
    SupplierAlreadyActiveError,
    SupplierAlreadyInactiveError,
)
from src.modules.supplier.domain.value_objects import SupplierType
from src.shared.interfaces.entities import AggregateRoot


def _generate_id() -> uuid.UUID:
    return uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4()


_SUPPLIER_GUARDED_FIELDS: frozenset[str] = frozenset({"type"})


@dataclass
class Supplier(AggregateRoot):
    """Supplier aggregate root.

    Represents a product source — either a Chinese marketplace or a local
    regional supplier. Type is immutable after creation.

    Attributes:
        id: Unique supplier identifier (UUIDv7).
        name: Display name (max 255 chars).
        type: CROSS_BORDER or LOCAL (immutable).
        region: Geographic region (max 100 chars).
        is_active: Whether new products can reference this supplier.
        version: Optimistic locking counter.
    """

    id: uuid.UUID
    name: str
    type: SupplierType
    region: str
    is_active: bool = True
    version: int = 1
    created_at: datetime = field(factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(factory=lambda: datetime.now(UTC))

    _UPDATABLE_FIELDS: ClassVar[frozenset[str]] = frozenset({"name", "region"})

    def __setattr__(self, name: str, value: object) -> None:
        if name in _SUPPLIER_GUARDED_FIELDS and getattr(
            self, "_Supplier__initialized", False
        ):
            raise AttributeError(
                f"Cannot set '{name}' directly on Supplier. Type is immutable after creation."
            )
        super().__setattr__(name, value)

    def __attrs_post_init__(self) -> None:
        super().__attrs_post_init__()
        object.__setattr__(self, "_Supplier__initialized", True)

    @classmethod
    def create(
        cls,
        *,
        name: str,
        supplier_type: SupplierType,
        region: str,
        supplier_id: uuid.UUID | None = None,
        is_active: bool = True,
    ) -> Supplier:
        if not name or not name.strip():
            raise ValueError("Supplier name is required.")
        if not region or not region.strip():
            raise ValueError("Supplier region is required.")

        supplier = cls(
            id=supplier_id or _generate_id(),
            name=name.strip(),
            type=supplier_type,
            region=region.strip(),
            is_active=is_active,
        )
        supplier.add_domain_event(
            SupplierCreatedEvent(
                aggregate_id=str(supplier.id),
                supplier_name=supplier.name,
                supplier_type=supplier.type.value,
            )
        )
        return supplier

    def update(self, **kwargs: Any) -> None:
        unknown = kwargs.keys() - self._UPDATABLE_FIELDS
        if unknown:
            raise TypeError(
                f"update() got unexpected keyword argument(s): {', '.join(sorted(unknown))}"
            )

        if "name" in kwargs:
            name = kwargs["name"]
            if not name or not name.strip():
                raise ValueError("Supplier name is required.")
            self.name = name.strip()

        if "region" in kwargs:
            region = kwargs["region"]
            if not region or not region.strip():
                raise ValueError("Supplier region is required.")
            self.region = region.strip()

        self.updated_at = datetime.now(UTC)
        self.add_domain_event(SupplierUpdatedEvent(aggregate_id=str(self.id)))

    def deactivate(self) -> None:
        if not self.is_active:
            raise SupplierAlreadyInactiveError(self.id)
        self.is_active = False
        self.updated_at = datetime.now(UTC)
        self.add_domain_event(SupplierDeactivatedEvent(aggregate_id=str(self.id)))

    def activate(self) -> None:
        if self.is_active:
            raise SupplierAlreadyActiveError(self.id)
        self.is_active = True
        self.updated_at = datetime.now(UTC)
        self.add_domain_event(SupplierActivatedEvent(aggregate_id=str(self.id)))
