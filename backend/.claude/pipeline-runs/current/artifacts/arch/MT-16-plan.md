# MT-16 Architecture Plan: ProductAttributeValue ORM Model and Migration

## Overview
Add ProductAttributeValue ORM model to `models.py` following the existing `SKUAttributeValueLink` pattern. This is a bridge table linking products to EAV attribute values (one value per attribute per product).

## Files to Modify

### 1. `src/modules/catalog/infrastructure/models.py`

**Add new class `ProductAttributeValueModel`** after `SKUAttributeValueLink` (end of file):

```python
class ProductAttributeValueModel(Base):
    """Bridge between Product and EAV attribute values.

    Each row assigns one attribute value to a product.
    Unique constraint ensures one value per attribute per product.
    """

    __tablename__ = "product_attribute_values"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid7)
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    attribute_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attributes.id", ondelete="CASCADE"), index=True
    )
    attribute_value_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attribute_values.id", ondelete="RESTRICT"), index=True
    )

    product: Mapped[Product] = relationship("Product", back_populates="product_attribute_values")
    attribute: Mapped[Attribute] = relationship("Attribute")
    attribute_value: Mapped[AttributeValue] = relationship("AttributeValue")

    __table_args__ = (
        UniqueConstraint("product_id", "attribute_id", name="uix_product_single_attribute_value"),
        Index("ix_product_attr_val_lookup", "attribute_value_id", "product_id"),
    )
```

**Add relationship to Product model** (after `skus` relationship, ~line 493):
```python
product_attribute_values: Mapped[list[ProductAttributeValueModel]] = relationship(
    "ProductAttributeValueModel", back_populates="product", cascade="all, delete-orphan"
)
```

Note: Use forward reference string "ProductAttributeValueModel" since it's defined after Product.

### 2. Migration

Run `uv run alembic revision --autogenerate -m "add product_attribute_values table"` to generate migration.

Do NOT run `alembic upgrade head` (no DB available in dev).

## Key Decisions
- `ondelete="RESTRICT"` on attribute_value_id (same as SKUAttributeValueLink) — prevents deleting a value that's in use
- `ondelete="CASCADE"` on product_id and attribute_id — cleaning up when parent is removed
- UniqueConstraint name follows pattern: `uix_{table}_{semantic_description}`
- No `created_at`/`updated_at` needed — this is a simple pivot table

## Acceptance Criteria
- [ ] ProductAttributeValueModel class added to models.py
- [ ] Product.product_attribute_values relationship added
- [ ] Unique constraint on (product_id, attribute_id)
- [ ] Indexes on all FK columns
- [ ] Alembic migration generated
- [ ] ruff + mypy pass
