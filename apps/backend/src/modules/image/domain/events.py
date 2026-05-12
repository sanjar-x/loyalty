"""Image domain events.

Concrete event types:

* :class:`StorageObjectProcessedEvent` — fired after the worker
  successfully resizes / re-encodes the raw upload into the public
  WebP main + 3 variants. Catalog subscribes (IMG-004) to keep
  ``media_assets.url`` and ``media_assets.image_variants`` in sync
  on a reupload — denormalised storefront copies stay fresh without
  a JOIN.

Validation + ``aggregate_id`` auto-fill come from
:class:`shared.interfaces.entities.ModuleDomainEvent`.
"""

import uuid
from dataclasses import dataclass, field

from shared.interfaces.entities import ModuleDomainEvent


@dataclass(frozen=True)
class ImageEvent(ModuleDomainEvent, abstract=True):
    """Intermediate base for all image module domain events."""

    aggregate_type: str = "image"


@dataclass(frozen=True)
class StorageObjectProcessedEvent(
    ImageEvent,
    required_fields=("storage_object_id", "url"),
    aggregate_id_field="storage_object_id",
):
    """A storage object has finished post-processing successfully.

    Carries the public ``url`` and ``image_variants`` produced by
    :func:`build_variants` so subscribers can mirror the values into
    their own denormalised stores (e.g. catalog
    ``media_assets.url``) without a cross-module read.
    """

    storage_object_id: uuid.UUID | None = None
    url: str | None = None
    image_variants: list[dict] = field(default_factory=list)
    event_type: str = "StorageObjectProcessedEvent"


@dataclass(frozen=True)
class BackgroundRemovedEvent(
    ImageEvent,
    required_fields=("storage_object_id", "parent_storage_object_id", "url"),
    aggregate_id_field="storage_object_id",
):
    """A background-removal derivation finished successfully (IMG-007).

    Emitted from ``remove_background_task`` after the inference and
    S3 upload commit. Carries both ends of the parent → derived link
    so audit consumers and future search-reindex / moderation jobs do
    not need a JOIN to the ``storage_objects`` table.

    Distinct from :class:`StorageObjectProcessedEvent` so subscribers
    can decide which lifecycle they care about — catalog mirrors only
    ``Processed`` (URL refresh on reupload), while a future
    moderation queue would consume ``BackgroundRemoved`` (extra
    review pass for ML output).
    """

    storage_object_id: uuid.UUID | None = None
    parent_storage_object_id: uuid.UUID | None = None
    url: str | None = None
    derivation_kind: str = ""
    image_variants: list[dict] = field(default_factory=list)
    event_type: str = "BackgroundRemovedEvent"
