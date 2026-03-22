# tests/unit/modules/catalog/domain/test_events.py
"""Tests for Catalog domain events — __post_init__ validators and aggregate_id auto-set."""

import uuid

import pytest

from src.modules.catalog.domain.events import (
    BrandLogoConfirmedEvent,
    BrandLogoProcessedEvent,
    BrandLogoUploadInitiatedEvent,
)


class TestBrandLogoUploadInitiatedEvent:
    def test_raises_value_error_when_brand_id_is_none(self):
        with pytest.raises(ValueError, match="brand_id is required"):
            BrandLogoUploadInitiatedEvent(brand_id=None, object_key="key", content_type="image/png")

    def test_auto_sets_aggregate_id_from_brand_id(self):
        brand_id: uuid.UUID = uuid.uuid4()
        event = BrandLogoUploadInitiatedEvent(
            brand_id=brand_id, object_key="key", content_type="image/png"
        )
        assert event.aggregate_id == str(brand_id)

    def test_fields_populated(self):
        brand_id: uuid.UUID = uuid.uuid4()
        event = BrandLogoUploadInitiatedEvent(
            brand_id=brand_id, object_key="brands/logo.png", content_type="image/png"
        )
        assert event.aggregate_type == "Brand"
        assert event.event_type == "BrandLogoUploadInitiatedEvent"
        assert event.object_key == "brands/logo.png"
        assert event.content_type == "image/png"

    def test_preserves_explicit_aggregate_id(self):
        brand_id = uuid.uuid4()
        custom_agg_id = "custom-id"
        event = BrandLogoUploadInitiatedEvent(
            brand_id=brand_id,
            aggregate_id=custom_agg_id,
            object_key="k",
            content_type="c",
        )
        assert event.aggregate_id == custom_agg_id


class TestBrandLogoConfirmedEvent:
    def test_raises_value_error_when_brand_id_is_none(self):
        with pytest.raises(ValueError, match="brand_id is required"):
            BrandLogoConfirmedEvent(brand_id=None)

    def test_auto_sets_aggregate_id_from_brand_id(self):
        brand_id: uuid.UUID = uuid.uuid4()
        event = BrandLogoConfirmedEvent(brand_id=brand_id)
        assert event.aggregate_id == str(brand_id)

    def test_fields_populated(self):
        event = BrandLogoConfirmedEvent(brand_id=uuid.uuid4())
        assert event.aggregate_type == "Brand"
        assert event.event_type == "BrandLogoConfirmedEvent"


class TestBrandLogoProcessedEvent:
    def test_raises_value_error_when_brand_id_is_none(self):
        with pytest.raises(ValueError, match="brand_id is required"):
            BrandLogoProcessedEvent(brand_id=None)

    def test_auto_sets_aggregate_id_from_brand_id(self):
        brand_id = uuid.uuid4()
        event = BrandLogoProcessedEvent(
            brand_id=brand_id,
            object_key="k",
            content_type="image/webp",
            size_bytes=1024,
        )
        assert event.aggregate_id == str(brand_id)

    def test_fields_populated(self):
        brand_id: uuid.UUID = uuid.uuid4()
        event = BrandLogoProcessedEvent(
            brand_id=brand_id,
            object_key="brands/logo.webp",
            content_type="image/webp",
            size_bytes=2048,
        )
        assert event.aggregate_type == "Brand"
        assert event.event_type == "BrandLogoProcessedEvent"
        assert event.object_key == "brands/logo.webp"
        assert event.size_bytes == 2048
