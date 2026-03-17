# src/shared/interfaces/uow.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.shared.interfaces.entities import AggregateRoot


class IUnitOfWork(ABC):
    @abstractmethod
    async def __aenter__(self) -> IUnitOfWork:
        pass

    @abstractmethod
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    @abstractmethod
    async def flush(self) -> None:
        pass

    @abstractmethod
    async def commit(self) -> None:
        pass

    @abstractmethod
    async def rollback(self) -> None:
        pass

    @abstractmethod
    def register_aggregate(self, aggregate: AggregateRoot) -> None:
        """
        Регистрирует агрегат для сбора доменных событий при commit().

        Вызывается в Command Handler'е после мутации агрегата,
        чтобы UoW мог извлечь накопленные события и записать их
        в Outbox-таблицу атомарно с бизнес-транзакцией.
        """
        pass
