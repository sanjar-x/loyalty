"""Unit of Work implementation backed by SQLAlchemy AsyncSession.

Coordinates transactional writes, aggregate tracking, and atomic
persistence of domain events into the Outbox table.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.outbox import OutboxMessage
from src.shared.exceptions import ConflictError, UnprocessableEntityError
from src.shared.interfaces.entities import AggregateRoot, DomainEvent
from src.shared.interfaces.uow import IUnitOfWork

logger = structlog.get_logger(__name__)


class UnitOfWork(IUnitOfWork):
    """Transactional Unit of Work that flushes domain events to the Outbox.

    Registered aggregates have their pending domain events collected and
    persisted as ``OutboxMessage`` rows in the same transaction as the
    business data, guaranteeing atomicity.
    """

    def __init__(self, session: AsyncSession):
        """Initialize the UoW with an active async session.

        Args:
            session: The SQLAlchemy async session for the current request.
        """
        self._session: AsyncSession = session
        self._aggregates: list[AggregateRoot] = []

    async def __aenter__(self) -> UnitOfWork:
        """Enter the UoW context and reset tracked aggregates."""
        self._aggregates.clear()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the UoW context, rolling back on exception."""
        if exc_type:
            await self.rollback()
        self._aggregates.clear()

    async def flush(self) -> None:
        """Flush pending changes to the database without committing."""
        await self._session.flush()

    def register_aggregate(self, aggregate: AggregateRoot) -> None:
        """Register an aggregate root for domain event collection on commit.

        Args:
            aggregate: The aggregate whose events should be persisted.
        """
        if aggregate not in self._aggregates:
            self._aggregates.append(aggregate)

    async def commit(self) -> None:
        """Commit the transaction, persisting outbox events atomically.

        Raises:
            UnprocessableEntityError: On foreign key violations (sqlstate 23503).
            ConflictError: On other integrity constraint violations.
        """
        try:
            self._collect_and_persist_outbox_events()
            await self._session.commit()
        except IntegrityError as e:
            await self.rollback()
            sqlstate = getattr(e.orig, "sqlstate", None)

            if sqlstate == "23503":  # foreign_key_violation
                raise UnprocessableEntityError(
                    message="Business logic error",
                    error_code="FOREIGN_KEY_VIOLATION",
                ) from e

            raise ConflictError(
                message="Conflict! Record already exists or violates DB constraints.",
                error_code="DB_INTEGRITY_ERROR",
            ) from e

    async def rollback(self) -> None:
        """Roll back the current transaction and clear tracked aggregates."""
        await self._session.rollback()
        self._aggregates.clear()

    # ---------------------------------------------------------------------------
    # Outbox: domain event collection and mapping to OutboxMessage
    # ---------------------------------------------------------------------------

    def _collect_and_persist_outbox_events(self) -> None:
        """Extract domain events from registered aggregates and add them to the session.

        Iterates over all registered aggregates, serializes their pending
        domain events into ``OutboxMessage`` ORM instances, and adds them
        to the session. Called immediately before ``session.commit()`` so
        that business data and outbox records are committed atomically.
        """
        outbox_messages: list[OutboxMessage] = []

        for aggregate in self._aggregates:
            for event in aggregate.domain_events:
                outbox_messages.append(self._map_event_to_outbox(event))
            aggregate.clear_domain_events()

        if outbox_messages:
            self._session.add_all(outbox_messages)
            logger.debug(
                "Outbox: events added to transaction",
                count=len(outbox_messages),
            )

    @staticmethod
    def _serialize_value(value: Any) -> Any:
        """Recursively serialize a value for JSON compatibility.

        Handles UUID, datetime, lists, and dicts at any nesting depth.
        """
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, list):
            return [UnitOfWork._serialize_value(item) for item in value]
        if isinstance(value, dict):
            return {k: UnitOfWork._serialize_value(v) for k, v in value.items()}
        return value

    @staticmethod
    def _serialize_event_payload(event: DomainEvent) -> dict[str, Any]:
        """Serialize a dataclass domain event into a JSON-compatible dict.

        Args:
            event: The domain event dataclass to serialize.

        Returns:
            A dictionary with UUID and datetime values converted to strings
            at any nesting depth.
        """
        raw = dataclasses.asdict(event)
        return {key: UnitOfWork._serialize_value(value) for key, value in raw.items()}

    @staticmethod
    def _map_event_to_outbox(event: DomainEvent) -> OutboxMessage:
        """Map a domain event to an OutboxMessage ORM instance.

        Args:
            event: The domain event to persist.

        Returns:
            An ``OutboxMessage`` ready to be added to the session.
        """
        from src.shared.context import get_request_id

        correlation_id = get_request_id()
        return OutboxMessage(
            id=event.event_id,
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            event_type=event.event_type,
            payload=UnitOfWork._serialize_event_payload(event),
            correlation_id=correlation_id if correlation_id != "UNKNOWN" else None,
        )
