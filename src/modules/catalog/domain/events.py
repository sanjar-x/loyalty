# src/modules/catalog/domain/events.py
import uuid
from typing import TypedDict

from src.shared.events import IntegrationEvent


class BrandLogoPayload(TypedDict):
    """Строго типизированная структура для payload интеграционного события."""

    brand_id: uuid.UUID
    object_key: str
    content_type: str


class BrandLogoUploadConfirmedEvent(IntegrationEvent):
    """
    Интеграционное событие: Логотип бренда успешно загружен в S3.
    Инициирует фоновую обработку (ресайз, конвертация в WebP) и создание StorageObject.
    """

    event_type: str = "catalog.brand.logo_upload_confirmed"
    payload: BrandLogoPayload
