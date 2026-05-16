"""Unit tests for :func:`resolve_delivery_quote`.

The helper is consumed by both ``CreateOrderFromCartHandler`` and
``CreateBuyNowOrderHandler``; testing it in isolation pins down the
ownership / currency / expiry boundary so a regression in either flow
fails one targeted test instead of cascading through both handlers'
suites.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from src.modules.order.application._delivery import resolve_delivery_quote
from src.modules.order.domain.interfaces import (
    DeliveryQuoteLookupResult,
    IDeliveryQuoteLookup,
)
from src.shared.exceptions import UnprocessableEntityError, ValidationError

pytestmark = pytest.mark.unit


class _RecordingLookup(IDeliveryQuoteLookup):
    """Tracks the number of calls so the short-circuit branch is verifiable."""

    def __init__(self, records: dict[uuid.UUID, DeliveryQuoteLookupResult]) -> None:
        self._records = records
        self.calls = 0

    async def get(self, quote_id: uuid.UUID) -> DeliveryQuoteLookupResult | None:
        self.calls += 1
        return self._records.get(quote_id)


def _quote(
    *,
    identity_id: uuid.UUID | None,
    amount: int = 30000,
    currency: str = "RUB",
    expires_at: datetime | None = None,
) -> DeliveryQuoteLookupResult:
    return DeliveryQuoteLookupResult(
        quote_id=uuid.uuid4(),
        amount=amount,
        currency=currency,
        expires_at=expires_at,
        identity_id=identity_id,
    )


# ---------------------------------------------------------------------------
# Short-circuit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_none_quote_id_returns_zero_amount_without_lookup() -> None:
    lookup = _RecordingLookup({})
    amount, quote_id = await resolve_delivery_quote(
        quote_id=None,
        identity_id=uuid.uuid4(),
        expected_currency="RUB",
        lookup=lookup,
    )
    assert (amount, quote_id) == (0, None)
    assert lookup.calls == 0, "legacy clients must not pay the lookup cost"


# ---------------------------------------------------------------------------
# Not found
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_quote_raises_not_found() -> None:
    lookup = _RecordingLookup({})
    quote_id = uuid.uuid4()
    with pytest.raises(UnprocessableEntityError) as exc:
        await resolve_delivery_quote(
            quote_id=quote_id,
            identity_id=uuid.uuid4(),
            expected_currency="RUB",
            lookup=lookup,
        )
    assert exc.value.error_code == "ORDER_DELIVERY_QUOTE_NOT_FOUND"
    assert exc.value.details["delivery_quote_id"] == str(quote_id)


# ---------------------------------------------------------------------------
# Ownership (CR-2)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quote_owned_by_other_identity_rejected() -> None:
    placing = uuid.uuid4()
    owner = uuid.uuid4()
    quote = _quote(identity_id=owner)
    lookup = _RecordingLookup({quote.quote_id: quote})
    with pytest.raises(UnprocessableEntityError) as exc:
        await resolve_delivery_quote(
            quote_id=quote.quote_id,
            identity_id=placing,
            expected_currency="RUB",
            lookup=lookup,
        )
    assert exc.value.error_code == "ORDER_DELIVERY_QUOTE_OWNERSHIP_MISMATCH"


@pytest.mark.asyncio
async def test_quote_owned_by_same_identity_passes() -> None:
    identity_id = uuid.uuid4()
    quote = _quote(identity_id=identity_id, amount=12345)
    lookup = _RecordingLookup({quote.quote_id: quote})
    amount, qid = await resolve_delivery_quote(
        quote_id=quote.quote_id,
        identity_id=identity_id,
        expected_currency="RUB",
        lookup=lookup,
    )
    assert amount == 12345
    assert qid == quote.quote_id


@pytest.mark.asyncio
async def test_quote_without_owner_opts_out_of_ownership_check() -> None:
    """``identity_id is None`` is the documented legacy/admin opt-out."""
    quote = _quote(identity_id=None, amount=500)
    lookup = _RecordingLookup({quote.quote_id: quote})
    amount, _ = await resolve_delivery_quote(
        quote_id=quote.quote_id,
        identity_id=uuid.uuid4(),
        expected_currency="RUB",
        lookup=lookup,
    )
    assert amount == 500


# ---------------------------------------------------------------------------
# Currency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_currency_compared_case_insensitively() -> None:
    identity_id = uuid.uuid4()
    quote = _quote(identity_id=identity_id, currency="rub")  # lowercase
    lookup = _RecordingLookup({quote.quote_id: quote})
    amount, _ = await resolve_delivery_quote(
        quote_id=quote.quote_id,
        identity_id=identity_id,
        expected_currency="RUB",  # uppercase
        lookup=lookup,
    )
    assert amount == quote.amount


@pytest.mark.asyncio
async def test_currency_mismatch_raises_validation_error() -> None:
    identity_id = uuid.uuid4()
    quote = _quote(identity_id=identity_id, currency="USD")
    lookup = _RecordingLookup({quote.quote_id: quote})
    with pytest.raises(ValidationError) as exc:
        await resolve_delivery_quote(
            quote_id=quote.quote_id,
            identity_id=identity_id,
            expected_currency="RUB",
            lookup=lookup,
        )
    assert exc.value.error_code == "ORDER_DELIVERY_QUOTE_CURRENCY_MISMATCH"
    details = exc.value.details
    assert details["quote_currency"] == "USD"
    assert details["expected_currency"] == "RUB"
    # Backward-compat alias for mini-app builds that still read ``cart_currency``.
    assert details["cart_currency"] == "RUB"


# ---------------------------------------------------------------------------
# Expiry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quote_without_expiry_passes() -> None:
    """``expires_at is None`` skips the expiry branch entirely."""
    identity_id = uuid.uuid4()
    quote = _quote(identity_id=identity_id, expires_at=None)
    lookup = _RecordingLookup({quote.quote_id: quote})
    amount, _ = await resolve_delivery_quote(
        quote_id=quote.quote_id,
        identity_id=identity_id,
        expected_currency="RUB",
        lookup=lookup,
    )
    assert amount == quote.amount


@pytest.mark.asyncio
async def test_expired_quote_raises_unprocessable() -> None:
    identity_id = uuid.uuid4()
    quote = _quote(
        identity_id=identity_id,
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    lookup = _RecordingLookup({quote.quote_id: quote})
    with pytest.raises(UnprocessableEntityError) as exc:
        await resolve_delivery_quote(
            quote_id=quote.quote_id,
            identity_id=identity_id,
            expected_currency="RUB",
            lookup=lookup,
        )
    assert exc.value.error_code == "ORDER_DELIVERY_QUOTE_EXPIRED"
    assert "expired_at" in exc.value.details


@pytest.mark.asyncio
async def test_future_expiry_passes() -> None:
    identity_id = uuid.uuid4()
    quote = _quote(
        identity_id=identity_id,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    lookup = _RecordingLookup({quote.quote_id: quote})
    amount, _ = await resolve_delivery_quote(
        quote_id=quote.quote_id,
        identity_id=identity_id,
        expected_currency="RUB",
        lookup=lookup,
    )
    assert amount == quote.amount
