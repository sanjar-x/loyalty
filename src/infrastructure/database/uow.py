# src/infrastructure/database/uow.py
from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.outbox import OutboxMessage
from src.shared.exceptions import ConflictError, UnprocessableEntityError
from src.shared.interfaces.entities import AggregateRoot, DomainEvent
from src.shared.interfaces.uow import IUnitOfWork

logger = structlog.get_logger(__name__)


class UnitOfWork(IUnitOfWork):
    def __init__(self, session: AsyncSession):
        self._session = session
        self._aggregates: list[AggregateRoot] = []

    async def __aenter__(self) -> "UnitOfWork":
        self._aggregates.clear()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type:
            await self.rollback()
        self._aggregates.clear()

    async def flush(self) -> None:
        await self._session.flush()

    def register_aggregate(self, aggregate: AggregateRoot) -> None:
        """Регистрирует агрегат для сбора доменных событий при commit()."""
        if aggregate not in self._aggregates:
            self._aggregates.append(aggregate)

    async def commit(self) -> None:
        try:
            self._collect_and_persist_outbox_events()
            await self._session.commit()
        except IntegrityError as e:
            await self.rollback()
            sqlstate = getattr(e.orig, "sqlstate", None)

            if sqlstate == "23503":  # foreign_key_violation
                raise UnprocessableEntityError(
                    message="Ошибка бизнес-логики",
                    error_code="FOREIGN_KEY_VIOLATION",
                ) from e

            raise ConflictError(
                message="Конфликт! Запись уже существует или нарушает ограничения БД.",
                error_code="DB_INTEGRITY_ERROR",
            ) from e

    async def rollback(self) -> None:
        await self._session.rollback()
        self._aggregates.clear()

    # ------------------------------------------------------------------
    # Outbox: сбор доменных событий и маппинг в OutboxMessage
    # ------------------------------------------------------------------

    def _collect_and_persist_outbox_events(self) -> None:
        """
        Извлекает накопленные доменные события из зарегистрированных
        агрегатов, сериализует их и добавляет как OutboxMessage в сессию.

        Вызывается непосредственно перед session.commit(), поэтому
        бизнес-данные и Outbox-записи коммитятся атомарно.
        """
        outbox_messages: list[OutboxMessage] = []

        for aggregate in self._aggregates:
            for event in aggregate.domain_events:
                outbox_messages.append(self._map_event_to_outbox(event))
            aggregate.clear_domain_events()

        if outbox_messages:
            self._session.add_all(outbox_messages)
            logger.debug(
                "Outbox: события добавлены в транзакцию",
                count=len(outbox_messages),
            )

    @staticmethod
    def _map_event_to_outbox(event: DomainEvent) -> OutboxMessage:
        """Маппинг доменного события → ORM-запись в таблице outbox_messages."""
        return OutboxMessage(
            id=event.event_id,
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            event_type=event.event_type,
            payload=event.model_dump(mode="json"),
        )
