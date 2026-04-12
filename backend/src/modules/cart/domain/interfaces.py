"""
Cart domain interfaces (ports).

Defines abstract repository and cross-module service contracts.
The application layer depends only on these interfaces; concrete
implementations live in the infrastructure layer.
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from src.modules.cart.domain.entities import Cart
from src.modules.cart.domain.value_objects import (
    CheckoutAttemptInfo,
    CheckoutSnapshot,
    SkuSnapshot,
)


class ICartRepository(ABC):
    """Repository contract for the Cart aggregate."""

    @abstractmethod
    async def add(self, cart: Cart) -> Cart:
        """Persist a new cart and return it with any generated fields."""

    @abstractmethod
    async def get(self, cart_id: uuid.UUID) -> Cart | None:
        """Retrieve a cart by ID with eagerly loaded items."""

    @abstractmethod
    async def get_for_update(self, cart_id: uuid.UUID) -> Cart | None:
        """Retrieve a cart with pessimistic lock (SELECT FOR UPDATE)."""

    @abstractmethod
    async def get_active_by_identity(self, identity_id: uuid.UUID) -> Cart | None:
        """Find the active cart for an authenticated user."""

    @abstractmethod
    async def get_active_by_identity_for_update(
        self, identity_id: uuid.UUID
    ) -> Cart | None:
        """Find the active cart for an authenticated user with pessimistic lock."""

    @abstractmethod
    async def get_active_or_frozen_by_identity(
        self, identity_id: uuid.UUID
    ) -> Cart | None:
        """Find the active or frozen cart for an authenticated user."""

    @abstractmethod
    async def get_active_by_anonymous(self, anonymous_token: str) -> Cart | None:
        """Find the active cart for a guest user by anonymous token."""

    @abstractmethod
    async def update(self, cart: Cart) -> Cart:
        """Persist changes to an existing cart."""

    @abstractmethod
    async def save_checkout_snapshot(self, snapshot: CheckoutSnapshot) -> None:
        """Persist a checkout snapshot."""

    @abstractmethod
    async def update_checkout_snapshot(self, snapshot: CheckoutSnapshot) -> None:
        """Update an existing checkout snapshot in place."""

    @abstractmethod
    async def get_checkout_snapshot(
        self, snapshot_id: uuid.UUID
    ) -> CheckoutSnapshot | None:
        """Retrieve a checkout snapshot by ID."""

    @abstractmethod
    async def create_checkout_attempt(
        self,
        *,
        attempt_id: uuid.UUID,
        cart_id: uuid.UUID,
        snapshot_id: uuid.UUID,
    ) -> None:
        """Create a new pending checkout attempt."""

    @abstractmethod
    async def get_pending_checkout_attempt(
        self, cart_id: uuid.UUID
    ) -> CheckoutAttemptInfo | None:
        """Get the pending checkout attempt for a cart, if any."""

    @abstractmethod
    async def resolve_checkout_attempt(
        self,
        attempt_id: uuid.UUID,
        *,
        status: str,
        resolved_at: datetime,
    ) -> None:
        """Update a checkout attempt's status to a terminal state."""


class ISkuReadService(ABC):
    """Read-only cross-module query service for SKU data.

    Follows the ISupplierQueryService pattern from supplier module.
    """

    @abstractmethod
    async def get_sku_snapshot(self, sku_id: uuid.UUID) -> SkuSnapshot | None:
        """Get a single SKU snapshot, or None if not found."""

    @abstractmethod
    async def get_sku_snapshots_batch(
        self, sku_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, SkuSnapshot]:
        """Get multiple SKU snapshots in a single query.

        Returns a dict keyed by sku_id. Missing SKUs are omitted.
        """

    @abstractmethod
    async def check_skus_active(
        self, sku_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, bool]:
        """Check which SKUs are currently active."""


class IPickupPointReadService(ABC):
    """Cross-module query for pickup point validation."""

    @abstractmethod
    async def exists(self, pickup_point_id: uuid.UUID) -> bool:
        """Check whether a pickup point exists."""


class IOrderCreationService(ABC):
    """Port for synchronous in-process order creation at checkout."""

    @abstractmethod
    async def create_order_from_cart(
        self,
        cart_id: uuid.UUID,
        checkout_id: uuid.UUID,
        snapshot: CheckoutSnapshot,
    ) -> uuid.UUID:
        """Create an order from a confirmed checkout. Returns order_id."""
