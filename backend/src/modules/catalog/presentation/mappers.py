"""Shared mapping helpers for catalog presentation layer."""

from src.modules.catalog.application.queries.read_models import (
    MoneyReadModel,
    ProductVariantReadModel,
    SKUReadModel,
)
from src.modules.catalog.presentation.schemas import (
    MoneySchema,
    ProductVariantResponse,
    SKUResponse,
    VariantAttributePairSchema,
)


def _money(m: MoneyReadModel | None) -> MoneySchema | None:
    if m is None:
        return None
    return MoneySchema(amount=m.amount, currency=m.currency)


def to_sku_response(model: SKUReadModel) -> SKUResponse:
    """Convert a SKU read model to a SKU response schema."""

    return SKUResponse(
        id=model.id,
        product_id=model.product_id,
        variant_id=model.variant_id,
        sku_code=model.sku_code,
        price=_money(model.price),
        resolved_price=_money(model.resolved_price),
        compare_at_price=_money(model.compare_at_price),
        purchase_price=_money(model.purchase_price),
        selling_price=_money(model.selling_price),
        pricing_status=model.pricing_status,
        priced_at=model.priced_at,
        priced_failure_reason=model.priced_failure_reason,
        is_active=model.is_active,
        version=model.version,
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


def to_variant_response(v: ProductVariantReadModel) -> ProductVariantResponse:
    """Convert a ProductVariantReadModel to a ProductVariantResponse schema."""
    return ProductVariantResponse(
        id=v.id,
        name_i18n=v.name_i18n,
        description_i18n=v.description_i18n,
        sort_order=v.sort_order,
        default_price=_money(v.default_price),
        skus=[to_sku_response(s) for s in v.skus],
    )
