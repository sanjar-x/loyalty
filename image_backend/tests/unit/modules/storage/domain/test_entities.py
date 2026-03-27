"""Tests for StorageFile domain entity."""

import uuid

from src.modules.storage.domain.entities import StorageFile
from src.modules.storage.domain.value_objects import StorageStatus


class TestStorageFileCreate:
    """Factory method create() behaviour."""

    def test_create_generates_a_uuid(self):
        sf = StorageFile.create(
            bucket_name="b",
            object_key="raw/x/f.jpg",
            content_type="image/jpeg",
        )
        assert isinstance(sf.id, uuid.UUID)

    def test_create_sets_status_to_pending_upload(self):
        sf = StorageFile.create(
            bucket_name="b",
            object_key="raw/x/f.jpg",
            content_type="image/jpeg",
        )
        assert sf.status == StorageStatus.PENDING_UPLOAD

    def test_create_sets_required_fields_correctly(self):
        sf = StorageFile.create(
            bucket_name="test-bucket",
            object_key="raw/abc/photo.jpg",
            content_type="image/jpeg",
            size_bytes=1024,
            owner_module="catalog",
            filename="photo.jpg",
        )
        assert sf.bucket_name == "test-bucket"
        assert sf.object_key == "raw/abc/photo.jpg"
        assert sf.content_type == "image/jpeg"
        assert sf.size_bytes == 1024
        assert sf.owner_module == "catalog"
        assert sf.filename == "photo.jpg"

    def test_two_creates_produce_different_ids(self):
        sf1 = StorageFile.create(
            bucket_name="b",
            object_key="raw/x/f.jpg",
            content_type="image/jpeg",
        )
        sf2 = StorageFile.create(
            bucket_name="b",
            object_key="raw/x/f.jpg",
            content_type="image/jpeg",
        )
        assert sf1.id != sf2.id


class TestStorageFileDefaults:
    """Default field values after create()."""

    def test_size_bytes_defaults_to_zero(self):
        sf = StorageFile.create(
            bucket_name="b",
            object_key="k",
            content_type="image/png",
        )
        assert sf.size_bytes == 0

    def test_is_latest_defaults_to_true(self):
        sf = StorageFile.create(
            bucket_name="b",
            object_key="k",
            content_type="image/png",
        )
        assert sf.is_latest is True

    def test_url_defaults_to_none(self):
        sf = StorageFile.create(
            bucket_name="b",
            object_key="k",
            content_type="image/png",
        )
        assert sf.url is None

    def test_image_variants_defaults_to_none(self):
        sf = StorageFile.create(
            bucket_name="b",
            object_key="k",
            content_type="image/png",
        )
        assert sf.image_variants is None

    def test_owner_module_defaults_to_none(self):
        sf = StorageFile.create(
            bucket_name="b",
            object_key="k",
            content_type="image/png",
        )
        assert sf.owner_module is None

    def test_version_id_defaults_to_none(self):
        sf = StorageFile.create(
            bucket_name="b",
            object_key="k",
            content_type="image/png",
        )
        assert sf.version_id is None

    def test_etag_defaults_to_none(self):
        sf = StorageFile.create(
            bucket_name="b",
            object_key="k",
            content_type="image/png",
        )
        assert sf.etag is None

    def test_content_encoding_defaults_to_none(self):
        sf = StorageFile.create(
            bucket_name="b",
            object_key="k",
            content_type="image/png",
        )
        assert sf.content_encoding is None

    def test_cache_control_defaults_to_none(self):
        sf = StorageFile.create(
            bucket_name="b",
            object_key="k",
            content_type="image/png",
        )
        assert sf.cache_control is None

    def test_filename_defaults_to_none(self):
        sf = StorageFile.create(
            bucket_name="b",
            object_key="k",
            content_type="image/png",
        )
        assert sf.filename is None

    def test_created_at_defaults_to_none(self):
        sf = StorageFile.create(
            bucket_name="b",
            object_key="k",
            content_type="image/png",
        )
        assert sf.created_at is None

    def test_last_modified_in_s3_defaults_to_none(self):
        sf = StorageFile.create(
            bucket_name="b",
            object_key="k",
            content_type="image/png",
        )
        assert sf.last_modified_in_s3 is None


class TestStorageFileMutation:
    """Entity fields can be mutated after creation."""

    def test_can_complete_a_storage_file(self):
        sf = StorageFile.create(
            bucket_name="b",
            object_key="raw/x/f.jpg",
            content_type="image/jpeg",
            filename="f.jpg",
        )
        sf.status = StorageStatus.COMPLETED
        sf.url = "https://cdn.example.com/public/x.webp"
        sf.image_variants = [
            {
                "size": "thumbnail",
                "width": 150,
                "height": 150,
                "url": "https://cdn.example.com/public/x_thumb.webp",
            },
        ]
        assert sf.status == StorageStatus.COMPLETED
        assert sf.url.endswith(".webp")
        assert len(sf.image_variants) == 1
