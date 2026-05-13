"""Generic idempotency-key store and inbox-event store ports.

Both abstractions live in the shared kernel so that every module gets
the same idempotency / inbox semantics without re-inventing the wheel:

* :class:`IIdempotencyStore` — request-level idempotency on **write
  commands** (HTTP POST with an ``Idempotency-Key`` header). Reserve
  the key, do the work, attach the produced resource_id; on retry the
  reservation collides and the handler short-circuits with the cached
  resource_id.

* :class:`IInboxStore` — consumer-level idempotency on **broker-
  delivered events**. The relay can deliver the same outbox event
  more than once; the inbox uniqueness constraint
  ``(event_id, consumer)`` makes "at-least-once" delivery effectively
  exactly-once at the business-effect level.

The two are deliberately separate ports because their rate, lifetime,
and retry semantics are different:

* idempotency keys are short-lived (minutes/hours), keyed by a
  client-supplied token + scope, scoped per identity;
* inbox rows live for the same retention as outbox messages (≈ 7
  days), keyed by ``(event_id, consumer_name)``.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime


class IIdempotencyStore(ABC):
    """Per-request idempotency store.

    Each row represents a single ``(scope, key)`` reservation tied to
    the ``identity_id`` of the caller. Implementations MUST persist the
    row in a way that a retry of the same ``reserve`` raises a
    uniqueness violation, which the implementation catches and returns
    ``False`` for.
    """

    @abstractmethod
    async def reserve(
        self,
        *,
        key: str,
        identity_id: uuid.UUID,
        scope: str,
        expires_at: datetime,
    ) -> bool:
        """Try to reserve ``(scope, key)``.

        Args:
            key: Client-supplied idempotency token.
            identity_id: Identity that issued the request.
            scope: Free-form discriminator naming the operation
                (``"order.create"``, ``"loyalty.adjust"``, ...).
            expires_at: TTL — a janitor task may prune older rows.

        Returns:
            ``True`` if the row was newly inserted (caller proceeds
            with the operation); ``False`` if a row already existed
            (caller should call :meth:`get_result` to fetch the
            previously produced ``resource_id``).
        """

    @abstractmethod
    async def attach_result(
        self, *, key: str, scope: str, resource_id: uuid.UUID
    ) -> None:
        """Attach the produced ``resource_id`` to a reservation.

        Called after a successful business mutation so that subsequent
        retries (which observe a ``False`` from ``reserve``) can return
        the original resource_id.
        """

    @abstractmethod
    async def get_result(self, *, key: str, scope: str) -> uuid.UUID | None:
        """Return the ``resource_id`` previously attached, or ``None``."""


class IInboxStore(ABC):
    """Per-consumer event inbox.

    Records the ``(event_id, consumer)`` of every successfully-handled
    event. ``UNIQUE (event_id, consumer)`` makes redeliveries idempotent
    at the persistence layer.
    """

    @abstractmethod
    async def try_record(self, *, event_id: uuid.UUID, consumer: str) -> bool:
        """Insert ``(event_id, consumer)`` row.

        Returns:
            ``True`` if the row was newly inserted (handler should run);
            ``False`` if the row already existed (handler must be
            skipped — the event has been processed before).
        """
