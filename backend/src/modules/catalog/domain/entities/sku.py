"""
SKU child entity owned by the Product aggregate.

Stock Keeping Unit -- a purchasable item within a ProductVariant.
Each SKU represents a unique combination of variant attributes
identified by its ``variant_hash``.
Part of the domain layer -- zero infrastructure imports.

ADR-005: SKU is the source of truth for its purchase price; the
selling price is *computed* by the pricing recompute service and
written back via :meth:`SKU.apply_pricing_result`. Manual
``price`` (legacy) is retained as a fallback during the rollout.
"""

import uuid
from datetime import UTC, datetime
from typing import Any, ClassVar

from attr import dataclass, field

from src.modules.catalog.domain.value_objects import (
    Money,
    PurchaseCurrency,
    SkuPricingStatus,
)


@dataclass
class SKU:
    """Stock Keeping Unit -- a purchasable item within a ProductVariant.

    Child entity owned by a ProductVariant (which is itself a child of
    the Product aggregate). Each SKU represents a unique combination of
    variant attributes (e.g. size) identified by its ``variant_hash``.
    The hash is computed once by the owning Product and stored immutably;
    it is recalculated only when ``variant_attributes`` change via ``update()``.

    Attributes:
        id: Unique SKU identifier.
        product_id: FK to the owning Product aggregate (denormalized).
        variant_id: FK to the parent ProductVariant.
        sku_code: Human-readable stock-keeping code.
        variant_hash: SHA-256 hash of sorted variant attribute pairs.
        price: Legacy manual price; used as storefront fallback when
            ``selling_price`` is not yet computed (e.g. before backfill
            or while a SKU is in ``LEGACY`` status). New SKUs should
            set ``purchase_price`` and let the pricing engine derive
            ``selling_price``.
        compare_at_price: Previous/original price for strikethrough display.
        purchase_price: SKU's wholesale/cost price in ``purchase_currency``
            (ADR-005). When set, drives autonomous recompute of
            ``selling_price`` via the pricing engine. Can be ``None`` only
            for ``LEGACY`` SKUs; other statuses imply a non-null value.
        purchase_currency: Currency in which ``purchase_price`` is
            denominated; one of :class:`PurchaseCurrency`. Required
            iff ``purchase_price`` is set.
        selling_price: Output of the most recent successful pricing
            recompute. Read by storefront listings. Set only by
            :meth:`apply_pricing_result` (which runs through the
            anti-corruption writer in pricing/infrastructure).
        pricing_status: FSM lifecycle of the recompute output (see
            :class:`SkuPricingStatus`). Storefront only surfaces
            ``LEGACY`` and ``PRICED`` SKUs.
        priced_at: UTC timestamp of the last successful recompute.
        priced_with_formula_version_id: ``FormulaVersion`` UUID used to
            produce ``selling_price`` (provenance for audit).
        priced_inputs_hash: Deterministic SHA-256 of canonical inputs
            (purchase price+currency, formula version, FX rate ts,
            supplier/category settings versions, context id). Recompute
            short-circuits when the new hash equals this stored hash —
            this is what makes the at-least-once outbox delivery
            exactly-once-effective.
        priced_failure_reason: Short admin-readable message captured
            when ``pricing_status`` is one of the failure states.
        is_active: Whether the SKU is available for sale.
        version: Optimistic locking version counter (incremented by repo on save).
        deleted_at: Soft-delete timestamp, or None if active.
        created_at: Creation timestamp (UTC).
        updated_at: Last modification timestamp (UTC).
        variant_attributes: List of (attribute_id, attribute_value_id) tuples.
    """

    id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID
    sku_code: str
    variant_hash: str
    price: Money | None = None
    compare_at_price: Money | None = None
    purchase_price: Money | None = None
    purchase_currency: PurchaseCurrency | None = None
    selling_price: Money | None = None
    pricing_status: SkuPricingStatus = SkuPricingStatus.LEGACY
    priced_at: datetime | None = None
    priced_with_formula_version_id: uuid.UUID | None = None
    priced_inputs_hash: str | None = None
    priced_failure_reason: str | None = None
    is_active: bool = True
    version: int = 1
    deleted_at: datetime | None = None
    created_at: datetime = field(factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(factory=lambda: datetime.now(UTC))
    variant_attributes: list[tuple[uuid.UUID, uuid.UUID]] = field(factory=list)

    def __attrs_post_init__(self) -> None:
        """Validate cross-field invariants on construction."""
        if self.price is None and self.compare_at_price is not None:
            raise ValueError("compare_at_price cannot be set when price is None")
        if self.compare_at_price is not None:
            if self.compare_at_price.amount <= 0:
                raise ValueError("compare_at_price amount must be greater than zero")
            if self.price is not None:
                if self.compare_at_price.currency != self.price.currency:
                    raise ValueError(
                        f"compare_at_price currency ({self.compare_at_price.currency}) "
                        f"must match price currency ({self.price.currency})"
                    )
                if not self.compare_at_price > self.price:
                    raise ValueError("compare_at_price must be greater than price")

        # Purchase price / currency must travel as a pair.
        if (self.purchase_price is None) != (self.purchase_currency is None):
            raise ValueError(
                "purchase_price and purchase_currency must be set together"
            )
        if self.purchase_price is not None:
            if self.purchase_price.amount <= 0:
                raise ValueError("purchase_price amount must be greater than zero")
            if (
                self.purchase_currency is not None
                and self.purchase_price.currency != self.purchase_currency.value
            ):
                raise ValueError(
                    f"purchase_price.currency ({self.purchase_price.currency}) "
                    f"must match purchase_currency ({self.purchase_currency.value})"
                )

        # Status invariants — keep selling_price and provenance fields in
        # lock-step with pricing_status. Mismatches indicate corrupt state
        # (e.g. a manual SQL fix that forgot to clear stale provenance).
        if self.pricing_status is SkuPricingStatus.PRICED and (
            self.selling_price is None or self.priced_inputs_hash is None
        ):
            raise ValueError(
                "PRICED status requires selling_price and priced_inputs_hash"
            )
        if (
            self.pricing_status
            in (
                SkuPricingStatus.STALE_FX,
                SkuPricingStatus.MISSING_PURCHASE_PRICE,
                SkuPricingStatus.FORMULA_ERROR,
            )
            and not self.priced_failure_reason
        ):
            raise ValueError(
                f"{self.pricing_status.value} status requires priced_failure_reason"
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def soft_delete(self) -> None:
        """Mark this SKU as deleted.

        Sets ``deleted_at`` and ``updated_at`` to the current UTC timestamp.
        The record is retained in the database; filters must exclude
        non-None ``deleted_at`` when listing active variants.
        """
        if self.deleted_at is not None:
            return
        now = datetime.now(UTC)
        self.deleted_at = now
        self.updated_at = now

    _UPDATABLE_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "sku_code",
            "price",
            "compare_at_price",
            "is_active",
        }
    )

    def update(self, **kwargs: Any) -> None:
        """Update mutable SKU fields.

        Only fields present in ``kwargs`` are applied. Pass ``None`` for
        ``compare_at_price`` to clear it.

        After any price or compare_at_price change the constraint
        ``compare_at_price > price`` is re-validated.

        ``purchase_price`` is *not* updatable through this method — call
        :meth:`set_purchase_price` instead so the pricing recompute event
        is emitted atomically.

        Raises:
            TypeError: If an unknown field name is passed.
            ValueError: If the resulting compare_at_price <= price.
        """
        unknown = set(kwargs) - self._UPDATABLE_FIELDS
        if unknown:
            raise TypeError(f"Cannot update immutable/unknown fields: {unknown}")

        # Validate-then-mutate: compute new state before touching self
        new_price = kwargs.get("price", self.price)
        new_compare = kwargs.get("compare_at_price", self.compare_at_price)

        if new_price is None and new_compare is not None:
            raise ValueError("compare_at_price cannot be set when price is None")
        if new_compare is not None:
            if new_compare.amount <= 0:
                raise ValueError("compare_at_price amount must be greater than zero")
            if new_price is not None:
                if new_compare.currency != new_price.currency:
                    raise ValueError(
                        f"compare_at_price currency ({new_compare.currency}) "
                        f"must match price currency ({new_price.currency})"
                    )
                if not new_compare > new_price:
                    raise ValueError("compare_at_price must be greater than price")

        # All validation passed — safe to mutate
        changed = False
        if "sku_code" in kwargs:
            self.sku_code = kwargs["sku_code"]
            changed = True
        if "price" in kwargs:
            self.price = kwargs["price"]
            changed = True
        if "compare_at_price" in kwargs:
            self.compare_at_price = kwargs["compare_at_price"]
            changed = True
        if "is_active" in kwargs:
            self.is_active = kwargs["is_active"]
            changed = True

        if changed:
            self.updated_at = datetime.now(UTC)

    # ------------------------------------------------------------------
    # ADR-005 — pricing FSM
    # ------------------------------------------------------------------

    def set_purchase_price(
        self,
        *,
        purchase_price: Money,
        purchase_currency: PurchaseCurrency,
    ) -> bool:
        """Record a new purchase price and arm the pricing recompute pipeline.

        Returns ``True`` when the value actually changed (caller emits
        :class:`SKUPurchasePriceUpdatedEvent`); returns ``False`` for
        idempotent re-submits. Transitions ``pricing_status`` to
        ``PENDING`` so storefront listings hide the SKU until the
        recompute job lands a fresh ``selling_price`` — preventing a
        window where an admin updates the cost but the storefront is
        still showing the previous selling price.

        Args:
            purchase_price: The cost amount in smallest currency units;
                ``Money.currency`` must match ``purchase_currency.value``.
            purchase_currency: One of :class:`PurchaseCurrency`.

        Raises:
            ValueError: If ``purchase_price.currency`` and
                ``purchase_currency`` disagree, or amount is non-positive.
        """
        if purchase_price.amount <= 0:
            raise ValueError("purchase_price amount must be greater than zero")
        if purchase_price.currency != purchase_currency.value:
            raise ValueError(
                f"purchase_price.currency ({purchase_price.currency}) "
                f"must match purchase_currency ({purchase_currency.value})"
            )

        unchanged = (
            self.purchase_price is not None
            and self.purchase_price == purchase_price
            and self.purchase_currency is purchase_currency
        )
        if unchanged:
            return False

        self.purchase_price = purchase_price
        self.purchase_currency = purchase_currency
        # Force a recompute window: drop stale provenance, hide from storefront
        # until a fresh recompute lands. priced_failure_reason is cleared so a
        # previous failure doesn't surface for an already-fixed input.
        self.pricing_status = SkuPricingStatus.PENDING
        self.selling_price = None
        self.priced_inputs_hash = None
        self.priced_with_formula_version_id = None
        self.priced_failure_reason = None
        self.priced_at = None
        self.updated_at = datetime.now(UTC)
        return True

    def apply_pricing_result(
        self,
        *,
        selling_price: Money,
        formula_version_id: uuid.UUID,
        inputs_hash: str,
        priced_at: datetime,
    ) -> bool:
        """Land a successful recompute result.

        Idempotent on ``inputs_hash``: if the new hash equals the
        currently stored one, returns ``False`` and does not mutate
        the entity. Otherwise transitions to ``PRICED``, sets the
        provenance fields, and returns ``True`` (caller emits
        :class:`SKUPricedEvent`).

        Args:
            selling_price: Output of formula evaluation. Must be in the
                pricing context's target currency (typically RUB).
            formula_version_id: ``FormulaVersion`` UUID used.
            inputs_hash: SHA-256 of canonical inputs (computed by the
                recompute service; opaque to the entity).
            priced_at: UTC timestamp the recompute service captured.

        Raises:
            ValueError: If ``selling_price`` is non-positive or
                ``inputs_hash`` is empty.
        """
        if selling_price.amount <= 0:
            raise ValueError("selling_price amount must be greater than zero")
        if not inputs_hash:
            raise ValueError("inputs_hash must be a non-empty digest")

        if (
            self.pricing_status is SkuPricingStatus.PRICED
            and self.priced_inputs_hash == inputs_hash
        ):
            return False

        self.selling_price = selling_price
        self.priced_with_formula_version_id = formula_version_id
        self.priced_inputs_hash = inputs_hash
        self.priced_at = priced_at
        self.priced_failure_reason = None
        self.pricing_status = SkuPricingStatus.PRICED
        self.updated_at = datetime.now(UTC)
        return True

    def mark_pricing_failed(
        self,
        *,
        status: SkuPricingStatus,
        reason: str,
    ) -> bool:
        """Record a pricing-recompute failure on the SKU.

        Hides the SKU from storefront listings (status is non-priced)
        and stores a short admin-readable reason for surfacing in the
        back office.

        Returns ``True`` when status or reason actually changed —
        ``False`` for idempotent re-submits. Caller emits
        :class:`SKUPricingFailedEvent` only on the True branch.

        Args:
            status: One of ``STALE_FX``, ``MISSING_PURCHASE_PRICE``,
                ``FORMULA_ERROR``.
            reason: Short admin-readable message; truncated by callers
                to ~500 chars before persistence.

        Raises:
            ValueError: If ``status`` is not a failure state, or
                ``reason`` is empty.
        """
        if status not in (
            SkuPricingStatus.STALE_FX,
            SkuPricingStatus.MISSING_PURCHASE_PRICE,
            SkuPricingStatus.FORMULA_ERROR,
        ):
            raise ValueError(
                f"{status.value!r} is not a failure state; use "
                f"apply_pricing_result for PRICED transitions"
            )
        if not reason:
            raise ValueError("reason must be a non-empty admin-readable message")

        if self.pricing_status is status and self.priced_failure_reason == reason:
            return False

        # Failure clears computed selling_price — storefront fallback to
        # legacy ``price`` is still possible (handled by status enum
        # rather than by retaining a stale selling_price here).
        self.selling_price = None
        self.priced_inputs_hash = None
        self.priced_with_formula_version_id = None
        self.priced_at = None
        self.pricing_status = status
        self.priced_failure_reason = reason
        self.updated_at = datetime.now(UTC)
        return True

    def mark_pricing_pending(self) -> bool:
        """Reset to ``PENDING`` (e.g. when a fan‑out kicks off a recompute).

        Idempotent. Returns ``True`` on a real status change.
        """
        if self.pricing_status is SkuPricingStatus.PENDING:
            return False
        self.pricing_status = SkuPricingStatus.PENDING
        self.priced_failure_reason = None
        self.updated_at = datetime.now(UTC)
        return True
