"""``SupplierTypeContextMapping`` aggregate (FRD §SupplierType→Context Mapping).

Maps a ``supplier_type`` identifier (e.g. ``"cross_border"``, ``"local"``) to a
default ``context_id`` used when resolving a product's pricing context.

The ``supplier_type`` is stored as a plain snake_case string — the enum of
valid values lives in the ``supplier`` bounded context and is outside this
aggregate's knowledge.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

import attrs

from src.modules.pricing.domain.events import (
    SupplierTypeContextMappingCreatedEvent,
    SupplierTypeContextMappingDeletedEvent,
    SupplierTypeContextMappingUpdatedEvent,
)
from src.modules.pricing.domain.exceptions import (
    SupplierTypeContextMappingValidationError,
)
from src.shared.interfaces.entities import AggregateRoot

_SUPPLIER_TYPE_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


def _validate_supplier_type(value: str) -> None:
    if not isinstance(value, str) or not _SUPPLIER_TYPE_RE.match(value):
        raise SupplierTypeContextMappingValidationError(
            message=(
                "supplier_type must be 1-64 snake_case characters "
                "matching ^[a-z][a-z0-9_]{0,63}$"
            ),
            details={"supplier_type": str(value)},
        )


@attrs.define(kw_only=True)
class SupplierTypeContextMapping(AggregateRoot):
    """Maps ``supplier_type → context_id``.

    ``supplier_type`` is immutable after creation (identity-like); only the
    target ``context_id`` can be changed via :meth:`change_context`.
    """

    id: uuid.UUID
    supplier_type: str
    context_id: uuid.UUID
    version_lock: int = 0
    created_at: datetime = attrs.field(factory=lambda: datetime.now(UTC))
    updated_at: datetime = attrs.field(factory=lambda: datetime.now(UTC))
    updated_by: uuid.UUID | None = None

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        supplier_type: str,
        context_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> SupplierTypeContextMapping:
        _validate_supplier_type(supplier_type)

        now = datetime.now(UTC)
        mapping = cls(
            id=uuid.uuid4(),
            supplier_type=supplier_type,
            context_id=context_id,
            version_lock=0,
            created_at=now,
            updated_at=now,
            updated_by=actor_id,
        )
        mapping.add_domain_event(
            SupplierTypeContextMappingCreatedEvent(
                mapping_id=mapping.id,
                supplier_type=mapping.supplier_type,
                context_id=mapping.context_id,
                updated_by=actor_id,
            )
        )
        return mapping

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def change_context(
        self,
        *,
        new_context_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        """Point the mapping at a different context. No-op when unchanged."""
        if new_context_id == self.context_id:
            return

        previous = self.context_id
        self.context_id = new_context_id
        self._touch(actor_id)
        self.add_domain_event(
            SupplierTypeContextMappingUpdatedEvent(
                mapping_id=self.id,
                supplier_type=self.supplier_type,
                context_id=self.context_id,
                previous_context_id=previous,
                updated_by=actor_id,
            )
        )

    def mark_deleted(self, *, actor_id: uuid.UUID) -> None:
        """Emit a deletion event. The caller performs the SQL DELETE."""
        self.add_domain_event(
            SupplierTypeContextMappingDeletedEvent(
                mapping_id=self.id,
                supplier_type=self.supplier_type,
                context_id=self.context_id,
                updated_by=actor_id,
            )
        )

    def _touch(self, actor_id: uuid.UUID) -> None:
        self.updated_at = datetime.now(UTC)
        self.updated_by = actor_id
        self.version_lock += 1
