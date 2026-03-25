from src.modules.storage.domain.value_objects import StorageStatus


def test_storage_status_values():
    assert StorageStatus.PENDING_UPLOAD == "PENDING_UPLOAD"
    assert StorageStatus.PROCESSING == "PROCESSING"
    assert StorageStatus.COMPLETED == "COMPLETED"
    assert StorageStatus.FAILED == "FAILED"


def test_storage_status_is_terminal():
    assert StorageStatus.COMPLETED.is_terminal is True
    assert StorageStatus.FAILED.is_terminal is True
    assert StorageStatus.PENDING_UPLOAD.is_terminal is False
    assert StorageStatus.PROCESSING.is_terminal is False
