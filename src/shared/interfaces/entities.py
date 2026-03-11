# src/shared/interfaces/entities.py
import uuid
from typing import Protocol


class IBase(Protocol):
    """
    Доменный контракт для базовой сущности (Entity).
    Репозиторию неважно, это SQLAlchemy-модель или Pydantic-схема,
    главное — чтобы у объекта был идентификатор.
    """

    id: uuid.UUID

    # Можно добавить и другие обязательные поля, если они есть у всех моделей:
    # created_at: datetime
