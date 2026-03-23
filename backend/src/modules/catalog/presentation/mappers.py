"""Shared mapping helpers for catalog presentation layer."""

from src.modules.catalog.application.queries.read_models import ProductReadModel, SKUReadModel
from src.modules.catalog.presentation.schemas import (
    MoneySchema,
    ProductAttributeResponse,
    ProductResponse,
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
    return SKUResponse(
        id=model.id,
        product_id=model.product_id,
        sku_code=model.sku_code,
        variant_hash=model.variant_hash,
        price=MoneySchema(amount=model.price.amount, currency=model.price.currency),
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


def to_product_response(model: ProductReadModel) -> ProductResponse:
    """Convert a full product read model to a product response schema."""
    return ProductResponse(
        id=model.id,
        slug=model.slug,
        title_i18n=model.title_i18n,
        description_i18n=model.description_i18n,
        status=model.status,
        brand_id=model.brand_id,
        primary_category_id=model.primary_category_id,
        supplier_id=model.supplier_id,
        country_of_origin=model.country_of_origin,
        tags=model.tags,
        version=model.version,
        deleted_at=model.deleted_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
        published_at=model.published_at,
        min_price=model.min_price,
        max_price=model.max_price,
        skus=[to_sku_response(s) for s in model.skus],
        attributes=[
            ProductAttributeResponse(
                id=a.id,
                product_id=a.product_id,
                attribute_id=a.attribute_id,
                attribute_value_id=a.attribute_value_id,
            )
            for a in model.attributes
        ],
    )
