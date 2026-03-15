# src/modules/catalog/domain/events.py
"""
Доменные события модуля Catalog.

Эти события генерируются агрегатами (Brand, Category) при бизнес-операциях.
Сериализуются в JSON и сохраняются атомарно с бизнес-транзакцией.
Инфраструктурный слой отвечает за их последующую доставку.
"""

import uuid
from dataclasses import dataclass

from src.shared.interfaces.entities import DomainEvent


@dataclass
class BrandCreatedEvent(DomainEvent):
    """
    Бренд создан с запросом на загрузку логотипа.
    Модуль Storage создаёт запись StorageFile асинхронно.
    """

    brand_id: uuid.UUID = None  # type: ignore[assignment]
    object_key: str = ""
    content_type: str = ""
    aggregate_type: str = "Brand"
    event_type: str = "BrandCreatedEvent"


@dataclass
class BrandLogoConfirmedEvent(DomainEvent):
    """
    Загрузка логотипа подтверждена — требуется обработка (ресайз/WebP).
    Генерируется в Brand.confirm_logo_upload().
    """

    brand_id: uuid.UUID | None = None
    aggregate_type: str = "Brand"
    event_type: str = "BrandLogoConfirmedEvent"


@dataclass
class BrandLogoProcessedEvent(DomainEvent):
    """
    Логотип обработан — модуль Storage регистрирует итоговый файл.
    Генерируется в Brand.complete_logo_processing().
    """

    brand_id: uuid.UUID | None = None
    object_key: str = ""
    content_type: str = ""
    size_bytes: int = 0
    aggregate_type: str = "Brand"
    event_type: str = "BrandLogoProcessedEvent"
