"""Shared helpers for cart unit tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from src.modules.cart.domain.value_objects import (
    CheckoutItemSnapshot,
    CheckoutSnapshot,
)


def make_cart_logger() -> MagicMock:
    """Create a mock logger pre-configured for cart handler tests."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    logger.info = MagicMock()
    return logger


def make_checkout_snapshot(cart_id: uuid.UUID) -> CheckoutSnapshot:
    """Build a minimal ``CheckoutSnapshot`` for test assertions."""
    return CheckoutSnapshot(
        id=uuid.uuid4(),
        cart_id=cart_id,
        items=(
            CheckoutItemSnapshot(
                sku_id=uuid.uuid4(),
                quantity=1,
                unit_price_amount=10000,
                currency="RUB",
            ),
        ),
        pickup_point_id=uuid.uuid4(),
        total_amount=10000,
        currency="RUB",
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )
