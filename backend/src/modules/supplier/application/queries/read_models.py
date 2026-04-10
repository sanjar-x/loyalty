"""Read models (DTOs) for Supplier query handlers."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class PaginatedReadModel[T](BaseModel):
    items: list[T]
    total: int
    offset: int
    limit: int


class SupplierReadModel(BaseModel):
    id: uuid.UUID
    name: str
    type: str
    country_code: str
    subdivision_code: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


SupplierListReadModel = PaginatedReadModel[SupplierReadModel]
