"""Order domain ports."""

import uuid
from abc import ABC, abstractmethod
from datetime import date, datetime
from decimal import Decimal

from attrs import frozen

from src.modules.order.domain.entities import Order
from src.modules.order.domain.value_objects import OrderStatus, PickupPointPreference

# ---------------------------------------------------------------------------
# Cart ACL snapshot
# ---------------------------------------------------------------------------


@frozen
class CartCheckoutItemSnapshot:
    sku_id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID
    product_name: str
    variant_label: str | None
    supplier_type: str
    quantity: int
    unit_price_amount: int
    currency: str


@frozen
class CartCheckoutSnapshot:
    cart_id: uuid.UUID
    snapshot_id: uuid.UUID
    pickup_point: PickupPointPreference
    recipient_id: uuid.UUID
    total_amount: int
    currency: str
    cny_rate_at_checkout: Decimal | None
    items: tuple[CartCheckoutItemSnapshot, ...]


class ICartSnapshotReader(ABC):
    @abstractmethod
    async def get(
        self, *, cart_id: uuid.UUID, snapshot_id: uuid.UUID
    ) -> CartCheckoutSnapshot | None: ...


# ---------------------------------------------------------------------------
# Recipient ACL (order → recipient module)
# ---------------------------------------------------------------------------


@frozen
class RecipientLookupResult:
    """Read-only projection of a Recipient — used to fill RecipientSnapshot."""

    recipient_id: uuid.UUID
    identity_id: uuid.UUID
    full_name_ru: str
    full_name_lat: str
    phone: str
    email: str
    passport_serial: str
    passport_number: str
    passport_issue_date: date
    birth_date: date
    inn: str
    is_archived: bool


class IRecipientLookup(ABC):
    """ACL port: order reads recipient data through this single bridge."""

    @abstractmethod
    async def get(self, recipient_id: uuid.UUID) -> RecipientLookupResult | None: ...


# ---------------------------------------------------------------------------
# Order repository
# ---------------------------------------------------------------------------


class IOrderRepository(ABC):
    @abstractmethod
    async def add(self, order: Order) -> Order: ...

    @abstractmethod
    async def get(self, order_id: uuid.UUID) -> Order | None: ...

    @abstractmethod
    async def get_for_update(self, order_id: uuid.UUID) -> Order | None: ...

    @abstractmethod
    async def get_by_payment_intent(
        self, payment_intent_id: uuid.UUID
    ) -> Order | None: ...

    @abstractmethod
    async def get_by_incoming_declaration(self, declaration: str) -> Order | None: ...

    @abstractmethod
    async def get_by_cross_border_shipment(
        self, shipment_id: uuid.UUID
    ) -> Order | None: ...

    @abstractmethod
    async def get_by_last_mile_shipment(
        self, shipment_id: uuid.UUID
    ) -> Order | None: ...

    @abstractmethod
    async def update(self, order: Order) -> Order: ...

    @abstractmethod
    async def list_by_identity(
        self,
        identity_id: uuid.UUID,
        *,
        limit: int,
        cursor: datetime | None,
    ) -> list[Order]: ...

    @abstractmethod
    async def list_for_admin(
        self,
        *,
        statuses: list[OrderStatus] | None,
        limit: int,
        cursor: datetime | None,
    ) -> list[Order]: ...

    @abstractmethod
    async def find_stuck_in_cn(self, *, threshold: datetime) -> list[Order]:
        """Return orders in PROCURED whose last update is older than ``threshold``."""

    @abstractmethod
    async def find_hold_ttl_expired(self) -> list[Order]:
        """Return ON_HOLD orders whose ``hold_until`` is in the past."""

    @abstractmethod
    async def find_eligible_for_close(self, *, threshold: datetime) -> list[Order]:
        """Return DELIVERED orders updated more than ``threshold`` ago."""


# ---------------------------------------------------------------------------
# Idempotency + inbox
# ---------------------------------------------------------------------------


class IIdempotencyKeyStore(ABC):
    @abstractmethod
    async def reserve(
        self,
        *,
        key: str,
        identity_id: uuid.UUID,
        scope: str,
        expires_at: datetime,
    ) -> bool: ...

    @abstractmethod
    async def attach_result(
        self, *, key: str, scope: str, resource_id: uuid.UUID
    ) -> None: ...

    @abstractmethod
    async def get_result(self, *, key: str, scope: str) -> uuid.UUID | None: ...


class IInboxStore(ABC):
    """Per-consumer inbox (research (7) §6) — UNIQUE event_id deduplication."""

    @abstractmethod
    async def try_record(self, *, event_id: uuid.UUID, consumer: str) -> bool:
        """Insert (event_id, consumer) row. Returns False if already present."""


# ---------------------------------------------------------------------------
# State history writer (audit trail, research (2) §15.6)
# ---------------------------------------------------------------------------


@frozen
class HistoryActor:
    """Who triggered a state transition.

    ``actor_type`` is one of ``customer | manager | system | webhook``.
    """

    actor_type: str
    actor_id: str


class IOrderStateHistoryWriter(ABC):
    @abstractmethod
    async def append(
        self,
        *,
        order_id: uuid.UUID,
        from_status: OrderStatus | None,
        to_status: OrderStatus,
        event_type: str,
        event_id: uuid.UUID,
        actor: HistoryActor,
        metadata: dict | None,
        occurred_at: datetime,
    ) -> None: ...
