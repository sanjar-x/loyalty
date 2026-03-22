# tests/unit/modules/catalog/application/queries/test_product_read_models.py
"""Unit tests for Product read models (MT-6).

Covers:
- All 7 new read model classes: MoneyReadModel, VariantAttributePairReadModel,
  SKUReadModel, ProductAttributeValueReadModel, ProductReadModel,
  ProductListItemReadModel, ProductListReadModel
- BaseModel inheritance (not CamelModel)
- No domain imports (status is str, not an enum)
- Correct field types and optional defaults
- Correct nesting (ProductReadModel -> SKUReadModel -> MoneyReadModel, etc.)
- Serialization / deserialization round-trips via model_dump / model_validate
- ProductListReadModel pagination fields
- Edge cases: empty lists, None optionals, boundary values
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import pytest
from pydantic import BaseModel

from src.modules.catalog.application.queries.read_models import (
    MoneyReadModel,
    ProductAttributeValueReadModel,
    ProductListItemReadModel,
    ProductListReadModel,
    ProductReadModel,
    ProductVariantReadModel,
    SKUReadModel,
    VariantAttributePairReadModel,
)

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 3, 18, 12, 0, 0, tzinfo=UTC)
_LATER = datetime(2026, 3, 18, 13, 0, 0, tzinfo=UTC)


def _money(amount: int = 1000, currency: str = "USD") -> MoneyReadModel:
    return MoneyReadModel(amount=amount, currency=currency)


def _variant_pair(
    attribute_id: uuid.UUID | None = None,
    attribute_value_id: uuid.UUID | None = None,
) -> VariantAttributePairReadModel:
    return VariantAttributePairReadModel(
        attribute_id=attribute_id or uuid.uuid4(),
        attribute_value_id=attribute_value_id or uuid.uuid4(),
    )


def _sku(product_id: uuid.UUID | None = None, variant_id: uuid.UUID | None = None) -> SKUReadModel:
    return SKUReadModel(
        id=uuid.uuid4(),
        product_id=product_id or uuid.uuid4(),
        variant_id=variant_id or uuid.uuid4(),
        sku_code="SKU-001",
        variant_hash="abc123",
        price=_money(1999, "USD"),
        compare_at_price=None,
        is_active=True,
        version=1,
        deleted_at=None,
        created_at=_NOW,
        updated_at=_NOW,
        variant_attributes=[],
    )


def _variant(
    product_id: uuid.UUID | None = None,
    skus: list[SKUReadModel] | None = None,
) -> ProductVariantReadModel:
    return ProductVariantReadModel(
        id=uuid.uuid4(),
        product_id=product_id or uuid.uuid4(),
        name_i18n={"en": "Default Variant"},
        description_i18n=None,
        sort_order=0,
        default_price=None,
        skus=skus if skus is not None else [],
    )


def _product_attr_value(product_id: uuid.UUID | None = None) -> ProductAttributeValueReadModel:
    return ProductAttributeValueReadModel(
        id=uuid.uuid4(),
        product_id=product_id or uuid.uuid4(),
        attribute_id=uuid.uuid4(),
        attribute_value_id=uuid.uuid4(),
    )


def _product(
    product_id: uuid.UUID | None = None,
    variants: list[ProductVariantReadModel] | None = None,
    attributes: list[ProductAttributeValueReadModel] | None = None,
) -> ProductReadModel:
    pid = product_id or uuid.uuid4()
    return ProductReadModel(
        id=pid,
        slug="test-product",
        title_i18n={"en": "Test Product", "ru": "Тест"},
        description_i18n={"en": "A test product description"},
        status="active",
        brand_id=uuid.uuid4(),
        primary_category_id=uuid.uuid4(),
        tags=["tag1", "tag2"],
        version=1,
        created_at=_NOW,
        updated_at=_NOW,
        variants=variants if variants is not None else [],
        attributes=attributes if attributes is not None else [],
    )


def _list_item(item_id: uuid.UUID | None = None) -> ProductListItemReadModel:
    return ProductListItemReadModel(
        id=item_id or uuid.uuid4(),
        slug="test-product",
        title_i18n={"en": "Test Product"},
        status="active",
        brand_id=uuid.uuid4(),
        primary_category_id=uuid.uuid4(),
        version=1,
        created_at=_NOW,
        updated_at=_NOW,
    )


# ---------------------------------------------------------------------------
# MoneyReadModel
# ---------------------------------------------------------------------------


class TestMoneyReadModel:
    """Tests for MoneyReadModel."""

    def test_instantiation_with_valid_fields(self) -> None:
        """Happy path: MoneyReadModel can be created with amount and currency."""
        model = MoneyReadModel(amount=500, currency="EUR")
        assert model.amount == 500
        assert model.currency == "EUR"

    def test_amount_is_int(self) -> None:
        """amount field must be an integer (smallest currency unit)."""
        model = MoneyReadModel(amount=0, currency="USD")
        assert isinstance(model.amount, int)

    def test_currency_is_str(self) -> None:
        """currency field must be a plain string."""
        model = MoneyReadModel(amount=100, currency="GBP")
        assert isinstance(model.currency, str)

    def test_zero_amount_is_valid(self) -> None:
        """Zero amount is a valid edge case (free items)."""
        model = MoneyReadModel(amount=0, currency="USD")
        assert model.amount == 0

    def test_large_amount_is_valid(self) -> None:
        """Large monetary values are valid."""
        model = MoneyReadModel(amount=999_999_99, currency="USD")
        assert model.amount == 999_999_99

    def test_inherits_from_base_model(self) -> None:
        """MoneyReadModel must inherit from pydantic.BaseModel, not CamelModel."""
        assert issubclass(MoneyReadModel, BaseModel)

    def test_serialization_round_trip(self) -> None:
        """model_dump -> model_validate produces equivalent object."""
        original = MoneyReadModel(amount=1500, currency="USD")
        data = original.model_dump()
        restored = MoneyReadModel.model_validate(data)
        assert restored.amount == original.amount
        assert restored.currency == original.currency

    def test_json_round_trip(self) -> None:
        """model_dump_json -> model_validate_json produces equivalent object."""
        original = MoneyReadModel(amount=250, currency="RUB")
        json_str = original.model_dump_json()
        restored = MoneyReadModel.model_validate_json(json_str)
        assert restored.amount == original.amount
        assert restored.currency == original.currency


# ---------------------------------------------------------------------------
# VariantAttributePairReadModel
# ---------------------------------------------------------------------------


class TestVariantAttributePairReadModel:
    """Tests for VariantAttributePairReadModel."""

    def test_instantiation_with_valid_uuids(self) -> None:
        """Happy path: model created with two UUIDs."""
        attr_id = uuid.uuid4()
        val_id = uuid.uuid4()
        model = VariantAttributePairReadModel(
            attribute_id=attr_id,
            attribute_value_id=val_id,
        )
        assert model.attribute_id == attr_id
        assert model.attribute_value_id == val_id

    def test_fields_are_uuids(self) -> None:
        """Both fields must be uuid.UUID instances."""
        model = _variant_pair()
        assert isinstance(model.attribute_id, uuid.UUID)
        assert isinstance(model.attribute_value_id, uuid.UUID)

    def test_inherits_from_base_model(self) -> None:
        """VariantAttributePairReadModel must inherit from pydantic.BaseModel."""
        assert issubclass(VariantAttributePairReadModel, BaseModel)

    def test_serialization_round_trip(self) -> None:
        """model_dump -> model_validate produces equivalent object."""
        attr_id = uuid.uuid4()
        val_id = uuid.uuid4()
        original = VariantAttributePairReadModel(
            attribute_id=attr_id,
            attribute_value_id=val_id,
        )
        data = original.model_dump()
        restored = VariantAttributePairReadModel.model_validate(data)
        assert restored.attribute_id == original.attribute_id
        assert restored.attribute_value_id == original.attribute_value_id


# ---------------------------------------------------------------------------
# SKUReadModel
# ---------------------------------------------------------------------------


class TestSKUReadModel:
    """Tests for SKUReadModel."""

    def test_instantiation_minimal(self) -> None:
        """Happy path: SKU created with required fields, optionals default to None."""
        sku_id = uuid.uuid4()
        product_id = uuid.uuid4()
        variant_id = uuid.uuid4()
        model = SKUReadModel(
            id=sku_id,
            product_id=product_id,
            variant_id=variant_id,
            sku_code="SKU-ABC",
            variant_hash="hashxyz",
            price=_money(2999, "USD"),
            is_active=True,
            version=1,
            created_at=_NOW,
            updated_at=_NOW,
            variant_attributes=[],
        )
        assert model.id == sku_id
        assert model.product_id == product_id
        assert model.variant_id == variant_id
        assert model.sku_code == "SKU-ABC"
        assert model.compare_at_price is None
        assert model.deleted_at is None
        assert model.variant_attributes == []

    def test_price_is_money_read_model(self) -> None:
        """price field must be a nested MoneyReadModel."""
        sku = _sku()
        assert isinstance(sku.price, MoneyReadModel)

    def test_compare_at_price_optional_none(self) -> None:
        """compare_at_price defaults to None."""
        sku = _sku()
        assert sku.compare_at_price is None

    def test_compare_at_price_optional_set(self) -> None:
        """compare_at_price can be set to a MoneyReadModel."""
        product_id = uuid.uuid4()
        sku = SKUReadModel(
            id=uuid.uuid4(),
            product_id=product_id,
            variant_id=uuid.uuid4(),
            sku_code="SKU-002",
            variant_hash="hash2",
            price=_money(3000, "USD"),
            compare_at_price=_money(3500, "USD"),
            is_active=True,
            version=1,
            created_at=_NOW,
            updated_at=_NOW,
            variant_attributes=[],
        )
        assert isinstance(sku.compare_at_price, MoneyReadModel)
        assert sku.compare_at_price.amount == 3500

    def test_deleted_at_optional_set(self) -> None:
        """deleted_at can be set to a datetime."""
        product_id = uuid.uuid4()
        sku = SKUReadModel(
            id=uuid.uuid4(),
            product_id=product_id,
            variant_id=uuid.uuid4(),
            sku_code="SKU-DEL",
            variant_hash="hashdel",
            price=_money(1000, "USD"),
            is_active=False,
            version=2,
            deleted_at=_LATER,
            created_at=_NOW,
            updated_at=_LATER,
            variant_attributes=[],
        )
        assert sku.deleted_at == _LATER

    def test_variant_attributes_list_of_pairs(self) -> None:
        """variant_attributes holds a list of VariantAttributePairReadModel."""
        pair1 = _variant_pair()
        pair2 = _variant_pair()
        product_id = uuid.uuid4()
        sku = SKUReadModel(
            id=uuid.uuid4(),
            product_id=product_id,
            variant_id=uuid.uuid4(),
            sku_code="SKU-VAR",
            variant_hash="hashvar",
            price=_money(500, "EUR"),
            is_active=True,
            version=1,
            created_at=_NOW,
            updated_at=_NOW,
            variant_attributes=[pair1, pair2],
        )
        assert len(sku.variant_attributes) == 2
        assert all(isinstance(p, VariantAttributePairReadModel) for p in sku.variant_attributes)

    def test_inherits_from_base_model(self) -> None:
        """SKUReadModel must inherit from pydantic.BaseModel."""
        assert issubclass(SKUReadModel, BaseModel)

    def test_serialization_round_trip(self) -> None:
        """model_dump -> model_validate produces equivalent object."""
        pair = _variant_pair()
        sku_id = uuid.uuid4()
        original = SKUReadModel(
            id=sku_id,
            product_id=uuid.uuid4(),
            variant_id=uuid.uuid4(),
            sku_code="SKU-RT",
            variant_hash="hashrt",
            price=_money(4000, "GBP"),
            compare_at_price=_money(4500, "GBP"),
            is_active=True,
            version=3,
            created_at=_NOW,
            updated_at=_NOW,
            variant_attributes=[pair],
        )
        data = original.model_dump()
        restored = SKUReadModel.model_validate(data)
        assert restored.id == original.id
        assert restored.price.amount == original.price.amount
        assert restored.compare_at_price is not None
        assert restored.compare_at_price.amount == 4500
        assert len(restored.variant_attributes) == 1

    def test_no_domain_enum_in_is_active(self) -> None:
        """is_active is a plain bool, not a domain type."""
        sku = _sku()
        assert isinstance(sku.is_active, bool)


# ---------------------------------------------------------------------------
# ProductAttributeValueReadModel
# ---------------------------------------------------------------------------


class TestProductAttributeValueReadModel:
    """Tests for ProductAttributeValueReadModel."""

    def test_instantiation_with_valid_fields(self) -> None:
        """Happy path: all four UUID fields set correctly."""
        rec_id = uuid.uuid4()
        product_id = uuid.uuid4()
        attr_id = uuid.uuid4()
        val_id = uuid.uuid4()
        model = ProductAttributeValueReadModel(
            id=rec_id,
            product_id=product_id,
            attribute_id=attr_id,
            attribute_value_id=val_id,
        )
        assert model.id == rec_id
        assert model.product_id == product_id
        assert model.attribute_id == attr_id
        assert model.attribute_value_id == val_id

    def test_all_fields_are_uuids(self) -> None:
        """Every field must be a uuid.UUID instance."""
        model = _product_attr_value()
        assert isinstance(model.id, uuid.UUID)
        assert isinstance(model.product_id, uuid.UUID)
        assert isinstance(model.attribute_id, uuid.UUID)
        assert isinstance(model.attribute_value_id, uuid.UUID)

    def test_inherits_from_base_model(self) -> None:
        """ProductAttributeValueReadModel must inherit from pydantic.BaseModel."""
        assert issubclass(ProductAttributeValueReadModel, BaseModel)

    def test_serialization_round_trip(self) -> None:
        """model_dump -> model_validate produces equivalent object."""
        original = _product_attr_value()
        data = original.model_dump()
        restored = ProductAttributeValueReadModel.model_validate(data)
        assert restored.id == original.id
        assert restored.product_id == original.product_id
        assert restored.attribute_id == original.attribute_id
        assert restored.attribute_value_id == original.attribute_value_id


# ---------------------------------------------------------------------------
# ProductReadModel
# ---------------------------------------------------------------------------


class TestProductReadModel:
    """Tests for ProductReadModel (full product with nested SKUs and attributes)."""

    def test_instantiation_with_required_fields(self) -> None:
        """Happy path: ProductReadModel created with all required fields."""
        pid = uuid.uuid4()
        product = _product(product_id=pid)
        assert product.id == pid
        assert product.slug == "test-product"
        assert product.status == "active"

    def test_status_is_plain_string_not_enum(self) -> None:
        """status must be a plain str — never a domain enum."""
        product = _product()
        assert isinstance(product.status, str)
        # Must not be an enum instance
        assert type(product.status) is str

    def test_title_i18n_is_dict_of_str(self) -> None:
        """title_i18n is dict[str, str]."""
        product = _product()
        assert isinstance(product.title_i18n, dict)
        for k, v in product.title_i18n.items():
            assert isinstance(k, str)
            assert isinstance(v, str)

    def test_description_i18n_is_dict_of_str(self) -> None:
        """description_i18n is dict[str, str]."""
        product = _product()
        assert isinstance(product.description_i18n, dict)

    def test_tags_is_list_of_str(self) -> None:
        """tags is list[str]."""
        product = _product()
        assert isinstance(product.tags, list)
        assert all(isinstance(t, str) for t in product.tags)

    def test_optional_fields_default_to_none(self) -> None:
        """supplier_id, country_of_origin, deleted_at, published_at, min_price, max_price default None."""
        product = _product()
        assert product.supplier_id is None
        assert product.country_of_origin is None
        assert product.deleted_at is None
        assert product.published_at is None
        assert product.min_price is None
        assert product.max_price is None

    def test_optional_fields_can_be_set(self) -> None:
        """All optional fields accept non-None values."""
        supplier_id = uuid.uuid4()
        product = ProductReadModel(
            id=uuid.uuid4(),
            slug="full-product",
            title_i18n={"en": "Full"},
            description_i18n={"en": "Desc"},
            status="published",
            brand_id=uuid.uuid4(),
            primary_category_id=uuid.uuid4(),
            supplier_id=supplier_id,
            country_of_origin="US",
            tags=[],
            version=5,
            deleted_at=_LATER,
            created_at=_NOW,
            updated_at=_LATER,
            published_at=_NOW,
            min_price=500,
            max_price=9999,
            variants=[],
            attributes=[],
        )
        assert product.supplier_id == supplier_id
        assert product.country_of_origin == "US"
        assert product.deleted_at == _LATER
        assert product.published_at == _NOW
        assert product.min_price == 500
        assert product.max_price == 9999

    def test_variants_list_is_empty_by_default(self) -> None:
        """variants defaults to empty list when provided as []."""
        product = _product()
        assert product.variants == []

    def test_variants_list_contains_variant_read_models(self) -> None:
        """variants field is list[ProductVariantReadModel]."""
        pid = uuid.uuid4()
        variant = _variant(product_id=pid)
        product = _product(product_id=pid, variants=[variant])
        assert len(product.variants) == 1
        assert isinstance(product.variants[0], ProductVariantReadModel)

    def test_attributes_list_contains_product_attribute_value_models(self) -> None:
        """attributes field is list[ProductAttributeValueReadModel]."""
        pid = uuid.uuid4()
        attr_val = _product_attr_value(product_id=pid)
        product = _product(product_id=pid, attributes=[attr_val])
        assert len(product.attributes) == 1
        assert isinstance(product.attributes[0], ProductAttributeValueReadModel)

    def test_nesting_variant_contains_sku_with_money_model(self) -> None:
        """Nested variant's SKU.price is a MoneyReadModel, not a plain dict."""
        pid = uuid.uuid4()
        vid = uuid.uuid4()
        sku = _sku(product_id=pid, variant_id=vid)
        variant = _variant(product_id=pid, skus=[sku])
        product = _product(product_id=pid, variants=[variant])
        assert isinstance(product.variants[0].skus[0].price, MoneyReadModel)

    def test_nesting_variant_sku_contains_variant_pairs(self) -> None:
        """Nested variant's SKU.variant_attributes contains VariantAttributePairReadModel objects."""
        pid = uuid.uuid4()
        pair = _variant_pair()
        sku = SKUReadModel(
            id=uuid.uuid4(),
            product_id=pid,
            variant_id=uuid.uuid4(),
            sku_code="SKU-PAIR",
            variant_hash="hashpair",
            price=_money(1000, "USD"),
            is_active=True,
            version=1,
            created_at=_NOW,
            updated_at=_NOW,
            variant_attributes=[pair],
        )
        variant = _variant(product_id=pid, skus=[sku])
        product = _product(product_id=pid, variants=[variant])
        assert isinstance(
            product.variants[0].skus[0].variant_attributes[0], VariantAttributePairReadModel
        )

    def test_multiple_variants_and_attributes(self) -> None:
        """ProductReadModel correctly holds multiple variants and attributes."""
        pid = uuid.uuid4()
        variants = [_variant(product_id=pid) for _ in range(3)]
        attrs = [_product_attr_value(product_id=pid) for _ in range(2)]
        product = _product(product_id=pid, variants=variants, attributes=attrs)
        assert len(product.variants) == 3
        assert len(product.attributes) == 2

    def test_inherits_from_base_model(self) -> None:
        """ProductReadModel must inherit from pydantic.BaseModel, not CamelModel."""
        assert issubclass(ProductReadModel, BaseModel)

    def test_serialization_round_trip(self) -> None:
        """model_dump -> model_validate round-trip preserves all fields."""
        pid = uuid.uuid4()
        variant = _variant(product_id=pid, skus=[_sku(product_id=pid)])
        attr_val = _product_attr_value(product_id=pid)
        original = _product(product_id=pid, variants=[variant], attributes=[attr_val])

        data = original.model_dump()
        restored = ProductReadModel.model_validate(data)

        assert restored.id == original.id
        assert restored.slug == original.slug
        assert restored.status == original.status
        assert len(restored.variants) == 1
        assert len(restored.attributes) == 1
        assert isinstance(restored.variants[0], ProductVariantReadModel)
        assert isinstance(restored.variants[0].skus[0], SKUReadModel)

    def test_json_round_trip(self) -> None:
        """model_dump_json -> model_validate_json preserves all fields."""
        pid = uuid.uuid4()
        original = _product(
            product_id=pid,
            variants=[_variant(product_id=pid, skus=[_sku(product_id=pid)])],
            attributes=[_product_attr_value(product_id=pid)],
        )
        json_str = original.model_dump_json()
        # Verify it is valid JSON
        parsed = json.loads(json_str)
        assert "id" in parsed
        assert "variants" in parsed
        assert "attributes" in parsed

        restored = ProductReadModel.model_validate_json(json_str)
        assert restored.id == original.id
        assert len(restored.variants) == 1

    def test_empty_tags_list_is_valid(self) -> None:
        """tags=[] is a valid edge case."""
        product = ProductReadModel(
            id=uuid.uuid4(),
            slug="no-tags",
            title_i18n={"en": "No Tags"},
            description_i18n={"en": "Desc"},
            status="draft",
            brand_id=uuid.uuid4(),
            primary_category_id=uuid.uuid4(),
            tags=[],
            version=1,
            created_at=_NOW,
            updated_at=_NOW,
            variants=[],
            attributes=[],
        )
        assert product.tags == []

    @pytest.mark.parametrize("status_str", ["active", "draft", "published", "archived", "CUSTOM"])
    def test_status_accepts_any_string(self, status_str: str) -> None:
        """status is a plain str — any string value is valid."""
        product = ProductReadModel(
            id=uuid.uuid4(),
            slug="any-status",
            title_i18n={"en": "X"},
            description_i18n={"en": "Y"},
            status=status_str,
            brand_id=uuid.uuid4(),
            primary_category_id=uuid.uuid4(),
            tags=[],
            version=1,
            created_at=_NOW,
            updated_at=_NOW,
            variants=[],
            attributes=[],
        )
        assert product.status == status_str

    def test_min_price_max_price_are_int_or_none(self) -> None:
        """min_price and max_price are plain int|None (no currency attached)."""
        product = _product()
        assert product.min_price is None
        assert product.max_price is None

        product2 = ProductReadModel(
            id=uuid.uuid4(),
            slug="priced",
            title_i18n={"en": "Priced"},
            description_i18n={"en": "Desc"},
            status="active",
            brand_id=uuid.uuid4(),
            primary_category_id=uuid.uuid4(),
            tags=[],
            version=1,
            created_at=_NOW,
            updated_at=_NOW,
            min_price=100,
            max_price=9999,
            variants=[],
            attributes=[],
        )
        assert isinstance(product2.min_price, int)
        assert isinstance(product2.max_price, int)


# ---------------------------------------------------------------------------
# ProductListItemReadModel
# ---------------------------------------------------------------------------


class TestProductListItemReadModel:
    """Tests for ProductListItemReadModel (lightweight list-row DTO)."""

    def test_instantiation_with_valid_fields(self) -> None:
        """Happy path: all required fields set."""
        item_id = uuid.uuid4()
        model = ProductListItemReadModel(
            id=item_id,
            slug="my-product",
            title_i18n={"en": "My Product"},
            status="active",
            brand_id=uuid.uuid4(),
            primary_category_id=uuid.uuid4(),
            version=1,
            created_at=_NOW,
            updated_at=_NOW,
        )
        assert model.id == item_id
        assert model.slug == "my-product"
        assert model.status == "active"

    def test_status_is_plain_string(self) -> None:
        """status is a plain str — not an enum."""
        item = _list_item()
        assert isinstance(item.status, str)
        assert type(item.status) is str

    def test_title_i18n_is_dict(self) -> None:
        """title_i18n is a dict."""
        item = _list_item()
        assert isinstance(item.title_i18n, dict)

    def test_no_skus_or_attributes_fields(self) -> None:
        """ProductListItemReadModel is lightweight: no skus/attributes fields."""
        item = _list_item()
        assert not hasattr(item, "skus"), "lightweight model must not have skus"
        assert not hasattr(item, "attributes"), "lightweight model must not have attributes"
        assert not hasattr(item, "description_i18n"), (
            "lightweight model must not have description_i18n"
        )

    def test_version_is_int(self) -> None:
        """version is an integer."""
        item = _list_item()
        assert isinstance(item.version, int)

    def test_timestamps_are_datetime(self) -> None:
        """created_at and updated_at are datetime objects."""
        item = _list_item()
        assert isinstance(item.created_at, datetime)
        assert isinstance(item.updated_at, datetime)

    def test_inherits_from_base_model(self) -> None:
        """ProductListItemReadModel must inherit from pydantic.BaseModel."""
        assert issubclass(ProductListItemReadModel, BaseModel)

    def test_serialization_round_trip(self) -> None:
        """model_dump -> model_validate round-trip preserves all fields."""
        original = _list_item()
        data = original.model_dump()
        restored = ProductListItemReadModel.model_validate(data)
        assert restored.id == original.id
        assert restored.slug == original.slug
        assert restored.status == original.status
        assert restored.version == original.version


# ---------------------------------------------------------------------------
# ProductListReadModel (pagination)
# ---------------------------------------------------------------------------


class TestProductListReadModel:
    """Tests for ProductListReadModel (paginated product list DTO)."""

    def test_instantiation_with_items(self) -> None:
        """Happy path: paginated list with items and metadata."""
        items = [_list_item() for _ in range(3)]
        model = ProductListReadModel(items=items, total=100, offset=0, limit=20)
        assert len(model.items) == 3
        assert model.total == 100
        assert model.offset == 0
        assert model.limit == 20

    def test_instantiation_empty_items(self) -> None:
        """Edge case: empty items list is valid."""
        model = ProductListReadModel(items=[], total=0, offset=0, limit=20)
        assert model.items == []
        assert model.total == 0

    def test_items_are_product_list_item_models(self) -> None:
        """items field contains ProductListItemReadModel instances."""
        items = [_list_item(), _list_item()]
        model = ProductListReadModel(items=items, total=2, offset=0, limit=10)
        assert all(isinstance(item, ProductListItemReadModel) for item in model.items)

    def test_total_is_int(self) -> None:
        """total is an integer."""
        model = ProductListReadModel(items=[], total=42, offset=0, limit=10)
        assert isinstance(model.total, int)
        assert model.total == 42

    def test_offset_is_int(self) -> None:
        """offset is an integer."""
        model = ProductListReadModel(items=[], total=100, offset=20, limit=10)
        assert isinstance(model.offset, int)
        assert model.offset == 20

    def test_limit_is_int(self) -> None:
        """limit is an integer."""
        model = ProductListReadModel(items=[], total=100, offset=0, limit=50)
        assert isinstance(model.limit, int)
        assert model.limit == 50

    @pytest.mark.parametrize(
        "total,offset,limit",
        [
            (0, 0, 1),
            (1, 0, 10),
            (500, 490, 10),
            (1000, 0, 100),
            (999999, 999990, 10),
        ],
    )
    def test_pagination_boundary_values(self, total: int, offset: int, limit: int) -> None:
        """Pagination fields accept various valid combinations."""
        model = ProductListReadModel(items=[], total=total, offset=offset, limit=limit)
        assert model.total == total
        assert model.offset == offset
        assert model.limit == limit

    def test_inherits_from_base_model(self) -> None:
        """ProductListReadModel must inherit from pydantic.BaseModel."""
        assert issubclass(ProductListReadModel, BaseModel)

    def test_serialization_round_trip(self) -> None:
        """model_dump -> model_validate round-trip preserves pagination fields and items."""
        items = [_list_item(), _list_item()]
        original = ProductListReadModel(items=items, total=50, offset=10, limit=20)
        data = original.model_dump()
        restored = ProductListReadModel.model_validate(data)
        assert len(restored.items) == 2
        assert restored.total == 50
        assert restored.offset == 10
        assert restored.limit == 20

    def test_json_round_trip(self) -> None:
        """model_dump_json -> model_validate_json preserves all fields."""
        items = [_list_item()]
        original = ProductListReadModel(items=items, total=1, offset=0, limit=10)
        json_str = original.model_dump_json()
        parsed = json.loads(json_str)
        assert "items" in parsed
        assert "total" in parsed
        assert "offset" in parsed
        assert "limit" in parsed
        restored = ProductListReadModel.model_validate_json(json_str)
        assert restored.total == 1
        assert len(restored.items) == 1


# ---------------------------------------------------------------------------
# No domain imports — read_models.py architecture guard
# ---------------------------------------------------------------------------


class TestNoDomainImportsInReadModels:
    """Verify read_models.py does not import domain types."""

    def test_status_field_is_not_domain_enum(self) -> None:
        """ProductReadModel.status and ProductListItemReadModel.status are str fields.

        The domain ProductStatus enum must never appear in read_models.py.
        This test imports the module and confirms the 'status' fields accept
        arbitrary strings, which would fail if they were typed as the domain enum.
        """
        product = _product()
        # Assign a known enum string value and verify it's stored as str
        assert product.status == "active"
        assert type(product.status) is str

    def test_read_models_module_no_domain_catalog_import(self) -> None:
        """read_models.py must not import from the catalog domain layer."""
        import ast
        import pathlib

        source = pathlib.Path("src/modules/catalog/application/queries/read_models.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("src.modules.catalog.domain"), (
                    f"read_models.py imports domain module: {node.module}"
                )
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("src.modules.catalog.domain"), (
                        f"read_models.py imports domain module: {alias.name}"
                    )

    def test_read_models_module_no_sqlalchemy_import(self) -> None:
        """read_models.py must not import SQLAlchemy (presentation/infra concern)."""
        import ast
        import pathlib

        source = pathlib.Path("src/modules/catalog/application/queries/read_models.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("sqlalchemy"), (
                    f"read_models.py imports sqlalchemy: {node.module}"
                )

    def test_all_new_models_use_base_model_not_camel_model(self) -> None:
        """All 7 new read models inherit from BaseModel, not CamelModel."""
        models = [
            MoneyReadModel,
            VariantAttributePairReadModel,
            SKUReadModel,
            ProductAttributeValueReadModel,
            ProductReadModel,
            ProductListItemReadModel,
            ProductListReadModel,
        ]
        for model_cls in models:
            assert issubclass(model_cls, BaseModel), (
                f"{model_cls.__name__} must inherit from BaseModel"
            )
            # Verify it is NOT CamelModel by checking MRO class names
            mro_names = [c.__name__ for c in model_cls.__mro__]
            assert "CamelModel" not in mro_names, (
                f"{model_cls.__name__} must not inherit from CamelModel"
            )
