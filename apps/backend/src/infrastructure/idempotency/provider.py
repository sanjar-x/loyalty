"""Dishka provider for shared idempotency / inbox stores.

Both stores depend solely on the request-scoped ``AsyncSession`` and
expose their respective interfaces from :mod:`shared.interfaces.idempotency`,
so any module that injects ``IIdempotencyStore`` or ``IInboxStore`` gets
the same implementation without having to wire it locally.
"""

from __future__ import annotations

from dishka import Provider, Scope, provide

from src.infrastructure.idempotency.repositories import (
    SqlIdempotencyStore,
    SqlInboxStore,
)
from shared.interfaces.idempotency import IIdempotencyStore, IInboxStore


class IdempotencyProvider(Provider):
    """Provides ``IIdempotencyStore`` and ``IInboxStore`` request-scope."""

    idempotency_store = provide(
        SqlIdempotencyStore, scope=Scope.REQUEST, provides=IIdempotencyStore
    )
    inbox_store = provide(SqlInboxStore, scope=Scope.REQUEST, provides=IInboxStore)
