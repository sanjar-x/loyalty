"""ACL port contracts used by Order command handlers.

These ports decouple Order's application layer from the concrete
gateway adapters living in ``infrastructure/adapters/`` (which is the
only place allowed to import Logistics / Payment internals — see
``ALLOWED_CROSS_MODULE`` in tests/architecture).
"""

import uuid
from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime

from attrs import frozen

from src.modules.order.domain.value_objects import PickupPointPreference


@frozen
class PaymentTicket:
    intent_id: uuid.UUID
    client_secret: str | None


class IPaymentGateway(ABC):
    @abstractmethod
    async def authorize(
        self,
        *,
        order_id: uuid.UUID,
        identity_id: uuid.UUID,
        amount: int,
        currency: str,
        idempotency_key: str,
        provider: str,
    ) -> PaymentTicket: ...

    @abstractmethod
    async def capture(self, *, intent_id: uuid.UUID, idempotency_key: str) -> None: ...

    @abstractmethod
    async def refund(self, *, intent_id: uuid.UUID, idempotency_key: str) -> None: ...


class IDobroPostGateway(ABC):
    """ACL into logistics — DobroPost cross-border shipment booking."""

    @abstractmethod
    async def book_cross_border(
        self,
        *,
        order_id: uuid.UUID,
        identity_id: uuid.UUID,
        incoming_declaration: str,
        idempotency_key: str,
    ) -> uuid.UUID:
        """Book a DobroPost shipment and return its shipment_id."""

    @abstractmethod
    async def cancel_cross_border(
        self, *, shipment_id: uuid.UUID, idempotency_key: str
    ) -> None: ...

    @abstractmethod
    async def update_recipient(
        self,
        *,
        order_id: uuid.UUID,
        idempotency_key: str,
    ) -> None:
        """Push the order's current RecipientSnapshot to DobroPost.

        Used after ``RefreshRecipientSnapshotHandler`` succeeds: pulls
        the int-id from the side mapping and PUTs ``/api/shipment`` so
        the customs officer re-validates with corrected passport data.
        """


@frozen
class DobroPostShipmentMappingRecord:
    """Read projection of a DobroPost int-id ↔ UUID mapping row."""

    order_id: uuid.UUID
    shipment_uuid: uuid.UUID
    dp_shipment_id: int
    incoming_declaration: str
    dp_track_number: str | None
    last_status_id: int | None
    last_status_at: datetime | None


class IDobroPostShipmentMappingRepository(ABC):
    @abstractmethod
    async def add(
        self,
        *,
        order_id: uuid.UUID,
        shipment_uuid: uuid.UUID,
        dp_shipment_id: int,
        incoming_declaration: str,
        dp_track_number: str | None,
    ) -> None: ...

    @abstractmethod
    async def get_by_shipment_uuid(
        self, shipment_uuid: uuid.UUID
    ) -> DobroPostShipmentMappingRecord | None: ...

    @abstractmethod
    async def get_by_dp_shipment_id(
        self, dp_shipment_id: int
    ) -> DobroPostShipmentMappingRecord | None: ...

    @abstractmethod
    async def get_by_order_id(
        self, order_id: uuid.UUID
    ) -> DobroPostShipmentMappingRecord | None: ...

    @abstractmethod
    async def update_status(
        self,
        *,
        dp_shipment_id: int,
        last_status_id: int,
        dp_track_number: str | None = None,
    ) -> None: ...


class IRussianCarrierGateway(ABC):
    """ACL into logistics — russian carrier last-mile shipment booking."""

    @abstractmethod
    async def book_last_mile(
        self,
        *,
        order_id: uuid.UUID,
        cross_border_shipment_id: uuid.UUID,
        pickup_point: PickupPointPreference,
        idempotency_key: str,
    ) -> uuid.UUID:
        """Book a russian carrier shipment and return its shipment_id."""


class ITelegramChatLookup(ABC):
    """T-2 / D3.1 — read-side ACL into identity for Telegram chat resolution.

    Implemented as an anti-corruption adapter that reads
    ``linked_accounts`` directly (whitelisted in
    ``ALLOWED_CROSS_MODULE`` for the single adapter file). Returns the
    Telegram chat_id (an ``int`` per Bot API) for an identity that has
    a Telegram-linked account, or ``None`` if the customer signed up
    via email/OIDC without linking Telegram.
    """

    @abstractmethod
    async def get_chat_id(self, identity_id: uuid.UUID) -> int | None: ...


class ITelegramNotifier(ABC):
    """T-2 / D3.1 — outbound port for Telegram push notifications.

    The infrastructure adapter wraps the aiogram ``Bot.send_message``
    call. Implementations MUST swallow user-blocked-the-bot errors
    (HTTP 403) so a single bad recipient does not cause TaskIQ to
    retry indefinitely; transient failures (5xx, network) propagate
    so the broker's retry policy handles them.
    """

    @abstractmethod
    async def send_html(self, *, chat_id: int, html: str) -> None: ...


# ---------------------------------------------------------------------------
# Walk-in admin-create-order ports
# ---------------------------------------------------------------------------


@frozen
class CatalogSkuSnapshot:
    """Read-only projection of a SKU + parent metadata at order-creation time.

    ``selling_price`` is the ADR-005 autonomous-recompute output (already
    in customer currency). When ``None``, the SKU has not yet completed
    pricing recompute and is not orderable — the handler raises a 422.
    ``supplier_type`` comes from the parent ``Supplier`` row; ``LOCAL``
    is the safe fallback when the product has no supplier link
    (legacy / draft data).
    """

    sku_id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID
    product_name: str
    variant_label: str | None
    supplier_type: str  # value of shared.domain.SupplierType
    selling_price_amount: int | None
    currency: str
    is_active: bool


class ICatalogSkuPriceReader(ABC):
    """ACL port: walk-in handler reads SKU + price + parent metadata.

    Implementations join skus + products + product_variants +
    suppliers in a single query. Returning ``None`` for an unknown SKU
    lets the handler differentiate "user typo" (422) from a server
    error.
    """

    @abstractmethod
    async def get_many(
        self, sku_ids: Sequence[uuid.UUID], *, locale: str = "ru"
    ) -> dict[uuid.UUID, CatalogSkuSnapshot]:
        """Return a mapping from sku_id → snapshot for every found SKU."""


@frozen
class WalkInCustomerProfileInput:
    """Minimal customer data required to provision a walk-in identity.

    The provisioner writes both the Identity row (with
    ``primary_auth_method=WALK_IN``, ``is_active=True``) and the
    Customer row sharing the same primary key.
    """

    full_name: str
    phone: str
    email: str | None = None


@frozen
class WalkInIdentityProvisioned:
    identity_id: uuid.UUID


class IWalkInIdentityProvisioner(ABC):
    """ACL port: provision a fresh Identity + Customer for a walk-in order.

    Single shot: the provisioner does not deduplicate by phone/email
    (a walk-in is by definition a stranger; if the same person comes
    back tomorrow they'll get a second identity unless someone manually
    merges them — that's the deliberate, MVP-simple semantic).
    """

    @abstractmethod
    async def provision(
        self, profile: WalkInCustomerProfileInput
    ) -> WalkInIdentityProvisioned: ...


@frozen
class PriceOverrideAuditEntry:
    order_id: uuid.UUID
    order_item_id: uuid.UUID
    sku_id: uuid.UUID
    base_price_amount: int
    override_price_amount: int
    currency: str
    admin_id: uuid.UUID
    reason: str | None


class IPriceOverrideAuditWriter(ABC):
    """ACL port: persist one audit row per overridden walk-in line item.

    Writes happen in the same UoW commit as the Order rows, so the
    audit log can never disagree with what's in ``order_items``.
    """

    @abstractmethod
    async def write_many(self, entries: Sequence[PriceOverrideAuditEntry]) -> None: ...
