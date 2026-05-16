"""
Order domain value objects — Loyality cross-border dropship FSM.

Reference: backend/docs/Order/Research - Order (2) State Machine FSM.md §15.
"""

from __future__ import annotations

import enum
import re
import uuid
from datetime import datetime

from attrs import frozen

# ---------------------------------------------------------------------------
# Order FSM states
# ---------------------------------------------------------------------------


class OrderStatus(enum.StrEnum):
    """Loyality order lifecycle states (14 values).

    FSM transitions::

        PENDING ─PaymentCaptured─► PAID
                ─PaymentFailed─► CANCELLED
                ─CustomerCancel─► CANCELLED
        PAID ─ManagerProcured(track)─► PROCURED
             ─Cancel(reason)─► CANCELLED  (refund issued)
        PROCURED ─CrossBorderArrived(648/649)─► ARRIVED_IN_RU
                 ─PassportInvalid─► ON_HOLD
                 ─CustomsRejected/StuckInCN─► ON_HOLD
                 ─Cancel(reason)─► CANCELLED  (refund + recall)
        ON_HOLD ─Resume─► (previous state)
                ─TtlExpired/ManualCancel─► CANCELLED  (refund)
        ARRIVED_IN_RU ─LastMileCreated─► IN_LAST_MILE
        IN_LAST_MILE ─DeliveredToPickupPoint─► AWAITING_PICKUP
                     ─CarrierFailed─► RETURNING_TO_RU_WAREHOUSE
        AWAITING_PICKUP ─CustomerPickedUp─► DELIVERED
                        ─StorageExpired─► RETURNING_TO_RU_WAREHOUSE
                        ─CustomerRefused─► RETURNING_TO_RU_WAREHOUSE
        RETURNING_TO_RU_WAREHOUSE ─ReturnedToWarehouse─► NOT_DELIVERED
        DELIVERED ─ReturnRequested─► RETURN_IN_PROGRESS
                  ─ReturnPeriodElapsed(14d)─► CLOSED
        RETURN_IN_PROGRESS ─ReturnReceived─► RETURNED
        CLOSED, CANCELLED, NOT_DELIVERED, RETURNED — terminal
    """

    PENDING = "pending"
    PAID = "paid"
    PROCURED = "procured"
    ON_HOLD = "on_hold"
    ARRIVED_IN_RU = "arrived_in_ru"
    IN_LAST_MILE = "in_last_mile"
    AWAITING_PICKUP = "awaiting_pickup"
    DELIVERED = "delivered"
    RETURNING_TO_RU_WAREHOUSE = "returning_to_ru_warehouse"
    NOT_DELIVERED = "not_delivered"
    RETURN_IN_PROGRESS = "return_in_progress"
    RETURNED = "returned"
    CLOSED = "closed"
    CANCELLED = "cancelled"


TERMINAL_STATUSES: frozenset[OrderStatus] = frozenset(
    {
        OrderStatus.CLOSED,
        OrderStatus.CANCELLED,
        OrderStatus.NOT_DELIVERED,
        OrderStatus.RETURNED,
    }
)

PAID_STATUSES: frozenset[OrderStatus] = frozenset(
    {
        OrderStatus.PAID,
        OrderStatus.PROCURED,
        OrderStatus.ON_HOLD,
        OrderStatus.ARRIVED_IN_RU,
        OrderStatus.IN_LAST_MILE,
        OrderStatus.AWAITING_PICKUP,
        OrderStatus.DELIVERED,
        OrderStatus.RETURNING_TO_RU_WAREHOUSE,
        OrderStatus.RETURN_IN_PROGRESS,
    }
)


# ---------------------------------------------------------------------------
# Cancellation taxonomy (research (8) §6.2)
# ---------------------------------------------------------------------------


class CancellationCategory(enum.StrEnum):
    """Top-level cancellation taxonomy."""

    CUSTOMER = "customer"
    MERCHANT = "merchant"
    SYSTEM = "system"
    LOGISTICS = "logistics"


class CancellationReason(enum.StrEnum):
    """Specific cancellation reason codes (taxonomized enum)."""

    # CUSTOMER-initiated
    CUSTOMER_CHANGED_MIND = "customer_changed_mind"
    CUSTOMER_FOUND_BETTER_PRICE = "customer_found_better_price"
    CUSTOMER_WRONG_ITEM = "customer_wrong_item"
    CUSTOMER_DELIVERY_TOO_SLOW = "customer_delivery_too_slow"
    CUSTOMER_DUPLICATE_ORDER = "customer_duplicate_order"

    # MERCHANT-initiated
    MERCHANT_OUT_OF_STOCK = "merchant_out_of_stock"
    MERCHANT_PRICE_ERROR = "merchant_price_error"
    MERCHANT_FRAUD_SUSPECTED = "merchant_fraud_suspected"
    MERCHANT_REGION_NOT_SERVED = "merchant_region_not_served"
    MERCHANT_ITEM_DISCONTINUED = "merchant_item_discontinued"
    MERCHANT_FORCE_CANCEL = "merchant_force_cancel"

    # SYSTEM-initiated
    SYSTEM_PAYMENT_FAILED = "system_payment_failed"
    SYSTEM_PAYMENT_TIMEOUT = "system_payment_timeout"
    SYSTEM_AUTH_EXPIRED = "system_auth_expired"
    SYSTEM_HOLD_TTL_EXPIRED = "system_hold_ttl_expired"

    # LOGISTICS-initiated
    LOGISTICS_CUSTOMS_REJECTED = "logistics_customs_rejected"
    LOGISTICS_LOST_IN_TRANSIT = "logistics_lost_in_transit"
    LOGISTICS_UNDELIVERABLE_ADDRESS = "logistics_undeliverable_address"
    LOGISTICS_PASSPORT_INVALID = "logistics_passport_invalid"


_CATEGORY_BY_REASON: dict[CancellationReason, CancellationCategory] = {
    CancellationReason.CUSTOMER_CHANGED_MIND: CancellationCategory.CUSTOMER,
    CancellationReason.CUSTOMER_FOUND_BETTER_PRICE: CancellationCategory.CUSTOMER,
    CancellationReason.CUSTOMER_WRONG_ITEM: CancellationCategory.CUSTOMER,
    CancellationReason.CUSTOMER_DELIVERY_TOO_SLOW: CancellationCategory.CUSTOMER,
    CancellationReason.CUSTOMER_DUPLICATE_ORDER: CancellationCategory.CUSTOMER,
    CancellationReason.MERCHANT_OUT_OF_STOCK: CancellationCategory.MERCHANT,
    CancellationReason.MERCHANT_PRICE_ERROR: CancellationCategory.MERCHANT,
    CancellationReason.MERCHANT_FRAUD_SUSPECTED: CancellationCategory.MERCHANT,
    CancellationReason.MERCHANT_REGION_NOT_SERVED: CancellationCategory.MERCHANT,
    CancellationReason.MERCHANT_ITEM_DISCONTINUED: CancellationCategory.MERCHANT,
    CancellationReason.MERCHANT_FORCE_CANCEL: CancellationCategory.MERCHANT,
    CancellationReason.SYSTEM_PAYMENT_FAILED: CancellationCategory.SYSTEM,
    CancellationReason.SYSTEM_PAYMENT_TIMEOUT: CancellationCategory.SYSTEM,
    CancellationReason.SYSTEM_AUTH_EXPIRED: CancellationCategory.SYSTEM,
    CancellationReason.SYSTEM_HOLD_TTL_EXPIRED: CancellationCategory.SYSTEM,
    CancellationReason.LOGISTICS_CUSTOMS_REJECTED: CancellationCategory.LOGISTICS,
    CancellationReason.LOGISTICS_LOST_IN_TRANSIT: CancellationCategory.LOGISTICS,
    CancellationReason.LOGISTICS_UNDELIVERABLE_ADDRESS: CancellationCategory.LOGISTICS,
    CancellationReason.LOGISTICS_PASSPORT_INVALID: CancellationCategory.LOGISTICS,
}


def category_of(reason: CancellationReason) -> CancellationCategory:
    return _CATEGORY_BY_REASON[reason]


# ---------------------------------------------------------------------------
# Hold reasons (research (2) §15.5)
# ---------------------------------------------------------------------------


class HoldReason(enum.StrEnum):
    PASSPORT_INVALID = "passport_invalid"
    CUSTOMS_REJECTED = "customs_rejected"
    STUCK_IN_CN = "stuck_in_cn"
    MANUAL_REVIEW = "manual_review"
    BOOKING_FAILED = "booking_failed"
    """ORD-006 (D1.2) — async DobroPost booking exhausted retries.
    Order goes ON_HOLD with this reason instead of staying stuck in
    PROCURED with no shipment. Manager triages from the admin
    dashboard; resume via :class:`ResumeOrderHandler` after the
    DobroPost outage clears."""


# ---------------------------------------------------------------------------
# Customer-facing status (research (2) §15.8)
# ---------------------------------------------------------------------------


class CustomerFacingStatus(enum.StrEnum):
    """Укрупнённые статусы для UI customer'а — не raw status_id."""

    AWAITING_PAYMENT = "awaiting_payment"  # PENDING
    PROCESSING = "processing"  # PAID — менеджер выкупает
    SHIPPED_FROM_CHINA = "shipped_from_china"  # PROCURED — едет в РФ
    AT_RU_CUSTOMS_HOLD = "at_ru_customs_hold"  # ON_HOLD (passport/customs)
    IN_RU_DELIVERY = "in_ru_delivery"  # ARRIVED_IN_RU, IN_LAST_MILE
    READY_FOR_PICKUP = "ready_for_pickup"  # AWAITING_PICKUP
    DELIVERED = "delivered"  # DELIVERED, CLOSED
    RETURNING = "returning"  # RETURNING_TO_RU_WAREHOUSE, RETURN_IN_PROGRESS
    NOT_DELIVERED = "not_delivered"  # NOT_DELIVERED, RETURNED
    CANCELLED = "cancelled"  # CANCELLED


_CUSTOMER_FACING_MAP: dict[OrderStatus, CustomerFacingStatus] = {
    OrderStatus.PENDING: CustomerFacingStatus.AWAITING_PAYMENT,
    OrderStatus.PAID: CustomerFacingStatus.PROCESSING,
    OrderStatus.PROCURED: CustomerFacingStatus.SHIPPED_FROM_CHINA,
    OrderStatus.ON_HOLD: CustomerFacingStatus.AT_RU_CUSTOMS_HOLD,
    OrderStatus.ARRIVED_IN_RU: CustomerFacingStatus.IN_RU_DELIVERY,
    OrderStatus.IN_LAST_MILE: CustomerFacingStatus.IN_RU_DELIVERY,
    OrderStatus.AWAITING_PICKUP: CustomerFacingStatus.READY_FOR_PICKUP,
    OrderStatus.DELIVERED: CustomerFacingStatus.DELIVERED,
    OrderStatus.CLOSED: CustomerFacingStatus.DELIVERED,
    OrderStatus.RETURNING_TO_RU_WAREHOUSE: CustomerFacingStatus.RETURNING,
    OrderStatus.RETURN_IN_PROGRESS: CustomerFacingStatus.RETURNING,
    OrderStatus.NOT_DELIVERED: CustomerFacingStatus.NOT_DELIVERED,
    OrderStatus.RETURNED: CustomerFacingStatus.NOT_DELIVERED,
    OrderStatus.CANCELLED: CustomerFacingStatus.CANCELLED,
}


def to_customer_facing(status: OrderStatus) -> CustomerFacingStatus:
    return _CUSTOMER_FACING_MAP[status]


# ---------------------------------------------------------------------------
# Incoming declaration (китайский трек, research (6) §10.3)
# ---------------------------------------------------------------------------

_INCOMING_DECLARATION_PATTERN = re.compile(r"^[A-Za-z0-9\-]{1,15}$")


@frozen
class IncomingDeclaration:
    """Chinese tracking number — DobroPost ``incomingDeclaration``.

    Constraints (research (6) §10.3): <16 chars, alphanumeric.
    """

    value: str

    @classmethod
    def parse(cls, raw: str) -> IncomingDeclaration:
        normalized = (raw or "").strip()
        if not _INCOMING_DECLARATION_PATTERN.match(normalized):
            raise ValueError(
                "Incoming declaration must be 1-15 alphanumeric characters"
            )
        return cls(value=normalized)


# ---------------------------------------------------------------------------
# Order number (display id)
# ---------------------------------------------------------------------------


@frozen
class OrderNumber:
    """Deterministic human-readable order id ``LOY-YYYYMMDD-XXXXXX``."""

    value: str

    @classmethod
    def from_id(cls, order_id: uuid.UUID, created_at: datetime) -> OrderNumber:
        return cls(
            value=f"LOY-{created_at.strftime('%Y%m%d')}-{order_id.hex[-6:].upper()}"
        )


# ---------------------------------------------------------------------------
# Pickup point preference (research (2) §15.6)
# ---------------------------------------------------------------------------


class PickupCarrier(enum.StrEnum):
    CDEK = "cdek"
    YANDEX = "yandex"
    BOXBERRY = "boxberry"
    POCHTA = "pochta"


@frozen
class PickupPointPreference:
    carrier: PickupCarrier
    point_id: str


# ---------------------------------------------------------------------------
# Offline payment receipt (walk-in admin-created orders)
# ---------------------------------------------------------------------------


class OfflinePaymentMethod(enum.StrEnum):
    """How a walk-in customer paid the admin offline.

    The provider-side PaymentIntent is intentionally NOT created — the
    admin asserts payment was received out-of-band. ``reference`` carries
    whatever external document anchors the fact (receipt number, bank
    transfer id, internal POS ticket).
    """

    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    CARD_TERMINAL = "card_terminal"
    OTHER = "other"


@frozen
class OfflinePaymentReceipt:
    """Frozen marker of an offline payment captured by admin.

    ``reference`` is required so the audit trail can be reconciled
    against external documents. ``paid_at`` defaults to creation time
    only when not supplied by the admin (e.g. POS scenario where the
    money changed hands seconds ago).
    """

    method: OfflinePaymentMethod
    reference: str
    paid_at: datetime

    def __attrs_post_init__(self) -> None:
        if not self.reference.strip():
            raise ValueError(
                "OfflinePaymentReceipt.reference must be non-empty — "
                "admin must anchor the payment to an external document."
            )
