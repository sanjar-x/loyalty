# src/modules/catalog/domain/events.py
"""
Доменные события модуля Catalog.

Эти события генерируются агрегатами (Brand, Category) при бизнес-операциях.
Сериализуются в JSON и сохраняются атомарно с бизнес-транзакцией.
Инфраструктурный слой отвечает за их последующую доставку.
"""

import uuid

from src.shared.interfaces.entities import DomainEvent


class BrandCreatedEvent(DomainEvent):
    """
    Бренд создан с запросом на загрузку логотипа.
    Модуль Storage создаёт запись StorageObject асинхронно.
    """

    brand_id: uuid.UUID
    object_key: str
    content_type: str
    aggregate_type: str = "Brand"
    event_type: str = "BrandCreatedEvent"


class BrandLogoConfirmedEvent(DomainEvent):
    """
    Загрузка логотипа подтверждена — требуется обработка (ресайз/WebP).
    Генерируется в Brand.confirm_logo_upload().
    """

    brand_id: uuid.UUID
    aggregate_type: str = "Brand"
    event_type: str = "BrandLogoConfirmedEvent"


class BrandLogoProcessedEvent(DomainEvent):
    """
    Логотип обработан — модуль Storage регистрирует итоговый файл.
    Генерируется воркером после успешного ресайза и загрузки в S3.
    """

    brand_id: uuid.UUID
    object_key: str
    content_type: str
    size_bytes: int
    aggregate_type: str = "Brand"
    event_type: str = "BrandLogoProcessedEvent"
