"""Read-only validator for the Product PUBLISHED transition (CAT-019 / C1.1).

Mirrors the gate enforced by ``Product.transition_status(PUBLISHED)``
without mutating the aggregate or emitting events. Returns a structured
verdict the admin UI uses to render a ``PublishGateBlocker`` panel —
shows per-SKU diagnostics + the list of failing rules, so the operator
can fix the problems before clicking Publish.

Returns ``ok=True`` even when ``gate_failures`` is non-empty: a "cannot
publish yet" answer is still a valid preview, not an error.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.entities.product import (
    _publish_diagnostic_for_sku,
)
from src.modules.catalog.domain.exceptions import ProductNotFoundError
from src.modules.catalog.domain.interfaces import IProductRepository
from src.modules.catalog.domain.value_objects import ProductStatus
from shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class ValidateProductPublishQuery:
    """Input — only the product id is needed (read-side, no auth context)."""

    product_id: uuid.UUID


@dataclass(frozen=True)
class GateFailure:
    """One named reason the publish gate is closed.

    ``code`` matches the strings the admin UI maps to localised labels:
    ``NO_ACTIVE_SKU``, ``ALL_SKUS_UNPRICED``, ``STATUS_NOT_TRANSITIONABLE``.
    """

    code: str
    message: str


@dataclass(frozen=True)
class ValidateProductPublishResult:
    """Verdict + per-SKU diagnostics returned to the admin UI."""

    ok: bool
    current_status: str
    next_status: str
    sku_diagnostics: list[dict]
    gate_failures: list[GateFailure]


class ValidateProductPublishHandler:
    """Compute the publish-gate verdict for a single product without mutating it.

    Reuses ``_publish_diagnostic_for_sku`` from the aggregate so the
    diagnostic shape is bit-for-bit identical to what
    ``ProductNotReadyError.details["sku_diagnostics"]`` carries when the
    real ``transition_status(PUBLISHED)`` raises.
    """

    def __init__(
        self,
        repo: IProductRepository,
        logger: ILogger,
    ) -> None:
        self._repo = repo
        self._logger = logger.bind(handler="ValidateProductPublishHandler")

    async def handle(
        self, query: ValidateProductPublishQuery
    ) -> ValidateProductPublishResult:
        product = await self._repo.get_with_variants(query.product_id)
        if product is None:
            raise ProductNotFoundError(product_id=query.product_id)

        current = product.status
        target = ProductStatus.PUBLISHED

        gate_failures: list[GateFailure] = []

        # 1. FSM rule — PUBLISHED reachable only from READY_FOR_REVIEW.
        allowed = product._ALLOWED_TRANSITIONS.get(current, set())
        if target not in allowed:
            gate_failures.append(
                GateFailure(
                    code="STATUS_NOT_TRANSITIONABLE",
                    message=(
                        f"Cannot transition from {current.value!r} to "
                        f"{target.value!r} — only "
                        f"{sorted(s.value for s in allowed) or 'no targets'} "
                        "are reachable from this state."
                    ),
                )
            )

        # 2. At least one active (non-deleted, is_active=True) SKU.
        active_skus = [
            s
            for v in product.variants
            if v.deleted_at is None
            for s in v.skus
            if s.deleted_at is None and s.is_active
        ]
        if not active_skus:
            gate_failures.append(
                GateFailure(
                    code="NO_ACTIVE_SKU",
                    message=(
                        "Product has no active SKUs. Add at least one SKU "
                        "(or re-activate an existing one) before publishing."
                    ),
                )
            )

        # 3. Per-SKU diagnostics — surface even when no FSM gate is broken
        # so the UI can render a green checklist.
        sku_diagnostics = [_publish_diagnostic_for_sku(s) for s in active_skus]

        # 4. Pricing rule — every active SKU must have a manual price OR
        # an autonomous selling_price (ADR-005). Skip when there are no
        # active SKUs (NO_ACTIVE_SKU already covers that).
        if active_skus and not any(
            s.price is not None or s.selling_price is not None for s in active_skus
        ):
            gate_failures.append(
                GateFailure(
                    code="ALL_SKUS_UNPRICED",
                    message=(
                        "No active SKU carries a price. Either set a manual "
                        "``price`` per SKU, or set ``purchase_price`` and let "
                        "the autonomous recompute pipeline derive "
                        "``selling_price``. See ``sku_diagnostics`` for the "
                        "next step on each row."
                    ),
                )
            )

        return ValidateProductPublishResult(
            ok=not gate_failures,
            current_status=current.value,
            next_status=target.value,
            sku_diagnostics=sku_diagnostics,
            gate_failures=gate_failures,
        )


__all__ = [
    "GateFailure",
    "ValidateProductPublishHandler",
    "ValidateProductPublishQuery",
    "ValidateProductPublishResult",
]
