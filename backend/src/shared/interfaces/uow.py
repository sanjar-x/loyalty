"""
Unit of Work port (Hexagonal Architecture).

Defines ``IUnitOfWork``, the abstract base for transactional boundaries.
Command handlers depend on this interface to flush, commit, or roll back
a business transaction and to register aggregates whose domain events
should be written to the Outbox on commit.

Typical usage:
    async with uow:
        repo.add(entity)
        uow.register_aggregate(entity)
        await uow.commit()
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.shared.interfaces.entities import AggregateRoot


class IUnitOfWork(ABC):
    """Abstract transactional boundary for write operations.

    Implementations wrap a database session/transaction and handle
    domain event extraction + Outbox writes on ``commit()``.
    """

    @abstractmethod
    async def __aenter__(self) -> IUnitOfWork:
        """Enter the transactional context."""
        pass

    @abstractmethod
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the transactional context, rolling back on unhandled exceptions."""
        pass

    @abstractmethod
    async def flush(self) -> None:
        """Flush pending ORM changes to the database without committing.

        Useful for obtaining auto-generated values (e.g. database defaults)
        before the transaction is finalized.
        """
        pass

    @abstractmethod
    async def commit(self) -> None:
        """Commit the current transaction.

        Extracts domain events from registered aggregates and writes
        them to the Outbox table atomically within the same transaction.
        """
        pass

    @abstractmethod
    async def rollback(self) -> None:
        """Roll back the current transaction, discarding all pending changes."""
        pass

    @abstractmethod
    def register_aggregate(self, aggregate: AggregateRoot) -> None:
        """Register an aggregate for domain event collection on commit.

        Called in command handlers after mutating an aggregate, so that
        ``commit()`` can extract accumulated events and write them
        to the Outbox table atomically with the business transaction.

        Args:
            aggregate: The mutated aggregate root instance.
        """
        pass

    @abstractmethod
    def enqueue_external_event(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: dict[str, Any],
        event_id: uuid.UUID | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Stage a one-off external event for atomic Outbox insertion on commit.

        Distinct from :meth:`register_aggregate`: external events do not
        come from a domain aggregate of ours — typical sources are
        third-party webhook payloads (DobroPost / payment-provider
        callbacks) where the upstream system emits a fact and our
        consumers should observe it through the same Outbox/relay
        pipeline as native domain events. Using this method instead of
        ``session.add(OutboxMessage(...))`` from a router preserves the
        UoW's atomicity + IntegrityError translation contract.

        Args:
            aggregate_type: Logical aggregate label for routing
                (e.g. ``"DobroPostShipment"``).
            aggregate_id: Stable id for inbox dedup.
            event_type: ``PascalCase`` matching the consumer's
                registration in the outbox dispatch registry.
            payload: JSON-serialisable dict; must include any field
                consumers expect (the UoW does not augment it).
            event_id: Optional pre-computed UUID. When provided, lets
                the caller derive a deterministic id (e.g. UUID5 from
                the canonical payload) so DobroPost retries collapse
                into one Outbox row instead of N.
            correlation_id: Request-correlation marker. Defaults to
                whatever the request context carries.
        """
        pass
