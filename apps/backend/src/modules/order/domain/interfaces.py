"""Order domain ports."""

import uuid
from abc import ABC, abstractmethod
from datetime import date, datetime
from decimal import Decimal

from attrs import frozen

from src.modules.order.domain.entities import Order
from src.modules.order.domain.value_objects import OrderStatus, PickupPointPreference
from src.shared.domain.supplier_type import SupplierType

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
    supplier_type: SupplierType
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
    """Read-only projection of a Recipient (shipping coordinates only).

    Post-Sprint-1.5 Part 2 / ADR-011: customs PII moved to the
    ``passport`` bounded context — read via :class:`IPassportLookup`.
    """

    recipient_id: uuid.UUID
    identity_id: uuid.UUID
    full_name_ru: str
    full_name_lat: str
    phone: str
    email: str
    is_archived: bool


class IRecipientLookup(ABC):
    """ACL port: order reads recipient data through this single bridge."""

    @abstractmethod
    async def get(self, recipient_id: uuid.UUID) -> RecipientLookupResult | None: ...


# ---------------------------------------------------------------------------
# Passport ACL (order → passport module) — ADR-011 / Sprint 1.5 Part 2
# ---------------------------------------------------------------------------


@frozen
class PassportLookupResult:
    """Read-only projection of a Passport — used to populate PassportSnapshot.

    Passport and Recipient are independent bounded contexts (ADR-011).
    Order reads each through its own ACL adapter; the cross-border
    invariant in ``Order.create`` combines both at checkout time.
    """

    passport_id: uuid.UUID
    identity_id: uuid.UUID
    full_name_ru: str
    full_name_lat: str
    passport_serial: str
    passport_number: str
    passport_issue_date: date
    birth_date: date
    inn: str
    validation_status: str
    is_archived: bool


class IPassportLookup(ABC):
    """ACL port: order reads passport data through this single bridge.

    Ownership boundary is enforced by the handler comparing
    ``passport.identity_id == auth.identity_id``; same pattern as
    ``IRecipientLookup``. Implementation lives in
    ``order/infrastructure/adapters/passport_lookup.py`` (whitelisted
    in ``ALLOWED_CROSS_MODULE`` as ``("order","passport")``).
    """

    @abstractmethod
    async def get(self, passport_id: uuid.UUID) -> PassportLookupResult | None: ...


# ---------------------------------------------------------------------------
# Delivery quote ACL (order → logistics)
# ---------------------------------------------------------------------------


@frozen
class DeliveryQuoteLookupResult:
    """Read-only projection of a logistics ``DeliveryQuote``.

    Order needs only the priced amount + currency to populate
    ``Order.delivery_amount`` / ``Order.delivery_quote_id``. Provider-
    specific payload (offer_id, tariff_code, weight, …) stays inside
    the logistics module — the booking handler will pull it back
    through its own lookup at procurement time.

    ``identity_id`` (CR-2) lets the order command refuse a quote
    that belongs to a different customer. ``None`` for admin-side
    or legacy quotes that pre-date the ownership column — the
    command treats ``None`` as opt-out (no ownership check, same as
    before) so old quotes don't suddenly fail.
    """

    quote_id: uuid.UUID
    amount: int  # smallest currency unit (kopecks)
    currency: str  # ISO 4217
    expires_at: datetime | None
    identity_id: uuid.UUID | None


class IDeliveryQuoteLookup(ABC):
    """ACL port: order reads a delivery quote through this single bridge.

    Implementation lives in
    ``order.infrastructure.adapters.delivery_quote_adapter`` and reads
    ``logistics.delivery_quotes`` directly — same anti-corruption
    pattern as ``cart→catalog`` ``CatalogSkuAdapter``. Whitelisted in
    ``tests/architecture/test_boundaries.py``.
    """

    @abstractmethod
    async def get(self, quote_id: uuid.UUID) -> DeliveryQuoteLookupResult | None: ...


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
# Idempotency + inbox -- moved to shared kernel (REFACT-001 PR-3a + PR-3b).
# Order now consumes ``IIdempotencyStore`` and ``IInboxStore`` from
# ``src.shared.interfaces.idempotency``; the framework-shared
# ``IdempotencyProvider`` (registered in ``bootstrap.container``) wires
# the SqlIdempotencyStore / SqlInboxStore implementations.
# ---------------------------------------------------------------------------


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
