# src/shared/interfaces/entities.py
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


class IBase(Protocol):
    """
    Доменный контракт для базовой сущности (Entity).
    Репозиторию неважно, это SQLAlchemy-модель или Pydantic-схема,
    главное — чтобы у объекта был идентификатор.
    """

    id: uuid.UUID


# ---------------------------------------------------------------------------
# Domain Events (Базовые классы для Transactional Outbox)
# ---------------------------------------------------------------------------


@dataclass
class DomainEvent:
    """
    Базовый класс доменного события.
    Все события сериализуются через dataclasses.asdict()
    и записываются в таблицу outbox_messages атомарно с бизнес-транзакцией.
    """

    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Подклассы ОБЯЗАНЫ переопределить эти поля
    aggregate_type: str = ""
    aggregate_id: str = ""
    event_type: str = ""

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if cls.aggregate_type == "" or cls.event_type == "":
            raise TypeError(f"{cls.__name__} must override 'aggregate_type' and 'event_type'")


class AggregateRoot:
    """
    Mixin для доменных агрегатов, аккумулирующих события in-memory.

    Используется как mixin к attrs-dataclass'ам:
        @attr.dataclass
        class Brand(AggregateRoot):
            ...

    Агрегат накапливает события через add_domain_event().
    UnitOfWork при commit() извлекает их и записывает в Outbox.
    """

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)

    def __attrs_post_init__(self) -> None:
        # attrs вызывает __attrs_post_init__ после генерации __init__
        self._domain_events: list[DomainEvent] = []

    def add_domain_event(self, event: DomainEvent) -> None:
        self._domain_events.append(event)

    def clear_domain_events(self) -> None:
        self._domain_events.clear()

    @property
    def domain_events(self) -> list[DomainEvent]:
        return self._domain_events.copy()
