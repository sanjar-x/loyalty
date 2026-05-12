import uuid

from src.modules.catalog.application.commands.sync_media import compute_media_diff


def test_compute_diff_all_new():
    current = []
    incoming = [
        {
            "storage_object_id": str(uuid.uuid4()),
            "url": "https://cdn/a.webp",
            "role": "MAIN",
        }
    ]
    to_add, to_update, to_delete = compute_media_diff(current, incoming)
    assert len(to_add) == 1
    assert len(to_update) == 0
    assert len(to_delete) == 0


def test_compute_diff_delete_removed():
    sid = str(uuid.uuid4())
    current = [{"storage_object_id": sid, "id": str(uuid.uuid4()), "role": "MAIN"}]
    incoming = []
    _to_add, _to_update, to_delete = compute_media_diff(current, incoming)
    assert len(to_delete) == 1
    assert to_delete[0]["storage_object_id"] == sid


def test_compute_diff_update_changed_role():
    sid = str(uuid.uuid4())
    mid = str(uuid.uuid4())
    current = [
        {
            "storage_object_id": sid,
            "id": mid,
            "role": "GALLERY",
            "sort_order": 0,
            "variant_id": None,
        }
    ]
    incoming = [
        {"storage_object_id": sid, "role": "MAIN", "sort_order": 0, "variant_id": None}
    ]
    _to_add, to_update, _to_delete = compute_media_diff(current, incoming)
    assert len(to_update) == 1
    assert to_update[0]["role"] == "MAIN"


def test_compute_diff_no_change():
    sid = str(uuid.uuid4())
    mid = str(uuid.uuid4())
    current = [
        {
            "storage_object_id": sid,
            "id": mid,
            "role": "MAIN",
            "sort_order": 0,
            "variant_id": None,
        }
    ]
    incoming = [
        {"storage_object_id": sid, "role": "MAIN", "sort_order": 0, "variant_id": None}
    ]
    to_add, to_update, to_delete = compute_media_diff(current, incoming)
    assert len(to_add) == 0
    assert len(to_update) == 0
    assert len(to_delete) == 0


def test_compute_diff_external_urls():
    current = [
        {"url": "https://ext.com/old.jpg", "is_external": True, "id": str(uuid.uuid4())}
    ]
    incoming = [{"url": "https://ext.com/new.jpg", "is_external": True}]
    to_add, _to_update, to_delete = compute_media_diff(current, incoming)
    assert len(to_add) == 1
    assert len(to_delete) == 1
