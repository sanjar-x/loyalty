"""Unit tests for the SKU autonomous-pricing FSM (ADR-005).

Covers the new mutators (``set_purchase_price``, ``apply_pricing_result``,
``mark_pricing_failed``, ``mark_pricing_pending``) and the
construction-time invariants that keep ``pricing_status`` consistent
with selling/provenance fields.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from src.modules.catalog.domain.entities.sku import SKU
from src.modules.catalog.domain.value_objects import (
    Money,
    PurchaseCurrency,
    SkuPricingStatus,
    is_priced_for_storefront,
)


def _make_sku(**overrides) -> SKU:
    """Build a minimally-valid SKU for testing the pricing FSM."""
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "product_id": uuid.uuid4(),
        "variant_id": uuid.uuid4(),
        "sku_code": "SKU-TEST-1",
        "variant_hash": "a" * 64,
    }
    defaults.update(overrides)
    return SKU(**defaults)  # ty: ignore[invalid-argument-type]


# ---------------------------------------------------------------------------
# Construction invariants
# ---------------------------------------------------------------------------


class TestSKUPricingConstructionInvariants:
    def test_purchase_price_and_currency_must_travel_together(self):
        with pytest.raises(ValueError, match="purchase_price and purchase_currency"):
            _make_sku(purchase_price=Money(amount=100, currency="RUB"))

    def test_purchase_price_currency_must_match_enum_value(self):
        with pytest.raises(ValueError, match="must match purchase_currency"):
            _make_sku(
                purchase_price=Money(amount=100, currency="USD"),
                purchase_currency=PurchaseCurrency.RUB,
            )

    def test_priced_status_requires_selling_price_and_hash(self):
        with pytest.raises(ValueError, match="PRICED status requires"):
            _make_sku(pricing_status=SkuPricingStatus.PRICED)

    def test_failure_status_requires_reason(self):
        with pytest.raises(ValueError, match="requires priced_failure_reason"):
            _make_sku(pricing_status=SkuPricingStatus.STALE_FX)

    def test_legacy_status_is_default_and_visible_on_storefront(self):
        sku = _make_sku()
        assert sku.pricing_status is SkuPricingStatus.LEGACY
        assert is_priced_for_storefront(sku.pricing_status)

    def test_pending_status_is_hidden_from_storefront(self):
        assert not is_priced_for_storefront(SkuPricingStatus.PENDING)
        assert not is_priced_for_storefront(SkuPricingStatus.STALE_FX)
        assert not is_priced_for_storefront(SkuPricingStatus.FORMULA_ERROR)
        assert not is_priced_for_storefront(SkuPricingStatus.MISSING_PURCHASE_PRICE)


# ---------------------------------------------------------------------------
# set_purchase_price
# ---------------------------------------------------------------------------


class TestSetPurchasePrice:
    def test_records_value_and_arms_pending(self):
        sku = _make_sku()
        changed = sku.set_purchase_price(
            purchase_price=Money(amount=20000, currency="CNY"),
            purchase_currency=PurchaseCurrency.CNY,
        )
        assert changed is True
        assert sku.purchase_price is not None
        assert sku.purchase_price.amount == 20000
        assert sku.purchase_currency is PurchaseCurrency.CNY
        assert sku.pricing_status is SkuPricingStatus.PENDING
        assert sku.selling_price is None
        assert sku.priced_inputs_hash is None

    def test_idempotent_on_identical_value(self):
        sku = _make_sku(
            purchase_price=Money(amount=15000, currency="RUB"),
            purchase_currency=PurchaseCurrency.RUB,
            pricing_status=SkuPricingStatus.LEGACY,
        )
        changed = sku.set_purchase_price(
            purchase_price=Money(amount=15000, currency="RUB"),
            purchase_currency=PurchaseCurrency.RUB,
        )
        assert changed is False
        assert sku.pricing_status is SkuPricingStatus.LEGACY  # untouched

    def test_clears_provenance_on_change(self):
        sku = _make_sku(
            purchase_price=Money(amount=10000, currency="RUB"),
            purchase_currency=PurchaseCurrency.RUB,
            selling_price=Money(amount=15000, currency="RUB"),
            pricing_status=SkuPricingStatus.PRICED,
            priced_at=datetime.now(UTC),
            priced_with_formula_version_id=uuid.uuid4(),
            priced_inputs_hash="x" * 64,
        )
        sku.set_purchase_price(
            purchase_price=Money(amount=12000, currency="RUB"),
            purchase_currency=PurchaseCurrency.RUB,
        )
        assert sku.pricing_status is SkuPricingStatus.PENDING
        assert sku.selling_price is None
        assert sku.priced_inputs_hash is None
        assert sku.priced_with_formula_version_id is None
        assert sku.priced_at is None

    def test_rejects_currency_mismatch(self):
        sku = _make_sku()
        with pytest.raises(ValueError, match="must match purchase_currency"):
            sku.set_purchase_price(
                purchase_price=Money(amount=10000, currency="USD"),
                purchase_currency=PurchaseCurrency.RUB,
            )

    def test_rejects_non_positive_amount(self):
        sku = _make_sku()
        with pytest.raises(ValueError, match="greater than zero"):
            sku.set_purchase_price(
                purchase_price=Money(amount=0, currency="RUB"),
                purchase_currency=PurchaseCurrency.RUB,
            )


# ---------------------------------------------------------------------------
# apply_pricing_result
# ---------------------------------------------------------------------------


class TestApplyPricingResult:
    def test_lands_priced_state(self):
        sku = _make_sku()
        formula_id = uuid.uuid4()
        priced_at = datetime.now(UTC)
        changed = sku.apply_pricing_result(
            selling_price=Money(amount=25000, currency="RUB"),
            formula_version_id=formula_id,
            inputs_hash="a" * 64,
            priced_at=priced_at,
        )
        assert changed is True
        assert sku.pricing_status is SkuPricingStatus.PRICED
        assert sku.selling_price is not None
        assert sku.selling_price.amount == 25000
        assert sku.priced_with_formula_version_id == formula_id
        assert sku.priced_inputs_hash == "a" * 64
        assert sku.priced_at == priced_at
        assert sku.priced_failure_reason is None

    def test_idempotent_on_identical_hash(self):
        formula_id = uuid.uuid4()
        priced_at = datetime.now(UTC)
        sku = _make_sku(
            selling_price=Money(amount=25000, currency="RUB"),
            pricing_status=SkuPricingStatus.PRICED,
            priced_at=priced_at,
            priced_with_formula_version_id=formula_id,
            priced_inputs_hash="b" * 64,
        )
        before_updated = sku.updated_at
        changed = sku.apply_pricing_result(
            selling_price=Money(amount=99999, currency="RUB"),  # ignored on no-op
            formula_version_id=uuid.uuid4(),
            inputs_hash="b" * 64,
            priced_at=datetime.now(UTC),
        )
        assert changed is False
        assert sku.selling_price is not None
        assert sku.selling_price.amount == 25000
        assert sku.updated_at == before_updated

    def test_clears_prior_failure(self):
        sku = _make_sku(
            pricing_status=SkuPricingStatus.STALE_FX,
            priced_failure_reason="FX rate older than 14 days",
        )
        sku.apply_pricing_result(
            selling_price=Money(amount=25000, currency="RUB"),
            formula_version_id=uuid.uuid4(),
            inputs_hash="c" * 64,
            priced_at=datetime.now(UTC),
        )
        assert sku.pricing_status is SkuPricingStatus.PRICED
        assert sku.priced_failure_reason is None

    def test_rejects_non_positive_price(self):
        sku = _make_sku()
        with pytest.raises(ValueError, match="greater than zero"):
            sku.apply_pricing_result(
                selling_price=Money(amount=0, currency="RUB"),
                formula_version_id=uuid.uuid4(),
                inputs_hash="d" * 64,
                priced_at=datetime.now(UTC),
            )


# ---------------------------------------------------------------------------
# mark_pricing_failed
# ---------------------------------------------------------------------------


class TestMarkPricingFailed:
    def test_records_failure_and_clears_selling(self):
        sku = _make_sku(
            selling_price=Money(amount=25000, currency="RUB"),
            pricing_status=SkuPricingStatus.PRICED,
            priced_at=datetime.now(UTC),
            priced_with_formula_version_id=uuid.uuid4(),
            priced_inputs_hash="e" * 64,
        )
        changed = sku.mark_pricing_failed(
            status=SkuPricingStatus.STALE_FX,
            reason="FX rate older than 14 days",
        )
        assert changed is True
        assert sku.pricing_status is SkuPricingStatus.STALE_FX
        assert sku.selling_price is None
        assert sku.priced_inputs_hash is None
        assert sku.priced_with_formula_version_id is None
        assert sku.priced_at is None
        assert sku.priced_failure_reason == "FX rate older than 14 days"

    def test_idempotent_on_identical_status_and_reason(self):
        sku = _make_sku(
            pricing_status=SkuPricingStatus.MISSING_PURCHASE_PRICE,
            priced_failure_reason="No purchase price",
        )
        before_updated = sku.updated_at
        changed = sku.mark_pricing_failed(
            status=SkuPricingStatus.MISSING_PURCHASE_PRICE,
            reason="No purchase price",
        )
        assert changed is False
        assert sku.updated_at == before_updated

    def test_rejects_non_failure_status(self):
        sku = _make_sku()
        with pytest.raises(ValueError, match="not a failure state"):
            sku.mark_pricing_failed(
                status=SkuPricingStatus.PRICED,
                reason="x",
            )

    def test_rejects_empty_reason(self):
        sku = _make_sku()
        with pytest.raises(ValueError, match="non-empty"):
            sku.mark_pricing_failed(
                status=SkuPricingStatus.FORMULA_ERROR,
                reason="",
            )


# ---------------------------------------------------------------------------
# mark_pricing_pending
# ---------------------------------------------------------------------------


class TestMarkPricingPending:
    def test_transitions_to_pending(self):
        sku = _make_sku(pricing_status=SkuPricingStatus.LEGACY)
        changed = sku.mark_pricing_pending()
        assert changed is True
        assert sku.pricing_status is SkuPricingStatus.PENDING

    def test_idempotent(self):
        sku = _make_sku(pricing_status=SkuPricingStatus.PENDING)
        changed = sku.mark_pricing_pending()
        assert changed is False
