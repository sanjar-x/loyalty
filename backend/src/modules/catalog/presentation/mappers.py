"""Shared mapping helpers for catalog presentation layer."""

from src.modules.catalog.application.queries.read_models import SKUReadModel
from src.modules.catalog.presentation.schemas import (
    MoneySchema,
    SKUResponse,
    VariantAttributePairSchema,
)


def to_sku_response(model: SKUReadModel) -> SKUResponse:
    """Convert a SKU read model to a SKU response schema."""
    compare_at: MoneySchema | None = None
    if model.compare_at_price is not None:
        compare_at = MoneySchema(
            amount=model.compare_at_price.amount,
            currency=model.compare_at_price.currency,
        )
    price_schema: MoneySchema | None = None
    if model.price is not None:
        price_schema = MoneySchema(amount=model.price.amount, currency=model.price.currency)
    resolved_price_schema: MoneySchema | None = None
    if model.resolved_price is not None:
        resolved_price_schema = MoneySchema(
            amount=model.resolved_price.amount, currency=model.resolved_price.currency
        )
    return SKUResponse(
        id=model.id,
        product_id=model.product_id,
        variant_id=model.variant_id,
        sku_code=model.sku_code,
        variant_hash=model.variant_hash,
        price=price_schema,
        resolved_price=resolved_price_schema,
        compare_at_price=compare_at,
        is_active=model.is_active,
        version=model.version,
        deleted_at=model.deleted_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
        variant_attributes=[
            VariantAttributePairSchema(
                attribute_id=va.attribute_id,
                attribute_value_id=va.attribute_value_id,
            )
            for va in model.variant_attributes
        ],
    )
