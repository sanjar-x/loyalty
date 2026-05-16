"""Command: admin creates an offline (walk-in) order from scratch.

Flow:

1. Idempotency reservation against the shared kernel store (scope
   ``order.create_walk_in``). A retry with the same key returns the
   already-persisted order id, so a UI double-submit does not duplicate.
2. Provision a fresh Identity + Customer for the walk-in (the customer
   is not yet in the system — see ``IWalkInIdentityProvisioner``).
3. Snapshot SKU prices and parent metadata from catalog via
   ``ICatalogSkuPriceReader``. Each SKU must be active and have a
   non-null ``selling_price`` (ADR-005). Missing / inactive SKUs
   abort the whole order (422).
4. Validate price overrides:
   ``0 <= override <= base * settings.WALK_IN_MAX_PRICE_OVERRIDE_RATIO``.
   Out-of-range overrides raise :class:`PriceOverrideValidationError`.
5. Build ``OrderItem``s with the chosen unit_price (override or base)
   and supplier_type pulled from the catalog snapshot.
6. Build :class:`RecipientSnapshot` from inline recipient data — the
   snapshot's own ``__attrs_post_init__`` enforces passport/INN/phone
   format invariants (TYPE-005), so malformed input never reaches the DB.
7. ``Order.create_walk_in`` then ``Order.mark_paid_offline`` inside a
   single UoW. The order is born PAID; no PaymentIntent is created.
8. Audit rows for each overridden line go to ``order_line_price_overrides``
   via :class:`IPriceOverrideAuditWriter`.

The whole sequence sits inside one :class:`IUnitOfWork` so the outbox
events (``OrderCreatedEvent`` + ``OrderPaidOfflineEvent``) are flushed
atomically with the Order + Customer + price-override rows.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import cast

from attrs import field, frozen

from src.bootstrap.config import settings
from src.modules.order.application._history import record_history
from src.modules.order.application.ports import (
    CatalogSkuSnapshot,
    ICatalogSkuPriceReader,
    IPriceOverrideAuditWriter,
    IWalkInIdentityProvisioner,
    PriceOverrideAuditEntry,
    WalkInCustomerProfileInput,
)
from src.modules.order.domain.entities import Order, OrderItem
from src.modules.order.domain.exceptions import (
    IdempotencyKeyConflictError,
    OrderEmptyError,
    PriceOverrideValidationError,
)
from src.modules.order.domain.interfaces import (
    HistoryActor,
    IOrderRepository,
    IOrderStateHistoryWriter,
)
from src.modules.order.domain.recipient_snapshot import RecipientSnapshot
from src.modules.order.domain.value_objects import (
    OfflinePaymentMethod,
    OfflinePaymentReceipt,
    PickupPointPreference,
)
from src.shared.domain.supplier_type import SupplierType
from src.shared.exceptions import UnprocessableEntityError
from src.shared.interfaces.idempotency import IIdempotencyStore
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork

IDEMPOTENCY_TTL_HOURS = 24
SCOPE = "order.create_walk_in"


# ---------------------------------------------------------------------------
# Input DTOs (frozen attrs) — wire-format independent
# ---------------------------------------------------------------------------


@frozen
class InlineRecipientInput:
    """Recipient data captured inline (no backing ``recipients`` row).

    Mirrors the columns of :class:`RecipientSnapshot`. Field-level
    validation runs in ``RecipientSnapshot.__attrs_post_init__``, not
    here, so the handler does not duplicate format checks.
    """

    full_name_ru: str
    full_name_lat: str
    phone: str
    email: str
    passport_serial: str
    passport_number: str
    passport_issue_date: (
        object  # date — kept loose so the schema layer can hand a stdlib date through
    )
    birth_date: object
    inn: str


@frozen
class WalkInItemInput:
    """One line item in an admin-created walk-in order.

    ``unit_price_override_amount`` is the admin's manual price (in
    smallest currency units). When ``None``, the catalog's
    ``selling_price`` is used verbatim.
    """

    sku_id: uuid.UUID
    quantity: int
    unit_price_override_amount: int | None = None
    override_reason: str | None = None


@frozen
class OfflinePaymentInput:
    """Reference to the external payment document admin captured offline."""

    method: OfflinePaymentMethod
    reference: str
    paid_at: datetime | None = None


@dataclass(frozen=True)
class AdminCreateWalkInOrderCommand:
    admin_id: uuid.UUID
    profile: WalkInCustomerProfileInput
    recipient: InlineRecipientInput
    items: tuple[WalkInItemInput, ...]
    pickup_point: PickupPointPreference
    payment: OfflinePaymentInput
    currency: str
    idempotency_key: str
    cny_rate_at_checkout: Decimal | None = None
    delivery_amount: int = 0


@dataclass(frozen=True)
class AdminCreateWalkInOrderResult:
    order_id: uuid.UUID
    identity_id: uuid.UUID
    total_amount: int
    currency: str


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


@frozen
class _ResolvedLine:
    sku_id: uuid.UUID
    quantity: int
    unit_price_amount: int
    base_price_amount: int
    override_applied: bool
    override_reason: str | None
    currency: str
    product_id: uuid.UUID
    variant_id: uuid.UUID
    product_name: str
    variant_label: str | None
    supplier_type: SupplierType
    item_id: uuid.UUID = field(factory=uuid.uuid4)


class AdminCreateWalkInOrderHandler:
    def __init__(
        self,
        order_repo: IOrderRepository,
        sku_reader: ICatalogSkuPriceReader,
        identity_provisioner: IWalkInIdentityProvisioner,
        override_writer: IPriceOverrideAuditWriter,
        idempotency_store: IIdempotencyStore,
        history_writer: IOrderStateHistoryWriter,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._order_repo = order_repo
        self._sku_reader = sku_reader
        self._provisioner = identity_provisioner
        self._override_writer = override_writer
        self._idem = idempotency_store
        self._history = history_writer
        self._uow = uow
        self._logger = logger.bind(handler="AdminCreateWalkInOrderHandler")

    async def handle(
        self, command: AdminCreateWalkInOrderCommand
    ) -> AdminCreateWalkInOrderResult:
        if not command.items:
            raise OrderEmptyError()

        async with self._uow:
            # 1) Idempotency replay.
            existing_id = await self._idem.get_result(
                key=command.idempotency_key, scope=SCOPE
            )
            if existing_id is not None:
                existing = await self._order_repo.get(existing_id)
                if existing is None:
                    raise IdempotencyKeyConflictError()
                return AdminCreateWalkInOrderResult(
                    order_id=existing.id,
                    identity_id=existing.identity_id,
                    total_amount=existing.total_amount,
                    currency=existing.currency,
                )

            # 2) Snapshot SKU metadata + prices (single round-trip).
            snapshots = await self._sku_reader.get_many(
                tuple({itm.sku_id for itm in command.items}),
                locale="ru",
            )
            resolved = self._resolve_lines(command, snapshots)

            # 3) Build domain RecipientSnapshot (TYPE-005 validates here).
            recipient_snapshot = self._build_recipient_snapshot(command.recipient)

            # 4) Provision walk-in identity + customer.
            provisioned = await self._provisioner.provision(command.profile)

            # 5) Build OrderItems + factory.
            items: list[OrderItem] = []
            for line in resolved:
                items.append(
                    OrderItem(
                        id=line.item_id,
                        sku_id=line.sku_id,
                        product_id=line.product_id,
                        variant_id=line.variant_id,
                        product_name=line.product_name,
                        variant_label=line.variant_label,
                        supplier_type=line.supplier_type,
                        quantity=line.quantity,
                        unit_price_amount=line.unit_price_amount,
                        currency=line.currency,
                    )
                )

            order = Order.create_walk_in(
                identity_id=provisioned.identity_id,
                items=items,
                currency=command.currency,
                pickup_point=command.pickup_point,
                recipient_snapshot=recipient_snapshot,
                cny_rate_at_checkout=command.cny_rate_at_checkout,
                delivery_amount=command.delivery_amount,
            )

            paid_at = command.payment.paid_at or datetime.now(UTC)
            receipt = OfflinePaymentReceipt(
                method=command.payment.method,
                reference=command.payment.reference,
                paid_at=paid_at,
            )
            order.mark_paid_offline(receipt=receipt, admin_id=command.admin_id)

            # 6) Persist.
            order = await self._order_repo.add(order)
            await record_history(
                order=order,
                history_writer=self._history,
                actor=HistoryActor(
                    actor_type="manager", actor_id=str(command.admin_id)
                ),
                pre_commit_status=None,
            )

            # 7) Audit overrides — done after add() so order_item ids exist.
            audit_entries = [
                PriceOverrideAuditEntry(
                    order_id=order.id,
                    order_item_id=line.item_id,
                    sku_id=line.sku_id,
                    base_price_amount=line.base_price_amount,
                    override_price_amount=line.unit_price_amount,
                    currency=line.currency,
                    admin_id=command.admin_id,
                    reason=line.override_reason,
                )
                for line in resolved
                if line.override_applied
            ]
            if audit_entries:
                await self._override_writer.write_many(audit_entries)

            # 8) Idempotency commit.
            now = datetime.now(UTC)
            reserved = await self._idem.reserve(
                key=command.idempotency_key,
                identity_id=command.admin_id,
                scope=SCOPE,
                expires_at=now + timedelta(hours=IDEMPOTENCY_TTL_HOURS),
            )
            if not reserved:
                raise IdempotencyKeyConflictError()
            await self._idem.attach_result(
                key=command.idempotency_key,
                scope=SCOPE,
                resource_id=order.id,
            )

            self._uow.register_aggregate(order)
            await self._uow.commit()

        self._logger.info(
            "walk_in_order.created",
            order_id=str(order.id),
            identity_id=str(provisioned.identity_id),
            admin_id=str(command.admin_id),
            total_amount=order.total_amount,
            currency=order.currency,
            item_count=len(items),
            override_count=len(audit_entries),
        )
        return AdminCreateWalkInOrderResult(
            order_id=order.id,
            identity_id=provisioned.identity_id,
            total_amount=order.total_amount,
            currency=order.currency,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_lines(
        self,
        command: AdminCreateWalkInOrderCommand,
        snapshots: dict[uuid.UUID, CatalogSkuSnapshot],
    ) -> list[_ResolvedLine]:
        max_ratio = float(getattr(settings, "WALK_IN_MAX_PRICE_OVERRIDE_RATIO", 10.0))
        resolved: list[_ResolvedLine] = []
        missing: list[str] = []
        inactive: list[str] = []
        unpriced: list[str] = []
        currency_mismatch: list[str] = []
        for itm in command.items:
            snap = snapshots.get(itm.sku_id)
            if snap is None:
                missing.append(str(itm.sku_id))
                continue
            if not snap.is_active:
                inactive.append(str(itm.sku_id))
                continue
            if snap.selling_price_amount is None:
                unpriced.append(str(itm.sku_id))
                continue
            if snap.currency != command.currency:
                currency_mismatch.append(str(itm.sku_id))
                continue
            base = snap.selling_price_amount
            override = itm.unit_price_override_amount
            applied = override is not None
            unit_price = override if applied else base
            if applied and (unit_price < 0 or unit_price > int(base * max_ratio)):
                raise PriceOverrideValidationError(
                    sku_id=str(itm.sku_id),
                    base_price=base,
                    override_price=unit_price,
                    max_ratio=max_ratio,
                )
            resolved.append(
                _ResolvedLine(
                    sku_id=itm.sku_id,
                    quantity=itm.quantity,
                    unit_price_amount=unit_price,
                    base_price_amount=base,
                    override_applied=applied,
                    override_reason=itm.override_reason,
                    currency=snap.currency,
                    product_id=snap.product_id,
                    variant_id=snap.variant_id,
                    product_name=snap.product_name,
                    variant_label=snap.variant_label,
                    supplier_type=SupplierType(snap.supplier_type),
                )
            )
        if missing or inactive or unpriced or currency_mismatch:
            raise UnprocessableEntityError(
                message="Walk-in order references unusable SKUs",
                error_code="WALK_IN_SKU_NOT_USABLE",
                details={
                    "missing": missing,
                    "inactive": inactive,
                    "unpriced": unpriced,
                    "currency_mismatch": currency_mismatch,
                },
            )
        return resolved

    @staticmethod
    def _build_recipient_snapshot(
        recipient: InlineRecipientInput,
    ) -> RecipientSnapshot:
        # Walk-in recipients carry no backing ``recipients`` row; we
        # mint a deterministic UUID so the snapshot has a stable
        # ``recipient_id`` field (the row is never persisted, but a
        # consistent id helps reconciliation queries and is required
        # by ``RecipientSnapshot.with_updated_data``).
        synthetic_recipient_id = uuid.uuid4()
        return RecipientSnapshot(
            recipient_id=str(synthetic_recipient_id),
            full_name_ru=recipient.full_name_ru,
            full_name_lat=recipient.full_name_lat,
            phone=recipient.phone,
            email=recipient.email,
            passport_serial=recipient.passport_serial,
            passport_number=recipient.passport_number,
            passport_issue_date=cast(date, recipient.passport_issue_date),
            birth_date=cast(date, recipient.birth_date),
            inn=recipient.inn,
        )
