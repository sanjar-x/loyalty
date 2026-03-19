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
