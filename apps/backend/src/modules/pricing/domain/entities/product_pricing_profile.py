"""Pricing aggregates.

Currently defines ``ProductPricingProfile`` — the owner of scope=product_input
variable values for a single product (see [[ADR-004]]).

Deliberately light on cross-aggregate invariants in this slice:
- ``values`` is stored as an opaque ``dict[str, Decimal]`` keyed by variable
  code. Code-level required/optional validation against the ``Variable``
  registry lives in a later slice (the registry doesn't exist yet).
- ``context_id`` is accepted as an opaque UUID; resolution via supplier/
  category projections is handled in a later slice.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import attrs

from src.modules.pricing.domain.events import (
    ProductPricingProfileCreatedEvent,
    ProductPricingProfileDeletedEvent,
    ProductPricingProfileUpdatedEvent,
)
from src.modules.pricing.domain.exceptions import PricingProfileValidationError
from src.modules.pricing.domain.value_objects import ProfileStatus
from src.shared.interfaces.entities import AggregateRoot

_VARIABLE_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


def _validate_values(values: dict[str, Decimal]) -> None:
    """Shape-only validation of a values map.

    Domain-level invariants:
    - Each key matches ``[a-z][a-z0-9_]{0,63}`` (variable-code convention).
    - Each value is a ``Decimal`` and finite.

    Semantic validation (is this variable required for this category? does
    unit match?) is the responsibility of a future slice that has access to
    the ``Variable`` registry.
    """
    for code, value in values.items():
        if not isinstance(code, str) or not _VARIABLE_CODE_RE.fullmatch(code):
            raise PricingProfileValidationError(
                message=f"Invalid variable code: {code!r}",
                error_code="PRICING_PROFILE_INVALID_VARIABLE_CODE",
                details={"code": code},
            )
        if not isinstance(value, Decimal):
            raise PricingProfileValidationError(
                message=(
                    f"Value for {code!r} must be a Decimal, got {type(value).__name__}"
                ),
                error_code="PRICING_PROFILE_INVALID_VALUE_TYPE",
                details={"code": code, "type": type(value).__name__},
            )
        if not value.is_finite():
            raise PricingProfileValidationError(
                message=f"Value for {code!r} must be finite",
                error_code="PRICING_PROFILE_NON_FINITE_VALUE",
                details={"code": code},
            )


@attrs.define(kw_only=True)
class ProductPricingProfile(AggregateRoot):
    """Pricing inputs for a single catalog product (ADR-004).

    Attributes:
        id: Profile UUID.
        product_id: Soft reference to ``catalog.Product.id`` (unique).
        context_id: Optional resolved pricing context UUID.
        values: Map of ``variable_code -> Decimal`` with the product's
            ``scope=product_input`` values (e.g. ``purchase_price_cny``).
        status: Lifecycle status (see :class:`ProfileStatus`).
        version_lock: Optimistic-locking counter; bumped on every write.
        created_at: Creation timestamp (UTC).
        updated_at: Last modification timestamp (UTC).
        updated_by: Identity ID of the last actor.
        is_deleted: Soft-delete marker (history is preserved).
    """

    id: uuid.UUID
    product_id: uuid.UUID
    context_id: uuid.UUID | None = None
    values: dict[str, Decimal] = attrs.field(factory=dict)
    status: ProfileStatus = ProfileStatus.DRAFT
    version_lock: int = 0
    created_at: datetime = attrs.field(factory=lambda: datetime.now(UTC))
    updated_at: datetime = attrs.field(factory=lambda: datetime.now(UTC))
    updated_by: uuid.UUID | None = None
    is_deleted: bool = False

    # ------------------------------------------------------------------
    # Factory / mutators
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        product_id: uuid.UUID,
        values: dict[str, Decimal],
        actor_id: uuid.UUID,
        context_id: uuid.UUID | None = None,
        status: ProfileStatus = ProfileStatus.DRAFT,
    ) -> ProductPricingProfile:
        """Instantiate a new profile and emit a ``Created`` event."""
        _validate_values(values)
        now = datetime.now(UTC)
        profile = cls(
            id=uuid.uuid4(),
            product_id=product_id,
            context_id=context_id,
            values=dict(values),
            status=status,
            version_lock=0,
            created_at=now,
            updated_at=now,
            updated_by=actor_id,
            is_deleted=False,
        )
        profile.add_domain_event(
            ProductPricingProfileCreatedEvent(
                profile_id=profile.id,
                product_id=profile.product_id,
                context_id=profile.context_id,
                status=profile.status.value,
                values=_values_to_str(profile.values),
                updated_by=actor_id,
            )
        )
        return profile

    def update_values(
        self,
        *,
        values: dict[str, Decimal],
        actor_id: uuid.UUID,
        status: ProfileStatus | None = None,
        context_id: uuid.UUID | None = None,
        context_id_provided: bool = False,
    ) -> None:
        """Replace the values map and optionally the status / context.

        ``context_id_provided=True`` is required to distinguish "caller wants
        to clear context_id" (``None``) from "caller didn't touch it".
        """
        _validate_values(values)
        self.values = dict(values)
        if status is not None:
            self.status = status
        if context_id_provided:
            self.context_id = context_id
        self.updated_by = actor_id
        self.updated_at = datetime.now(UTC)
        self.version_lock += 1
        self.add_domain_event(
            ProductPricingProfileUpdatedEvent(
                profile_id=self.id,
                product_id=self.product_id,
                context_id=self.context_id,
                status=self.status.value,
                values=_values_to_str(self.values),
                updated_by=actor_id,
            )
        )

    def mark_stale(self, actor_id: uuid.UUID | None = None) -> None:
        """Mark the profile stale (e.g. on category/supplier change)."""
        if self.status == ProfileStatus.STALE:
            return
        self.status = ProfileStatus.STALE
        self.updated_at = datetime.now(UTC)
        if actor_id is not None:
            self.updated_by = actor_id
        self.version_lock += 1
        self.add_domain_event(
            ProductPricingProfileUpdatedEvent(
                profile_id=self.id,
                product_id=self.product_id,
                context_id=self.context_id,
                status=self.status.value,
                values=_values_to_str(self.values),
                updated_by=actor_id,
            )
        )

    def soft_delete(self, actor_id: uuid.UUID | None = None) -> None:
        """Flip the soft-delete flag and emit a ``Deleted`` event."""
        if self.is_deleted:
            return
        self.is_deleted = True
        self.updated_at = datetime.now(UTC)
        if actor_id is not None:
            self.updated_by = actor_id
        self.version_lock += 1
        self.add_domain_event(
            ProductPricingProfileDeletedEvent(
                profile_id=self.id,
                product_id=self.product_id,
            )
        )


def _values_to_str(values: dict[str, Decimal]) -> dict[str, str]:
    """Serialize a Decimal map for event payloads (JSON-safe, lossless)."""
    return {code: format(value, "f") for code, value in values.items()}


__all__ = ["ProductPricingProfile"]
