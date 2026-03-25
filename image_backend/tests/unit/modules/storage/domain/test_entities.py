import uuid
from src.modules.storage.domain.entities import StorageFile
from src.modules.storage.domain.value_objects import StorageStatus


def test_create_storage_file_has_new_fields():
    sf = StorageFile.create(
        bucket_name="test-bucket",
        object_key="raw/abc/photo.jpg",
        content_type="image/jpeg",
        filename="photo.jpg",
    )
    assert sf.status == StorageStatus.PENDING_UPLOAD
    assert sf.url is None
    assert sf.image_variants is None
    assert sf.filename == "photo.jpg"


def test_storage_file_complete():
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
