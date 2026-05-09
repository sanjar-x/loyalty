"""Command: request a background-removal derivation of a storage object.

Public application-layer entry point used by the
:func:`request_background_removal` admin route handler. Idempotent —
a second call against the same parent returns the existing derivation
instead of provisioning a new row + dispatching a fresh ML run.

Flow (IMG-007):
    1. Look up parent ``StorageFile`` and reject 404 / 422 (not ready).
    2. ``find_derivation(parent_id, BG_REMOVED)`` — if a row already
       exists, return it: status=COMPLETED gives the URL straight back,
       status=PROCESSING tells the client to listen on the existing
       SSE stream.
    3. Otherwise insert a fresh ``PROCESSING`` row and ``.kiq()`` the
       :func:`remove_background_task` — the worker (with the
       ``[bg-removal]`` extras installed) downloads the parent bytes,
       runs Bria RMBG-2.0, uploads the cutout, marks COMPLETED, and
       pushes SSE.

The ML pipeline lives in the infrastructure layer behind the
:class:`IBackgroundRemover` port; the handler does not import it
directly.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal

import structlog

from src.bootstrap.config import Settings
from src.modules.image.domain.entities import StorageFile
from src.modules.image.domain.exceptions import (
    BackgroundRemovalDisabledError,
    StorageFileNotFoundError,
    StorageFileNotReadyError,
)
from src.modules.image.domain.interfaces import IStorageRepository
from src.modules.image.domain.value_objects import DerivationKind, StorageStatus
from src.shared.interfaces.uow import IUnitOfWork

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class RequestBackgroundRemovalCommand:
    """Input for kicking off a bg-removal derivation."""

    parent_storage_object_id: uuid.UUID


@dataclass(frozen=True)
class RequestBackgroundRemovalResult:
    """Output describing what (if anything) the worker is doing.

    Attributes:
        derived_storage_object_id: ID of the derivation row — same
            value the caller subscribes to via
            ``GET /admin/media/{id}/status`` for SSE updates.
        status: Lifecycle state at the moment of return. ``COMPLETED``
            means the URL is already attached and no work was kicked.
            ``PROCESSING`` means the worker has been queued (or was
            already running on a prior call).
        url: Public URL of the cutout when ``status=COMPLETED``;
            ``None`` while processing.
        already_existed: ``True`` when an existing derivation was
            returned instead of provisioning a new row — lets the
            admin UI distinguish "already done" (instant feedback)
            from "queued, please wait" (show progress).
    """

    derived_storage_object_id: uuid.UUID
    status: Literal["COMPLETED", "PROCESSING"]
    url: str | None
    already_existed: bool


class RequestBackgroundRemovalHandler:
    """Application command handler for IMG-007."""

    def __init__(
        self,
        repo: IStorageRepository,
        uow: IUnitOfWork,
        settings: Settings,
    ) -> None:
        self._repo = repo
        self._uow = uow
        self._settings = settings
        self._log = logger.bind(handler="RequestBackgroundRemovalHandler")

    async def handle(
        self, command: RequestBackgroundRemovalCommand
    ) -> RequestBackgroundRemovalResult:
        if not self._settings.BG_REMOVAL_ENABLED:
            raise BackgroundRemovalDisabledError()

        parent_id = command.parent_storage_object_id
        log = self._log.bind(parent_storage_object_id=str(parent_id))

        async with self._uow:
            parent = await self._repo.get_by_id(parent_id)
            if parent is None:
                raise StorageFileNotFoundError(storage_object_id=str(parent_id))

            # Background removal needs the *processed* bytes (resized
            # WebP), not the raw upload. Reject early so the worker
            # never has to handle the in-flight case.
            if parent.status != StorageStatus.COMPLETED:
                raise StorageFileNotReadyError(
                    storage_object_id=str(parent_id),
                    status=parent.status.value,
                )

            existing = await self._repo.find_derivation(
                parent_id, DerivationKind.BG_REMOVED
            )
            if existing is not None:
                # Idempotent re-call. Returning the existing row
                # (whatever its status) lets the admin UI subscribe
                # to the same SSE stream without re-dispatching the
                # task — protects against accidental N×$$ ML cost.
                log.info(
                    "background_removal_already_exists",
                    derived_storage_object_id=str(existing.id),
                    status=existing.status.value,
                )
                return RequestBackgroundRemovalResult(
                    derived_storage_object_id=existing.id,
                    status="COMPLETED"
                    if existing.status == StorageStatus.COMPLETED
                    else "PROCESSING",
                    url=existing.url
                    if existing.status == StorageStatus.COMPLETED
                    else None,
                    already_existed=True,
                )

            # Insert a placeholder row in PROCESSING so the SSE channel
            # is addressable from the moment we return 202. The
            # worker fills in ``object_key``, ``url``, and
            # ``image_variants`` on completion. Dispatch of the TaskIQ
            # job itself happens in the router (presentation layer)
            # to keep the application layer free of infrastructure
            # imports — see ``confirm_upload`` for the same pattern.
            derived = StorageFile.create(
                bucket_name=parent.bucket_name,
                object_key=f"public/{parent_id}_bg_removed.placeholder",
                content_type="image/webp",
                owner_module=parent.owner_module,
                filename=parent.filename,
                parent_storage_object_id=parent_id,
                derivation_kind=DerivationKind.BG_REMOVED,
            )
            derived.status = StorageStatus.PROCESSING
            await self._repo.add(derived)
            await self._uow.commit()

        log.info(
            "background_removal_queued",
            derived_storage_object_id=str(derived.id),
        )
        return RequestBackgroundRemovalResult(
            derived_storage_object_id=derived.id,
            status="PROCESSING",
            url=None,
            already_existed=False,
        )
