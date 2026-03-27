"""Tests for StorageStatus value object."""

from src.modules.storage.domain.value_objects import StorageStatus


class TestStorageStatusValues:
    """All 4 enum members match their string representations."""

    def test_pending_upload_value(self):
        assert StorageStatus.PENDING_UPLOAD == "PENDING_UPLOAD"
        assert str(StorageStatus.PENDING_UPLOAD) == "PENDING_UPLOAD"

    def test_processing_value(self):
        assert StorageStatus.PROCESSING == "PROCESSING"
        assert str(StorageStatus.PROCESSING) == "PROCESSING"

    def test_completed_value(self):
        assert StorageStatus.COMPLETED == "COMPLETED"
        assert str(StorageStatus.COMPLETED) == "COMPLETED"

    def test_failed_value(self):
        assert StorageStatus.FAILED == "FAILED"
        assert str(StorageStatus.FAILED) == "FAILED"


class TestStorageStatusIsTerminal:
    """is_terminal property correctly identifies terminal/non-terminal states."""

    def test_completed_is_terminal(self):
        assert StorageStatus.COMPLETED.is_terminal is True

    def test_failed_is_terminal(self):
        assert StorageStatus.FAILED.is_terminal is True

    def test_pending_upload_is_not_terminal(self):
        assert StorageStatus.PENDING_UPLOAD.is_terminal is False

    def test_processing_is_not_terminal(self):
        assert StorageStatus.PROCESSING.is_terminal is False


class TestStorageStatusMembership:
    """Enum has exactly 4 members."""

    def test_enum_has_exactly_four_members(self):
        assert len(StorageStatus) == 4

    def test_enum_members_are_expected(self):
        names = {m.name for m in StorageStatus}
        assert names == {"PENDING_UPLOAD", "PROCESSING", "COMPLETED", "FAILED"}
