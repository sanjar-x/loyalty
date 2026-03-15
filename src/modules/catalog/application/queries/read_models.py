# src/modules/catalog/application/queries/read_models.py
"""
Read Models (DTO) для Query-обработчиков модуля Catalog.

Эти модели не содержат бизнес-логики — только данные для чтения.
Используются напрямую Query Handler'ами без участия доменных агрегатов,
репозиториев или Unit of Work.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class CategoryNode(BaseModel):
    """Плоский узел дерева категорий (Read Model)."""

    id: uuid.UUID
    name: str
    slug: str
    full_slug: str
    level: int
    sort_order: int
    parent_id: uuid.UUID | None = None
    children: list[CategoryNode] = []
