"""Read models (DTOs) for Supplier query handlers."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedReadModel(BaseModel, Generic[T]):
    items: list[T]
    total: int
    offset: int
    limit: int


class SupplierReadModel(BaseModel):
    id: uuid.UUID
    name: str
    type: str
    region: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


SupplierListReadModel = PaginatedReadModel[SupplierReadModel]
