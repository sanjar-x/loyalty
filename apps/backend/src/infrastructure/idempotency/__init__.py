"""Shared idempotency / inbox infrastructure.

* :class:`IdempotencyKeyModel` / :class:`ConsumerInboxModel` — ORM
  tables shared across every bounded context.
* :class:`SqlIdempotencyStore` / :class:`SqlInboxStore` — PostgreSQL
  adapters implementing the :class:`IIdempotencyStore` /
  :class:`IInboxStore` ports from :mod:`shared.interfaces.idempotency`.
* :func:`run_inbox_idempotent` — TaskIQ-consumer wrapper that
  short-circuits on duplicate ``event_id``.
"""

from src.infrastructure.idempotency.models import (
    ConsumerInboxModel,
    IdempotencyKeyModel,
)
from src.infrastructure.idempotency.repositories import (
    SqlIdempotencyStore,
    SqlInboxStore,
)
from src.infrastructure.idempotency.runner import run_inbox_idempotent

__all__ = [
    "ConsumerInboxModel",
    "IdempotencyKeyModel",
    "SqlIdempotencyStore",
    "SqlInboxStore",
    "run_inbox_idempotent",
]
