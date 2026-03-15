# src/modules/catalog/application/constants.py
"""
Детерминированные ключи для S3-объектов модуля Catalog.

Ключи вычисляются из идентификатора агрегата, что устраняет
необходимость синхронного вызова модуля Storage при создании сущностей.
"""

import uuid


def raw_logo_key(brand_id: uuid.UUID) -> str:
    """Ключ raw-загрузки логотипа бренда (до обработки)."""
    return f"raw_uploads/catalog/brands/{brand_id}/logo_raw"


def public_logo_key(brand_id: uuid.UUID) -> str:
    """Ключ обработанного логотипа бренда (публичный)."""
    return f"public/brands/{brand_id}/logo.webp"
