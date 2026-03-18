"""Tests for Product / SKU / ProductAttribute presentation schemas."""

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.modules.catalog.presentation.schemas import (
    MoneySchema,
    ProductAttributeAssignRequest,
    ProductAttributeAssignResponse,
    ProductAttributeResponse,
    ProductCreateRequest,
    ProductCreateResponse,
    ProductListItemResponse,
    ProductListResponse,
    ProductResponse,
    ProductStatusChangeRequest,
    ProductUpdateRequest,
    SKUCreateRequest,
    SKUCreateResponse,
    SKUResponse,
    SKUUpdateRequest,
    VariantAttributePairSchema,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(tz=UTC)


# ---------------------------------------------------------------------------
# MoneySchema
# ---------------------------------------------------------------------------


class TestMoneySchema:
    """Validation for MoneySchema (amount + currency)."""

    def test_valid_money(self) -> None:
        m = MoneySchema(amount=1000, currency="USD")
        assert m.amount == 1000
        assert m.currency == "USD"

    def test_zero_amount_accepted(self) -> None:
        m = MoneySchema(amount=0, currency="EUR")
        assert m.amount == 0

    def test_negative_amount_rejected(self) -> None:
        with pytest.raises(ValidationError, match="amount"):
            MoneySchema(amount=-1, currency="USD")

    @pytest.mark.parametrize("currency", ["US", "USDD", "us", "12", ""])
    def test_invalid_currency_rejected(self, currency: str) -> None:
        with pytest.raises(ValidationError, match="currency"):
            MoneySchema(amount=100, currency=currency)

    @pytest.mark.parametrize("currency", ["USD", "EUR", "RUB", "GBP"])
    def test_valid_currencies_accepted(self, currency: str) -> None:
        m = MoneySchema(amount=100, currency=currency)
        assert m.currency == currency

    def test_lowercase_currency_rejected(self) -> None:
        with pytest.raises(ValidationError, match="currency"):
            MoneySchema(amount=100, currency="usd")

    def test_camel_case_serialization(self) -> None:
        m = MoneySchema(amount=500, currency="USD")
        data = m.model_dump(by_alias=True)
        assert data == {"amount": 500, "currency": "USD"}


# ---------------------------------------------------------------------------
# VariantAttributePairSchema
# ---------------------------------------------------------------------------


class TestVariantAttributePairSchema:
    """Validation for VariantAttributePairSchema."""

    def test_valid_pair(self) -> None:
        aid, vid = _uuid(), _uuid()
        pair = VariantAttributePairSchema(attribute_id=aid, attribute_value_id=vid)
        assert pair.attribute_id == aid
        assert pair.attribute_value_id == vid

    def test_camel_case_aliases(self) -> None:
        aid, vid = _uuid(), _uuid()
        pair = VariantAttributePairSchema(attribute_id=aid, attribute_value_id=vid)
        data = pair.model_dump(by_alias=True)
        assert "attributeId" in data
        assert "attributeValueId" in data

    def test_missing_attribute_id_rejected(self) -> None:
        with pytest.raises(ValidationError, match="attributeId"):
            VariantAttributePairSchema.model_validate({"attributeValueId": str(_uuid())})

    def test_missing_attribute_value_id_rejected(self) -> None:
        with pytest.raises(ValidationError, match="attributeValueId"):
            VariantAttributePairSchema.model_validate({"attributeId": str(_uuid())})


# ---------------------------------------------------------------------------
# ProductCreateRequest
# ---------------------------------------------------------------------------


class TestProductCreateRequest:
    """Validation for ProductCreateRequest."""

    def test_valid_creation(self) -> None:
        req = ProductCreateRequest(
            title_i18n={"en": "Test Product"},
            slug="test-product",
            brand_id=_uuid(),
            primary_category_id=_uuid(),
        )
        assert req.slug == "test-product"
        assert req.title_i18n == {"en": "Test Product"}
        assert req.description_i18n == {}
        assert req.tags == []
        assert req.supplier_id is None
        assert req.country_of_origin is None

    def test_all_fields(self) -> None:
        bid, cid, sid = _uuid(), _uuid(), _uuid()
        req = ProductCreateRequest(
            title_i18n={"en": "Full Product", "ru": "Полный товар"},
            slug="full-product",
            brand_id=bid,
            primary_category_id=cid,
            description_i18n={"en": "A description"},
            supplier_id=sid,
            country_of_origin="US",
            tags=["new", "sale"],
        )
        assert req.brand_id == bid
        assert req.supplier_id == sid
        assert req.country_of_origin == "US"
        assert req.tags == ["new", "sale"]

    def test_missing_title_rejected(self) -> None:
        with pytest.raises(ValidationError, match="titleI18N"):
            ProductCreateRequest.model_validate(
                {
                    "slug": "test",
                    "brandId": str(_uuid()),
                    "primaryCategoryId": str(_uuid()),
                }
            )

    def test_missing_slug_rejected(self) -> None:
        with pytest.raises(ValidationError, match="slug"):
            ProductCreateRequest(
                title_i18n={"en": "Test"},
                brand_id=_uuid(),
                primary_category_id=_uuid(),
            )  # type: ignore[call-arg]

    def test_missing_brand_id_rejected(self) -> None:
        with pytest.raises(ValidationError, match="brandId"):
            ProductCreateRequest.model_validate(
                {
                    "titleI18N": {"en": "Test"},
                    "slug": "test",
                    "primaryCategoryId": str(_uuid()),
                }
            )

    def test_empty_title_i18n_rejected(self) -> None:
        with pytest.raises(ValidationError, match="title_i18n"):
            ProductCreateRequest(
                title_i18n={},
                slug="test",
                brand_id=_uuid(),
                primary_category_id=_uuid(),
            )

    @pytest.mark.parametrize(
        "slug",
        ["valid-slug", "abc123", "a-b-c", "test", "product-123"],
    )
    def test_slug_valid_patterns(self, slug: str) -> None:
        req = ProductCreateRequest(
            title_i18n={"en": "T"},
            slug=slug,
            brand_id=_uuid(),
            primary_category_id=_uuid(),
        )
        assert req.slug == slug

    @pytest.mark.parametrize(
        "slug",
        ["UPPERCASE", "has spaces", "special!char", "under_score", "CamelCase"],
    )
    def test_slug_invalid_patterns_rejected(self, slug: str) -> None:
        with pytest.raises(ValidationError, match="slug"):
            ProductCreateRequest(
                title_i18n={"en": "T"},
                slug=slug,
                brand_id=_uuid(),
                primary_category_id=_uuid(),
            )

    def test_slug_max_length_255(self) -> None:
        with pytest.raises(ValidationError, match="slug"):
            ProductCreateRequest(
                title_i18n={"en": "T"},
                slug="a" * 256,
                brand_id=_uuid(),
                primary_category_id=_uuid(),
            )

    def test_slug_at_max_length_accepted(self) -> None:
        req = ProductCreateRequest(
            title_i18n={"en": "T"},
            slug="a" * 255,
            brand_id=_uuid(),
            primary_category_id=_uuid(),
        )
        assert len(req.slug) == 255

    def test_country_of_origin_max_length_2(self) -> None:
        with pytest.raises(ValidationError, match="country_of_origin"):
            ProductCreateRequest(
                title_i18n={"en": "T"},
                slug="test",
                brand_id=_uuid(),
                primary_category_id=_uuid(),
                country_of_origin="USA",
            )

    def test_camel_case_serialization(self) -> None:
        bid, cid = _uuid(), _uuid()
        req = ProductCreateRequest(
            title_i18n={"en": "T"},
            slug="test",
            brand_id=bid,
            primary_category_id=cid,
        )
        data = req.model_dump(by_alias=True)
        assert "titleI18N" in data
        assert "brandId" in data
        assert "primaryCategoryId" in data
        assert "descriptionI18N" in data
        assert "supplierId" in data
        assert "countryOfOrigin" in data


# ---------------------------------------------------------------------------
# ProductCreateResponse
# ---------------------------------------------------------------------------


class TestProductCreateResponse:
    """Validation for ProductCreateResponse."""

    def test_valid_response(self) -> None:
        pid = _uuid()
        resp = ProductCreateResponse(id=pid, message="Product created")
        assert resp.id == pid
        assert resp.message == "Product created"


# ---------------------------------------------------------------------------
# ProductUpdateRequest
# ---------------------------------------------------------------------------


class TestProductUpdateRequest:
    """Validation for ProductUpdateRequest (PATCH semantics).

    Uses model_validate for most tests because supplier_id and
    country_of_origin use the ``...`` sentinel default, which Pydantic
    treats as required when using the Python constructor.  The JSON
    deserialization path (model_validate) is the actual usage path in
    the FastAPI endpoint.
    """

    @staticmethod
    def _base_payload(**overrides: object) -> dict[str, object]:
        """Build a minimal valid ProductUpdateRequest payload with sentinels."""
        base: dict[str, object] = {
            "supplierId": None,
            "countryOfOrigin": None,
        }
        base.update(overrides)
        return base

    def test_empty_update_rejected(self) -> None:
        """Empty payload is rejected -- sentinel fields treated as required."""
        with pytest.raises(ValidationError):
            ProductUpdateRequest.model_validate({})

    def test_sentinel_null_alone_passes_validator(self) -> None:
        """Explicit null for sentinel fields counts as 'provided'."""
        req = ProductUpdateRequest.model_validate({"supplierId": None, "countryOfOrigin": None})
        assert req.supplier_id is None
        assert req.country_of_origin is None

    def test_title_only_accepted(self) -> None:
        req = ProductUpdateRequest.model_validate(self._base_payload(titleI18N={"en": "New Title"}))
        assert req.title_i18n == {"en": "New Title"}

    def test_slug_only_accepted(self) -> None:
        req = ProductUpdateRequest.model_validate(self._base_payload(slug="new-slug"))
        assert req.slug == "new-slug"

    def test_brand_id_only_accepted(self) -> None:
        bid = _uuid()
        req = ProductUpdateRequest.model_validate(self._base_payload(brandId=str(bid)))
        assert req.brand_id == bid

    def test_tags_only_accepted(self) -> None:
        req = ProductUpdateRequest.model_validate(self._base_payload(tags=["sale"]))
        assert req.tags == ["sale"]

    def test_supplier_id_omitted_raises_required(self) -> None:
        """Omitting supplierId from payload triggers required-field error."""
        with pytest.raises(ValidationError, match="supplierId"):
            ProductUpdateRequest.model_validate({"titleI18N": {"en": "T"}, "countryOfOrigin": None})

    def test_supplier_id_with_value(self) -> None:
        sid = _uuid()
        req = ProductUpdateRequest.model_validate({"supplierId": str(sid), "countryOfOrigin": None})
        assert req.supplier_id == sid

    def test_country_of_origin_explicit_none_accepted(self) -> None:
        req = ProductUpdateRequest.model_validate({"countryOfOrigin": None, "supplierId": None})
        assert req.country_of_origin is None

    def test_slug_validation_on_update(self) -> None:
        with pytest.raises(ValidationError, match="slug"):
            ProductUpdateRequest.model_validate(self._base_payload(slug="INVALID SLUG"))

    def test_empty_title_i18n_rejected_on_update(self) -> None:
        with pytest.raises(ValidationError, match="titleI18N"):
            ProductUpdateRequest.model_validate(self._base_payload(titleI18N={}))

    def test_multiple_fields_accepted(self) -> None:
        req = ProductUpdateRequest.model_validate(
            self._base_payload(
                titleI18N={"en": "Updated"},
                slug="updated",
                tags=["updated"],
                version=2,
            )
        )
        assert req.title_i18n == {"en": "Updated"}
        assert req.slug == "updated"
        assert req.version == 2


# ---------------------------------------------------------------------------
# ProductStatusChangeRequest
# ---------------------------------------------------------------------------


class TestProductStatusChangeRequest:
    """Validation for ProductStatusChangeRequest."""

    def test_valid_status(self) -> None:
        req = ProductStatusChangeRequest(status="active")
        assert req.status == "active"

    def test_missing_status_rejected(self) -> None:
        with pytest.raises(ValidationError, match="status"):
            ProductStatusChangeRequest()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# SKUCreateRequest
# ---------------------------------------------------------------------------


class TestSKUCreateRequest:
    """Validation for SKUCreateRequest."""

    def test_valid_sku(self) -> None:
        req = SKUCreateRequest(
            sku_code="SKU-001",
            price_amount=1500,
            price_currency="USD",
        )
        assert req.sku_code == "SKU-001"
        assert req.price_amount == 1500
        assert req.price_currency == "USD"
        assert req.compare_at_price_amount is None
        assert req.is_active is True
        assert req.variant_attributes == []

    def test_negative_price_rejected(self) -> None:
        with pytest.raises(ValidationError, match="price_amount"):
            SKUCreateRequest(
                sku_code="SKU-001",
                price_amount=-1,
                price_currency="USD",
            )

    def test_zero_price_accepted(self) -> None:
        req = SKUCreateRequest(
            sku_code="SKU-FREE",
            price_amount=0,
            price_currency="USD",
        )
        assert req.price_amount == 0

    def test_invalid_price_currency_rejected(self) -> None:
        with pytest.raises(ValidationError, match="price_currency"):
            SKUCreateRequest(
                sku_code="SKU-001",
                price_amount=100,
                price_currency="usd",
            )

    def test_empty_sku_code_rejected(self) -> None:
        with pytest.raises(ValidationError, match="sku_code"):
            SKUCreateRequest(
                sku_code="",
                price_amount=100,
                price_currency="USD",
            )

    def test_sku_code_max_length_100(self) -> None:
        with pytest.raises(ValidationError, match="sku_code"):
            SKUCreateRequest(
                sku_code="A" * 101,
                price_amount=100,
                price_currency="USD",
            )

    def test_compare_at_price_negative_rejected(self) -> None:
        with pytest.raises(ValidationError, match="compare_at_price_amount"):
            SKUCreateRequest(
                sku_code="SKU-001",
                price_amount=100,
                price_currency="USD",
                compare_at_price_amount=-1,
            )

    def test_compare_at_price_zero_accepted(self) -> None:
        req = SKUCreateRequest(
            sku_code="SKU-001",
            price_amount=100,
            price_currency="USD",
            compare_at_price_amount=0,
        )
        assert req.compare_at_price_amount == 0

    def test_with_variant_attributes(self) -> None:
        aid, vid = _uuid(), _uuid()
        req = SKUCreateRequest(
            sku_code="SKU-001",
            price_amount=100,
            price_currency="USD",
            variant_attributes=[
                VariantAttributePairSchema(attribute_id=aid, attribute_value_id=vid)
            ],
        )
        assert len(req.variant_attributes) == 1
        assert req.variant_attributes[0].attribute_id == aid

    def test_camel_case_serialization(self) -> None:
        req = SKUCreateRequest(
            sku_code="SKU-001",
            price_amount=100,
            price_currency="USD",
        )
        data = req.model_dump(by_alias=True)
        assert "skuCode" in data
        assert "priceAmount" in data
        assert "priceCurrency" in data
        assert "compareAtPriceAmount" in data
        assert "isActive" in data
        assert "variantAttributes" in data


# ---------------------------------------------------------------------------
# SKUCreateResponse
# ---------------------------------------------------------------------------


class TestSKUCreateResponse:
    """Validation for SKUCreateResponse."""

    def test_valid_response(self) -> None:
        sid = _uuid()
        resp = SKUCreateResponse(id=sid, message="SKU created")
        assert resp.id == sid
        assert resp.message == "SKU created"


# ---------------------------------------------------------------------------
# SKUUpdateRequest
# ---------------------------------------------------------------------------


class TestSKUUpdateRequest:
    """Validation for SKUUpdateRequest (PATCH semantics with sentinel).

    Uses model_validate because compare_at_price_amount uses the ``...``
    sentinel default.
    """

    @staticmethod
    def _base_payload(**overrides: object) -> dict[str, object]:
        """Build a minimal valid SKUUpdateRequest payload (includes sentinel)."""
        base: dict[str, object] = {"compareAtPriceAmount": None}
        base.update(overrides)
        return base

    def test_valid_partial_update(self) -> None:
        req = SKUUpdateRequest.model_validate(self._base_payload(priceAmount=2000))
        assert req.price_amount == 2000

    def test_compare_at_price_omitted_is_required(self) -> None:
        """When compareAtPriceAmount is omitted, Pydantic rejects it as required."""
        with pytest.raises(ValidationError, match="compareAtPriceAmount"):
            SKUUpdateRequest.model_validate({"priceAmount": 100})

    def test_compare_at_price_null_accepted(self) -> None:
        """Explicit null for compare_at_price clears the value."""
        req = SKUUpdateRequest.model_validate({"priceAmount": 100, "compareAtPriceAmount": None})
        assert req.compare_at_price_amount is None

    def test_compare_at_price_explicit_value(self) -> None:
        req = SKUUpdateRequest.model_validate({"compareAtPriceAmount": 5000})
        assert req.compare_at_price_amount == 5000

    def test_negative_price_amount_rejected(self) -> None:
        with pytest.raises(ValidationError, match="priceAmount"):
            SKUUpdateRequest.model_validate(self._base_payload(priceAmount=-1))

    def test_invalid_price_currency_rejected(self) -> None:
        with pytest.raises(ValidationError, match="priceCurrency"):
            SKUUpdateRequest.model_validate(self._base_payload(priceCurrency="usd"))

    def test_empty_sku_code_rejected(self) -> None:
        with pytest.raises(ValidationError, match="skuCode"):
            SKUUpdateRequest.model_validate(self._base_payload(skuCode=""))

    def test_with_variant_attributes(self) -> None:
        aid, vid = _uuid(), _uuid()
        req = SKUUpdateRequest.model_validate(
            self._base_payload(
                variantAttributes=[{"attributeId": str(aid), "attributeValueId": str(vid)}],
            )
        )
        assert len(req.variant_attributes) == 1

    def test_version_field(self) -> None:
        req = SKUUpdateRequest.model_validate(self._base_payload(priceAmount=100, version=3))
        assert req.version == 3

    def test_camel_case_serialization(self) -> None:
        req = SKUUpdateRequest.model_validate(self._base_payload(skuCode="NEW-CODE"))
        data = req.model_dump(by_alias=True)
        assert "skuCode" in data
        assert "priceAmount" in data
        assert "priceCurrency" in data
        assert "compareAtPriceAmount" in data
        assert "isActive" in data
        assert "variantAttributes" in data


# ---------------------------------------------------------------------------
# SKUResponse
# ---------------------------------------------------------------------------


class TestSKUResponse:
    """Validation for SKUResponse."""

    def test_valid_response(self) -> None:
        sid, pid = _uuid(), _uuid()
        aid, vid = _uuid(), _uuid()
        now = _now()
        resp = SKUResponse(
            id=sid,
            product_id=pid,
            sku_code="SKU-001",
            variant_hash="abc123",
            price=MoneySchema(amount=1000, currency="USD"),
            is_active=True,
            version=1,
            created_at=now,
            updated_at=now,
            variant_attributes=[
                VariantAttributePairSchema(attribute_id=aid, attribute_value_id=vid)
            ],
        )
        assert resp.id == sid
        assert resp.price.amount == 1000
        assert resp.compare_at_price is None
        assert resp.deleted_at is None

    def test_with_compare_at_price(self) -> None:
        now = _now()
        resp = SKUResponse(
            id=_uuid(),
            product_id=_uuid(),
            sku_code="SKU-001",
            variant_hash="abc",
            price=MoneySchema(amount=1000, currency="USD"),
            compare_at_price=MoneySchema(amount=1500, currency="USD"),
            is_active=True,
            version=1,
            created_at=now,
            updated_at=now,
            variant_attributes=[],
        )
        assert resp.compare_at_price is not None
        assert resp.compare_at_price.amount == 1500

    def test_camel_case_serialization(self) -> None:
        now = _now()
        resp = SKUResponse(
            id=_uuid(),
            product_id=_uuid(),
            sku_code="SKU-001",
            variant_hash="abc",
            price=MoneySchema(amount=1000, currency="USD"),
            is_active=True,
            version=1,
            created_at=now,
            updated_at=now,
            variant_attributes=[],
        )
        data = resp.model_dump(by_alias=True)
        assert "productId" in data
        assert "skuCode" in data
        assert "variantHash" in data
        assert "isActive" in data
        assert "createdAt" in data
        assert "updatedAt" in data
        assert "deletedAt" in data
        assert "compareAtPrice" in data
        assert "variantAttributes" in data


# ---------------------------------------------------------------------------
# ProductAttributeAssignRequest / Response
# ---------------------------------------------------------------------------


class TestProductAttributeAssignRequest:
    """Validation for ProductAttributeAssignRequest."""

    def test_valid_assignment(self) -> None:
        aid, vid = _uuid(), _uuid()
        req = ProductAttributeAssignRequest(
            attribute_id=aid,
            attribute_value_id=vid,
        )
        assert req.attribute_id == aid
        assert req.attribute_value_id == vid

    def test_camel_case_aliases(self) -> None:
        req = ProductAttributeAssignRequest(
            attribute_id=_uuid(),
            attribute_value_id=_uuid(),
        )
        data = req.model_dump(by_alias=True)
        assert "attributeId" in data
        assert "attributeValueId" in data


class TestProductAttributeAssignResponse:
    """Validation for ProductAttributeAssignResponse."""

    def test_valid_response(self) -> None:
        pid = _uuid()
        resp = ProductAttributeAssignResponse(id=pid, message="Assigned")
        assert resp.id == pid
        assert resp.message == "Assigned"


# ---------------------------------------------------------------------------
# ProductAttributeResponse
# ---------------------------------------------------------------------------


class TestProductAttributeResponse:
    """Validation for ProductAttributeResponse."""

    def test_valid_response(self) -> None:
        pid, aid, vid, rid = _uuid(), _uuid(), _uuid(), _uuid()
        resp = ProductAttributeResponse(
            id=rid,
            product_id=pid,
            attribute_id=aid,
            attribute_value_id=vid,
        )
        assert resp.id == rid
        assert resp.product_id == pid
        assert resp.attribute_id == aid
        assert resp.attribute_value_id == vid

    def test_camel_case_serialization(self) -> None:
        resp = ProductAttributeResponse(
            id=_uuid(),
            product_id=_uuid(),
            attribute_id=_uuid(),
            attribute_value_id=_uuid(),
        )
        data = resp.model_dump(by_alias=True)
        assert "productId" in data
        assert "attributeId" in data
        assert "attributeValueId" in data


# ---------------------------------------------------------------------------
# ProductResponse
# ---------------------------------------------------------------------------


class TestProductResponse:
    """Validation for ProductResponse (full detail)."""

    def test_valid_full_response(self) -> None:
        pid, bid, cid = _uuid(), _uuid(), _uuid()
        now = _now()
        resp = ProductResponse(
            id=pid,
            slug="test-product",
            title_i18n={"en": "Test Product"},
            description_i18n={"en": "Description"},
            status="draft",
            brand_id=bid,
            primary_category_id=cid,
            tags=["new"],
            version=1,
            created_at=now,
            updated_at=now,
            skus=[],
            attributes=[],
        )
        assert resp.id == pid
        assert resp.slug == "test-product"
        assert resp.status == "draft"
        assert resp.supplier_id is None
        assert resp.country_of_origin is None
        assert resp.deleted_at is None
        assert resp.published_at is None
        assert resp.min_price is None
        assert resp.max_price is None
        assert resp.skus == []
        assert resp.attributes == []

    def test_with_nested_skus_and_attributes(self) -> None:
        pid, bid, cid = _uuid(), _uuid(), _uuid()
        now = _now()
        sku_resp = SKUResponse(
            id=_uuid(),
            product_id=pid,
            sku_code="SKU-001",
            variant_hash="abc",
            price=MoneySchema(amount=1000, currency="USD"),
            is_active=True,
            version=1,
            created_at=now,
            updated_at=now,
            variant_attributes=[],
        )
        attr_resp = ProductAttributeResponse(
            id=_uuid(),
            product_id=pid,
            attribute_id=_uuid(),
            attribute_value_id=_uuid(),
        )
        resp = ProductResponse(
            id=pid,
            slug="test",
            title_i18n={"en": "T"},
            description_i18n={},
            status="active",
            brand_id=bid,
            primary_category_id=cid,
            tags=[],
            version=1,
            created_at=now,
            updated_at=now,
            skus=[sku_resp],
            attributes=[attr_resp],
        )
        assert len(resp.skus) == 1
        assert len(resp.attributes) == 1

    def test_camel_case_serialization(self) -> None:
        now = _now()
        resp = ProductResponse(
            id=_uuid(),
            slug="test",
            title_i18n={"en": "T"},
            description_i18n={},
            status="draft",
            brand_id=_uuid(),
            primary_category_id=_uuid(),
            tags=[],
            version=1,
            created_at=now,
            updated_at=now,
            skus=[],
            attributes=[],
        )
        data = resp.model_dump(by_alias=True)
        assert "titleI18N" in data
        assert "descriptionI18N" in data
        assert "brandId" in data
        assert "primaryCategoryId" in data
        assert "supplierId" in data
        assert "countryOfOrigin" in data
        assert "publishedAt" in data
        assert "minPrice" in data
        assert "maxPrice" in data
        assert "deletedAt" in data
        assert "createdAt" in data
        assert "updatedAt" in data


# ---------------------------------------------------------------------------
# ProductListItemResponse
# ---------------------------------------------------------------------------


class TestProductListItemResponse:
    """Validation for ProductListItemResponse (lightweight)."""

    def test_valid_list_item(self) -> None:
        pid, bid, cid = _uuid(), _uuid(), _uuid()
        now = _now()
        item = ProductListItemResponse(
            id=pid,
            slug="test",
            title_i18n={"en": "T"},
            status="draft",
            brand_id=bid,
            primary_category_id=cid,
            version=1,
            created_at=now,
            updated_at=now,
        )
        assert item.id == pid
        assert item.slug == "test"

    def test_camel_case_serialization(self) -> None:
        now = _now()
        item = ProductListItemResponse(
            id=_uuid(),
            slug="test",
            title_i18n={"en": "T"},
            status="draft",
            brand_id=_uuid(),
            primary_category_id=_uuid(),
            version=1,
            created_at=now,
            updated_at=now,
        )
        data = item.model_dump(by_alias=True)
        assert "titleI18N" in data
        assert "brandId" in data
        assert "primaryCategoryId" in data
        assert "createdAt" in data
        assert "updatedAt" in data


# ---------------------------------------------------------------------------
# ProductListResponse
# ---------------------------------------------------------------------------


class TestProductListResponse:
    """Validation for ProductListResponse (paginated)."""

    def test_valid_list_response(self) -> None:
        resp = ProductListResponse(items=[], total=0, offset=0, limit=20)
        assert resp.items == []
        assert resp.total == 0
        assert resp.offset == 0
        assert resp.limit == 20

    def test_with_items(self) -> None:
        now = _now()
        item = ProductListItemResponse(
            id=_uuid(),
            slug="test",
            title_i18n={"en": "T"},
            status="draft",
            brand_id=_uuid(),
            primary_category_id=_uuid(),
            version=1,
            created_at=now,
            updated_at=now,
        )
        resp = ProductListResponse(items=[item], total=1, offset=0, limit=20)
        assert len(resp.items) == 1
        assert resp.total == 1


# ---------------------------------------------------------------------------
# CamelCase aliasing (cross-schema verification)
# ---------------------------------------------------------------------------


class TestCamelCaseAliasing:
    """Verify camelCase aliasing works across all product schemas."""

    def test_populate_by_alias(self) -> None:
        """Schemas can be populated using camelCase field names."""
        req = ProductCreateRequest.model_validate(
            {
                "titleI18N": {"en": "Test"},
                "slug": "test",
                "brandId": str(_uuid()),
                "primaryCategoryId": str(_uuid()),
            }
        )
        assert req.title_i18n == {"en": "Test"}

    def test_sku_create_populate_by_alias(self) -> None:
        req = SKUCreateRequest.model_validate(
            {
                "skuCode": "SKU-001",
                "priceAmount": 100,
                "priceCurrency": "USD",
            }
        )
        assert req.sku_code == "SKU-001"
        assert req.price_amount == 100

    def test_product_update_populate_by_alias(self) -> None:
        req = ProductUpdateRequest.model_validate(
            {
                "titleI18N": {"en": "Updated"},
                "supplierId": None,
                "countryOfOrigin": None,
            }
        )
        assert req.title_i18n == {"en": "Updated"}
