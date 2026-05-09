"""Unit tests for ``RequestBackgroundRemovalHandler`` (IMG-007).

Covers the observable branches:

* feature flag off → ``BackgroundRemovalDisabledError`` (400)
* parent missing → ``StorageFileNotFoundError`` (404)
* parent not COMPLETED → ``StorageFileNotReadyError`` (422)
* idempotent re-call returns existing derivation untouched
  (``already_existed=True``)
* fresh call provisions a PROCESSING placeholder row and reports
  ``status="PROCESSING"`` so the router knows to dispatch the
  TaskIQ task — the handler itself stays free of infrastructure
  imports per Clean Architecture rule 3.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from src.bootstrap.config import Settings
from src.modules.image.application.commands.request_background_removal import (
    RequestBackgroundRemovalCommand,
    RequestBackgroundRemovalHandler,
)
from src.modules.image.domain.entities import StorageFile
from src.modules.image.domain.exceptions import (
    BackgroundRemovalDisabledError,
    StorageFileNotFoundError,
    StorageFileNotReadyError,
)
from src.modules.image.domain.interfaces import IStorageRepository
from src.modules.image.domain.value_objects import DerivationKind, StorageStatus
from src.shared.interfaces.entities import AggregateRoot
from src.shared.interfaces.uow import IUnitOfWork


class _FakeStorageRepo(IStorageRepository):
    """In-memory ``IStorageRepository`` covering only the methods the
    handler actually invokes; raises on the rest so a future change
    that broadens the handler's surface fails loudly here."""

    def __init__(self) -> None:
        self.store: dict[uuid.UUID, StorageFile] = {}

    async def add(self, storage_file: StorageFile) -> None:
        self.store[storage_file.id] = storage_file

    async def update(self, storage_file: StorageFile) -> None:
        self.store[storage_file.id] = storage_file

    async def get_by_id(self, storage_object_id: uuid.UUID) -> StorageFile | None:
        return self.store.get(storage_object_id)

    async def find_derivation(
        self, parent_storage_object_id: uuid.UUID, kind: DerivationKind
    ) -> StorageFile | None:
        for sf in self.store.values():
            if (
                sf.parent_storage_object_id == parent_storage_object_id
                and sf.derivation_kind == kind
                and sf.is_latest
            ):
                return sf
        return None

    # Methods we don't expect the handler to call:

    async def get_active_by_key(
        self, bucket_name: str, object_key: str
    ) -> StorageFile | None:
        raise NotImplementedError

    async def get_all_versions(self, bucket_name: str, object_key: str):
        raise NotImplementedError

    async def deactivate_previous_versions(
        self, bucket_name: str, object_key: str
    ) -> None:
        raise NotImplementedError

    async def mark_as_deleted(self, bucket_name: str, object_key: str) -> None:
        raise NotImplementedError

    async def list_pending_expired(self, older_than):
        raise NotImplementedError


class _FakeUow(IUnitOfWork):
    def __init__(self) -> None:
        self.commits = 0
        self.aggregates: list[AggregateRoot] = []

    async def __aenter__(self) -> IUnitOfWork:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        return None

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        return None

    def register_aggregate(self, aggregate: AggregateRoot) -> None:
        self.aggregates.append(aggregate)

    def enqueue_external_event(
        self,
        *,
        aggregate_type,
        aggregate_id,
        event_type,
        payload,
        event_id=None,
        correlation_id=None,
    ) -> None:
        return None


def _settings(*, enabled: bool) -> Settings:
    # Settings has many required env-bound fields (DB / Redis / RabbitMQ
    # creds); spec=Settings keeps the type contract while letting us
    # ignore everything the handler doesn't read.
    s = MagicMock(spec=Settings)
    s.BG_REMOVAL_ENABLED = enabled
    return s


def _make_completed_parent() -> StorageFile:
    parent = StorageFile.create(
        bucket_name="b",
        object_key="public/parent.webp",
        content_type="image/webp",
    )
    parent.status = StorageStatus.COMPLETED
    parent.url = "https://cdn.example/public/parent.webp"
    return parent


@pytest.mark.asyncio
class TestRequestBackgroundRemovalHandler:
    async def test_disabled_flag_raises_validation_error(self) -> None:
        repo, uow = _FakeStorageRepo(), _FakeUow()
        handler = RequestBackgroundRemovalHandler(
            repo=repo, uow=uow, settings=_settings(enabled=False)
        )

        with pytest.raises(BackgroundRemovalDisabledError):
            await handler.handle(
                RequestBackgroundRemovalCommand(parent_storage_object_id=uuid.uuid4())
            )
        assert uow.commits == 0

    async def test_missing_parent_raises_not_found(self) -> None:
        repo, uow = _FakeStorageRepo(), _FakeUow()
        handler = RequestBackgroundRemovalHandler(
            repo=repo, uow=uow, settings=_settings(enabled=True)
        )

        with pytest.raises(StorageFileNotFoundError):
            await handler.handle(
                RequestBackgroundRemovalCommand(parent_storage_object_id=uuid.uuid4())
            )

    async def test_parent_not_ready_raises_unprocessable(self) -> None:
        repo, uow = _FakeStorageRepo(), _FakeUow()
        parent = StorageFile.create(
            bucket_name="b",
            object_key="public/p.webp",
            content_type="image/webp",
        )
        # parent left in PENDING_UPLOAD on purpose
        repo.store[parent.id] = parent

        handler = RequestBackgroundRemovalHandler(
            repo=repo, uow=uow, settings=_settings(enabled=True)
        )

        with pytest.raises(StorageFileNotReadyError):
            await handler.handle(
                RequestBackgroundRemovalCommand(parent_storage_object_id=parent.id)
            )

    async def test_idempotent_returns_existing_derivation(self) -> None:
        repo, uow = _FakeStorageRepo(), _FakeUow()
        parent = _make_completed_parent()
        repo.store[parent.id] = parent

        existing = StorageFile.create(
            bucket_name=parent.bucket_name,
            object_key="public/derived.webp",
            content_type="image/webp",
            parent_storage_object_id=parent.id,
            derivation_kind=DerivationKind.BG_REMOVED,
        )
        existing.status = StorageStatus.COMPLETED
        existing.url = "https://cdn.example/public/derived.webp"
        repo.store[existing.id] = existing

        handler = RequestBackgroundRemovalHandler(
            repo=repo, uow=uow, settings=_settings(enabled=True)
        )

        result = await handler.handle(
            RequestBackgroundRemovalCommand(parent_storage_object_id=parent.id)
        )

        assert result.derived_storage_object_id == existing.id
        assert result.status == "COMPLETED"
        assert result.already_existed is True
        assert result.url == existing.url
        # No new placeholder row written; the existing one stays
        # whatever status it already had.
        assert len(repo.store) == 2

    async def test_fresh_call_provisions_processing_placeholder(self) -> None:
        repo, uow = _FakeStorageRepo(), _FakeUow()
        parent = _make_completed_parent()
        repo.store[parent.id] = parent

        handler = RequestBackgroundRemovalHandler(
            repo=repo, uow=uow, settings=_settings(enabled=True)
        )

        result = await handler.handle(
            RequestBackgroundRemovalCommand(parent_storage_object_id=parent.id)
        )

        assert result.status == "PROCESSING"
        assert result.already_existed is False
        assert result.url is None

        derived = repo.store[result.derived_storage_object_id]
        assert derived.parent_storage_object_id == parent.id
        assert derived.derivation_kind == DerivationKind.BG_REMOVED
        assert derived.status == StorageStatus.PROCESSING
        assert uow.commits == 1
