"""Object mothers for Cart value objects."""

from __future__ import annotations

import uuid

from src.modules.cart.domain.value_objects import SkuSnapshot


class SkuSnapshotMother:
    """Preconfigured SkuSnapshot instances for tests."""

    @staticmethod
    def active(
        *,
        sku_id: uuid.UUID | None = None,
        price_amount: int = 10000,
        currency: str = "RUB",
        supplier_type: str = "local",
        product_name: str = "Test Product",
    ) -> SkuSnapshot:
        return SkuSnapshot(
            sku_id=sku_id or uuid.uuid4(),
            product_id=uuid.uuid4(),
            variant_id=uuid.uuid4(),
            product_name=product_name,
            variant_label=None,
            image_url=None,
            price_amount=price_amount,
            currency=currency,
            supplier_type=supplier_type,
            is_active=True,
        )

    @staticmethod
    def inactive(*, sku_id: uuid.UUID | None = None) -> SkuSnapshot:
        return SkuSnapshot(
            sku_id=sku_id or uuid.uuid4(),
            product_id=uuid.uuid4(),
            variant_id=uuid.uuid4(),
            product_name="Inactive Product",
            variant_label=None,
            image_url=None,
            price_amount=5000,
            currency="RUB",
            supplier_type="local",
            is_active=False,
        )

    @staticmethod
    def cross_border(*, sku_id: uuid.UUID | None = None, price_amount: int = 20000) -> SkuSnapshot:
        return SkuSnapshot(
            sku_id=sku_id or uuid.uuid4(),
            product_id=uuid.uuid4(),
            variant_id=uuid.uuid4(),
            product_name="Cross-Border Product",
            variant_label="XL",
            image_url="https://cdn.example.com/img.webp",
            price_amount=price_amount,
            currency="RUB",
            supplier_type="cross_border",
            is_active=True,
        )
