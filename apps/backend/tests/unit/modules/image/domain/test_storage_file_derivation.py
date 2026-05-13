"""Unit tests for IMG-007 derivation invariants on ``StorageFile``.

Covers:
* both ``parent_storage_object_id`` and ``derivation_kind`` must
  travel together (factory rejects partial provision).
* successful derivation construction populates both fields.
"""

from __future__ import annotations

import uuid

import pytest

from src.modules.image.domain.entities import StorageFile
from src.modules.image.domain.value_objects import DerivationKind


class TestStorageFileDerivation:
    def test_create_plain_upload_has_no_parent(self) -> None:
        sf = StorageFile.create(
            bucket_name="b",
            object_key="public/x.webp",
            content_type="image/webp",
        )
        assert sf.parent_storage_object_id is None
        assert sf.derivation_kind is None

    def test_create_derivation_populates_both_fields(self) -> None:
        parent = uuid.uuid4()
        sf = StorageFile.create(
            bucket_name="b",
            object_key="public/x_bg_removed.webp",
            content_type="image/webp",
            parent_storage_object_id=parent,
            derivation_kind=DerivationKind.BG_REMOVED,
        )
        assert sf.parent_storage_object_id == parent
        assert sf.derivation_kind == DerivationKind.BG_REMOVED

    def test_create_rejects_parent_without_kind(self) -> None:
        with pytest.raises(ValueError):
            StorageFile.create(
                bucket_name="b",
                object_key="k",
                content_type="image/webp",
                parent_storage_object_id=uuid.uuid4(),
                # derivation_kind omitted on purpose
            )

    def test_create_rejects_kind_without_parent(self) -> None:
        with pytest.raises(ValueError):
            StorageFile.create(
                bucket_name="b",
                object_key="k",
                content_type="image/webp",
                derivation_kind=DerivationKind.BG_REMOVED,
                # parent_storage_object_id omitted on purpose
            )
