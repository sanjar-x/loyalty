# tests/unit/modules/catalog/domain/test_value_objects.py
"""Tests for Catalog domain value objects."""

from src.modules.catalog.domain.value_objects import MediaProcessingStatus


def test_media_processing_status_members():
    assert set(MediaProcessingStatus) == {
        MediaProcessingStatus.PENDING_UPLOAD,
        MediaProcessingStatus.PROCESSING,
        MediaProcessingStatus.COMPLETED,
        MediaProcessingStatus.FAILED,
    }
