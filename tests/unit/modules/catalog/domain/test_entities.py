import uuid

import pytest

from src.modules.catalog.domain.entities import Brand
from src.modules.catalog.domain.exceptions import InvalidLogoStateException
from src.modules.catalog.domain.value_objects import MediaProcessingStatus


def test_brand_init_logo_upload_sets_status_pending():
    # Arrange
    brand = Brand.create(name="Apple", slug="apple")

    # Act
    brand.init_logo_upload()

    # Assert
    assert brand.logo_status == MediaProcessingStatus.PENDING_UPLOAD


def test_brand_confirm_logo_upload_changes_status_to_processing():
    # Arrange
    brand = Brand.create(name="Apple", slug="apple")
    brand.init_logo_upload()

    # Act
    brand.confirm_logo_upload()

    # Assert
    assert brand.logo_status == MediaProcessingStatus.PROCESSING


def test_brand_confirm_logo_upload_raises_error_when_invalid_state():
    # Arrange
    brand = Brand.create(name="Apple", slug="apple")

    # Act & Assert
    with pytest.raises(InvalidLogoStateException) as exc_info:
        brand.confirm_logo_upload()

    assert (
        exc_info.value.details["expected_status"]
        == MediaProcessingStatus.PENDING_UPLOAD
    )


def test_brand_complete_logo_processing_sets_completed():
    # Arrange
    brand = Brand.create(name="Apple", slug="apple")
    brand.init_logo_upload()
    brand.confirm_logo_upload()
    file_id = uuid.uuid4()
    url = "https://example.com/logo.webp"

    # Act
    brand.complete_logo_processing(file_id=file_id, url=url)

    # Assert
    assert brand.logo_status == MediaProcessingStatus.COMPLETED
    assert brand.logo_file_id == file_id
    assert brand.logo_url == url


def test_brand_fail_logo_processing_sets_failed():
    # Arrange
    brand = Brand.create(name="Apple", slug="apple")
    brand.init_logo_upload()
    brand.confirm_logo_upload()

    # Act
    brand.fail_logo_processing()

    # Assert
    assert brand.logo_status == MediaProcessingStatus.FAILED
