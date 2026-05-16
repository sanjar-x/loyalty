"""Internal helper: resolve a logistics ``delivery_quote_id`` for order
creation handlers.

Originally inlined in :class:`CreateOrderFromCartHandler` as
``_resolve_delivery``. Extracted so the buy-now command can share the
exact same ownership / currency / expiry validations without copy-paste
(REC: any divergence between cart-flow and buy-now flow on these checks
would let a different bug into one branch and not the other).

The helper deliberately stays at module-private visibility (leading
underscore on the file) — only Order command handlers consume it; no
new public port.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from src.modules.order.domain.interfaces import IDeliveryQuoteLookup
from src.shared.exceptions import UnprocessableEntityError, ValidationError


async def resolve_delivery_quote(
    *,
    quote_id: uuid.UUID | None,
    identity_id: uuid.UUID,
    expected_currency: str,
    lookup: IDeliveryQuoteLookup,
) -> tuple[int, uuid.UUID | None]:
    """Return ``(delivery_amount, delivery_quote_id)`` for an order.

    Args:
        quote_id: Quote id supplied by the customer (``None`` for legacy
            clients without a priced shipping line).
        identity_id: Customer that is creating the order — used for the
            CR-2 ownership check.
        expected_currency: Currency the order is being priced in. Must
            match the quote's currency exactly (case-insensitive).
        lookup: ACL adapter into the logistics module.

    Returns:
        ``(0, None)`` when ``quote_id is None`` (legacy clients keep
        working without a priced shipping line); otherwise
        ``(quote.amount, quote.quote_id)``.

    Raises:
        UnprocessableEntityError: Quote not found, expired, or belongs
            to a different customer.
        ValidationError: Quote currency does not match the order
            currency — surfaced as 400 because the input is well-formed
            but business-rule rejected.
    """
    if quote_id is None:
        return 0, None
    quote = await lookup.get(quote_id)
    if quote is None:
        raise UnprocessableEntityError(
            message="Delivery quote not found",
            error_code="ORDER_DELIVERY_QUOTE_NOT_FOUND",
            details={"delivery_quote_id": str(quote_id)},
        )
    # CR-2: ownership check. Quotes stamped with ``identity_id``
    # (every customer storefront quote since REC-041) must match the
    # placing identity. ``None`` is the opt-out for admin / legacy
    # quotes; we keep the existing trust model for them so the upgrade
    # does not break workflows that haven't been re-quoted under the
    # new endpoint yet.
    if quote.identity_id is not None and quote.identity_id != identity_id:
        raise UnprocessableEntityError(
            message="Delivery quote belongs to a different customer",
            error_code="ORDER_DELIVERY_QUOTE_OWNERSHIP_MISMATCH",
            details={"delivery_quote_id": str(quote_id)},
        )
    if quote.currency.upper() != expected_currency.upper():
        raise ValidationError(
            message="Delivery quote currency does not match order currency",
            error_code="ORDER_DELIVERY_QUOTE_CURRENCY_MISMATCH",
            # ``cart_currency`` is kept alongside the new ``expected_currency``
            # for backward compatibility with mini-app builds that key off the
            # old name (introduced when this lived inline in
            # ``create_order_from_cart``). Drop ``cart_currency`` once the
            # frontend reads ``expected_currency`` only.
            details={
                "quote_currency": quote.currency,
                "expected_currency": expected_currency,
                "cart_currency": expected_currency,
            },
        )
    if quote.expires_at is not None and quote.expires_at <= datetime.now(UTC):
        raise UnprocessableEntityError(
            message="Delivery quote expired — request a new quote",
            error_code="ORDER_DELIVERY_QUOTE_EXPIRED",
            details={
                "delivery_quote_id": str(quote_id),
                "expired_at": quote.expires_at.isoformat(),
            },
        )
    return quote.amount, quote.quote_id
