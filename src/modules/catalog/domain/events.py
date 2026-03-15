# src/modules/catalog/domain/events.py
"""
Доменные события модуля Catalog.

Эти события генерируются агрегатами (Brand, Category) при бизнес-операциях.
Сериализуются в JSON и сохраняются атомарно с бизнес-транзакцией.
Инфраструктурный слой отвечает за их последующую доставку.
"""

import uuid

from src.shared.interfaces.entities import DomainEvent


class BrandLogoConfirmedEvent(DomainEvent):
    """
    Загрузка логотипа подтверждена — требуется обработка (ресайз/WebP).
    Генерируется в Brand.confirm_logo_upload().
    """

    brand_id: uuid.UUID
    aggregate_type: str = "Brand"
    event_type: str = "BrandLogoConfirmedEvent"
