"""Unit tests for ProductAttributeValueModel ORM metadata.

Validates table name, columns, constraints, indexes, and relationships
by inspecting SQLAlchemy model metadata -- no database connection required.
"""

import pytest
from sqlalchemy import UniqueConstraint, inspect
from sqlalchemy.orm import RelationshipProperty

from src.modules.catalog.infrastructure.models import (
    Product,
    ProductAttributeValueModel,
)

pytestmark = pytest.mark.unit


class TestProductAttributeValueModelTable:
    """Structural tests for the product_attribute_values table definition."""

    def test_tablename(self) -> None:
        """Model maps to the 'product_attribute_values' table."""
        assert ProductAttributeValueModel.__tablename__ == "product_attribute_values"

    def test_has_required_columns(self) -> None:
        """Table contains all expected columns: id, product_id, attribute_id, attribute_value_id."""
        mapper = inspect(ProductAttributeValueModel)
        column_names = {col.key for col in mapper.columns}
        expected = {"id", "product_id", "attribute_id", "attribute_value_id"}
        assert expected.issubset(column_names), f"Missing columns: {expected - column_names}"

    def test_primary_key_is_id(self) -> None:
        """Primary key is the 'id' column."""
        mapper = inspect(ProductAttributeValueModel)
        pk_cols = [col.name for col in mapper.columns if col.primary_key]
        assert pk_cols == ["id"]

    def test_id_column_is_uuid(self) -> None:
        """The 'id' column uses UUID type."""
        table = ProductAttributeValueModel.__table__
        col = table.c.id
        assert "UUID" in str(col.type).upper()


class TestProductAttributeValueModelForeignKeys:
    """Foreign key definitions on ProductAttributeValueModel."""

    def test_product_id_fk_targets_products(self) -> None:
        """product_id references products.id."""
        table = ProductAttributeValueModel.__table__
        fks = {fk.target_fullname for fk in table.c.product_id.foreign_keys}
        assert "products.id" in fks

    def test_attribute_id_fk_targets_attributes(self) -> None:
        """attribute_id references attributes.id."""
        table = ProductAttributeValueModel.__table__
        fks = {fk.target_fullname for fk in table.c.attribute_id.foreign_keys}
        assert "attributes.id" in fks

    def test_attribute_value_id_fk_targets_attribute_values(self) -> None:
        """attribute_value_id references attribute_values.id."""
        table = ProductAttributeValueModel.__table__
        fks = {fk.target_fullname for fk in table.c.attribute_value_id.foreign_keys}
        assert "attribute_values.id" in fks

    def test_product_id_cascade_delete(self) -> None:
        """product_id FK uses CASCADE on delete."""
        table = ProductAttributeValueModel.__table__
        fk = next(iter(table.c.product_id.foreign_keys))
        assert fk.ondelete == "CASCADE"

    def test_attribute_id_cascade_delete(self) -> None:
        """attribute_id FK uses CASCADE on delete."""
        table = ProductAttributeValueModel.__table__
        fk = next(iter(table.c.attribute_id.foreign_keys))
        assert fk.ondelete == "CASCADE"

    def test_attribute_value_id_restrict_delete(self) -> None:
        """attribute_value_id FK uses RESTRICT on delete (prevent orphaning)."""
        table = ProductAttributeValueModel.__table__
        fk = next(iter(table.c.attribute_value_id.foreign_keys))
        assert fk.ondelete == "RESTRICT"


class TestProductAttributeValueModelConstraints:
    """Unique constraints on ProductAttributeValueModel."""

    def test_unique_constraint_on_product_id_attribute_id(self) -> None:
        """UniqueConstraint exists on (product_id, attribute_id) -- one value per attribute per product."""
        table = ProductAttributeValueModel.__table__
        unique_constraints = [c for c in table.constraints if isinstance(c, UniqueConstraint)]
        matching = [
            c
            for c in unique_constraints
            if {col.name for col in c.columns} == {"product_id", "attribute_id"}
        ]
        assert len(matching) == 1, (
            "Expected exactly one UniqueConstraint on (product_id, attribute_id)"
        )

    def test_unique_constraint_name(self) -> None:
        """UniqueConstraint is named 'uix_product_single_attribute_value'."""
        table = ProductAttributeValueModel.__table__
        unique_constraints = [c for c in table.constraints if isinstance(c, UniqueConstraint)]
        names = {c.name for c in unique_constraints}
        assert "uix_product_single_attribute_value" in names


class TestProductAttributeValueModelIndexes:
    """Index definitions on ProductAttributeValueModel."""

    def _get_index_names(self) -> set[str]:
        """Return all index names on the table."""
        table = ProductAttributeValueModel.__table__
        return {idx.name for idx in table.indexes if idx.name}

    def test_product_id_indexed(self) -> None:
        """product_id column has an index for efficient product lookups."""
        table = ProductAttributeValueModel.__table__
        col = table.c.product_id
        assert col.index is True or any(col in idx.columns for idx in table.indexes)

    def test_attribute_id_indexed(self) -> None:
        """attribute_id column has an index."""
        table = ProductAttributeValueModel.__table__
        col = table.c.attribute_id
        assert col.index is True or any(col in idx.columns for idx in table.indexes)

    def test_attribute_value_id_indexed(self) -> None:
        """attribute_value_id column has an index."""
        table = ProductAttributeValueModel.__table__
        col = table.c.attribute_value_id
        assert col.index is True or any(col in idx.columns for idx in table.indexes)

    def test_composite_lookup_index_exists(self) -> None:
        """Composite index ix_product_attr_val_lookup on (attribute_value_id, product_id) exists."""
        assert "ix_product_attr_val_lookup" in self._get_index_names()


class TestProductAttributeValueModelRelationships:
    """ORM relationship definitions on ProductAttributeValueModel and Product."""

    def test_model_has_product_relationship(self) -> None:
        """ProductAttributeValueModel.product relationship exists."""
        mapper = inspect(ProductAttributeValueModel)
        rels = {r.key: r for r in mapper.relationships}
        assert "product" in rels

    def test_model_has_attribute_relationship(self) -> None:
        """ProductAttributeValueModel.attribute relationship exists."""
        mapper = inspect(ProductAttributeValueModel)
        rels = {r.key for r in mapper.relationships}
        assert "attribute" in rels

    def test_model_has_attribute_value_relationship(self) -> None:
        """ProductAttributeValueModel.attribute_value relationship exists."""
        mapper = inspect(ProductAttributeValueModel)
        rels = {r.key for r in mapper.relationships}
        assert "attribute_value" in rels

    def test_product_has_product_attribute_values_relationship(self) -> None:
        """Product model has a back-populates 'product_attribute_values' relationship."""
        mapper = inspect(Product)
        rels = {r.key for r in mapper.relationships}
        assert "product_attribute_values" in rels

    def test_product_relationship_cascade_delete_orphan(self) -> None:
        """Product.product_attribute_values uses 'all, delete-orphan' cascade."""
        mapper = inspect(Product)
        rel: RelationshipProperty = mapper.relationships["product_attribute_values"]  # type: ignore[assignment]
        cascade = rel.cascade
        assert cascade.delete is True
        assert cascade.delete_orphan is True


class TestProductAttributeValueModelRegistry:
    """ProductAttributeValueModel is registered in the model registry."""

    def test_model_in_registry(self) -> None:
        """ProductAttributeValueModel is importable from the registry module."""
        from src.infrastructure.database.registry import ProductAttributeValueModel as RegistryModel

        assert RegistryModel is ProductAttributeValueModel
