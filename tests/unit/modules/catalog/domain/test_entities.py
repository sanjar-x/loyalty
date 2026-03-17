import pytest

from src.modules.catalog.domain.entities import Brand, Category
from src.modules.catalog.domain.events import BrandCreatedEvent, BrandLogoConfirmedEvent
from src.modules.catalog.domain.exceptions import InvalidLogoStateException
from src.modules.catalog.domain.value_objects import MediaProcessingStatus
from tests.factories.catalog_mothers import BrandMothers, CategoryMothers


def test_brand_init_logo_upload_sets_status_pending():
    # Arrange
    brand = Brand.create(name="Apple", slug="apple")

    # Act
    brand.init_logo_upload(
        object_key="raw_uploads/catalog/brands/test/logo_raw",
        content_type="image/png",
    )

    # Assert
    assert brand.logo_status == MediaProcessingStatus.PENDING_UPLOAD


def test_brand_init_logo_upload_emits_brand_created_event():
    """init_logo_upload() должен сгенерировать BrandCreatedEvent."""
    # Arrange
    brand = Brand.create(name="Apple", slug="apple")
    object_key = f"raw_uploads/catalog/brands/{brand.id}/logo_raw"

    # Act
    brand.init_logo_upload(object_key=object_key, content_type="image/png")

    # Assert
    events = brand.domain_events
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, BrandCreatedEvent)
    assert event.brand_id == brand.id
    assert event.object_key == object_key
    assert event.content_type == "image/png"
    assert event.aggregate_type == "Brand"


def test_brand_confirm_logo_upload_changes_status_to_processing():
    # Arrange
    brand = Brand.create(name="Apple", slug="apple")
    brand.init_logo_upload(
        object_key="raw_uploads/catalog/brands/test/logo_raw",
        content_type="image/png",
    )
    brand.clear_domain_events()  # очищаем BrandCreatedEvent

    # Act
    brand.confirm_logo_upload()

    # Assert
    assert brand.logo_status == MediaProcessingStatus.PROCESSING


def test_brand_confirm_logo_upload_emits_domain_event():
    """confirm_logo_upload() должен сгенерировать BrandLogoConfirmedEvent."""
    # Arrange
    brand = Brand.create(name="Apple", slug="apple")
    brand.init_logo_upload(
        object_key="raw_uploads/catalog/brands/test/logo_raw",
        content_type="image/png",
    )
    brand.clear_domain_events()

    # Act
    brand.confirm_logo_upload()

    # Assert
    events = brand.domain_events
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, BrandLogoConfirmedEvent)
    assert event.brand_id == brand.id
    assert event.aggregate_type == "Brand"
    assert event.aggregate_id == str(brand.id)
    assert event.event_type == "BrandLogoConfirmedEvent"


def test_brand_confirm_logo_upload_raises_error_when_invalid_state():
    # Arrange
    brand = Brand.create(name="Apple", slug="apple")

    # Act & Assert
    with pytest.raises(InvalidLogoStateException) as exc_info:
        brand.confirm_logo_upload()

    assert (
        exc_info.value.details["expected_status"]  # ty:ignore[not-subscriptable]
        == MediaProcessingStatus.PENDING_UPLOAD
    )


def test_brand_complete_logo_processing_sets_completed():
    # Arrange
    brand = Brand.create(name="Apple", slug="apple")
    brand.init_logo_upload(
        object_key="raw_uploads/catalog/brands/test/logo_raw",
        content_type="image/png",
    )
    brand.confirm_logo_upload()
    url = "https://example.com/logo.webp"

    # Act
    brand.complete_logo_processing(
        url=url,
        object_key="processed/catalog/brands/test/logo.webp",
        content_type="image/webp",
        size_bytes=2048,
    )

    # Assert
    assert brand.logo_status == MediaProcessingStatus.COMPLETED
    assert brand.logo_url == url


def test_brand_fail_logo_processing_sets_failed():
    # Arrange
    brand = Brand.create(name="Apple", slug="apple")
    brand.init_logo_upload(
        object_key="raw_uploads/catalog/brands/test/logo_raw",
        content_type="image/png",
    )
    brand.confirm_logo_upload()

    # Act
    brand.fail_logo_processing()

    # Assert
    assert brand.logo_status == MediaProcessingStatus.FAILED


def test_brand_clear_domain_events():
    """clear_domain_events() очищает накопленные события."""
    # Arrange
    brand = Brand.create(name="Apple", slug="apple")
    brand.init_logo_upload(
        object_key="raw_uploads/catalog/brands/test/logo_raw",
        content_type="image/png",
    )
    assert len(brand.domain_events) == 1

    # Act
    brand.clear_domain_events()

    # Assert
    assert len(brand.domain_events) == 0


# --- Brand FSM — invalid transition tests ---


def test_brand_confirm_upload_from_completed_raises():
    brand = BrandMothers.with_completed_logo()
    with pytest.raises(InvalidLogoStateException):
        brand.confirm_logo_upload()


def test_brand_complete_processing_from_pending_raises():
    brand = BrandMothers.with_pending_logo()
    with pytest.raises(InvalidLogoStateException):
        brand.complete_logo_processing(
            url="https://cdn.test/logo.webp",
            object_key="processed/test/logo.webp",
            content_type="image/webp",
            size_bytes=1024,
        )


def test_brand_fail_processing_from_pending_raises():
    brand = BrandMothers.with_pending_logo()
    with pytest.raises(InvalidLogoStateException):
        brand.fail_logo_processing()


# --- Category depth enforcement ---


def test_category_create_child_increments_level():
    root = CategoryMothers.root()
    child = CategoryMothers.child(parent=root)
    assert child.level == root.level + 1


def test_category_create_child_builds_full_slug():
    root = CategoryMothers.root(slug="electronics")
    child = Category.create_child(name="Phones", slug="phones", parent=root)
    assert child.full_slug == "electronics/phones"


def test_category_deep_nested_builds_chain():
    categories = CategoryMothers.deep_nested(depth=3)
    assert len(categories) == 3
    assert categories[0].level == 0
    assert categories[1].level == 1
    assert categories[2].level == 2
