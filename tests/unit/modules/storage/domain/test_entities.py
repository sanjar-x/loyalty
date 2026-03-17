# tests/unit/modules/storage/domain/test_entities.py
"""Tests for Storage domain entity."""

import uuid

from tests.factories.storage_mothers import StorageFileMothers


class TestStorageFile:
    def test_create_sets_fields(self):
        sf = StorageFileMothers.pending()
        assert sf.bucket_name == "test-bucket"
        assert sf.content_type == "image/png"
        assert isinstance(sf.id, uuid.UUID)
        assert sf.is_latest is True

    def test_create_with_owner_module(self):
        sf = StorageFileMothers.pending(owner_module="identity")
        assert sf.owner_module == "identity"

    def test_create_active_has_size(self):
        sf = StorageFileMothers.active(size_bytes=2048)
        assert sf.size_bytes == 2048
        assert sf.content_type == "image/webp"
