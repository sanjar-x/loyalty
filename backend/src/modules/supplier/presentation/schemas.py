"""Pydantic request/response schemas for the Supplier API."""

import uuid
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import Field

from src.shared.schemas import CamelModel

S = TypeVar("S")


class PaginatedResponse(CamelModel, Generic[S]):
    items: list[S]
    total: int
    offset: int
    limit: int


class SupplierCreateRequest(CamelModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., pattern=r"^(cross_border|local)$")
    region: str = Field(..., min_length=1, max_length=100)


class SupplierCreateResponse(CamelModel):
    id: uuid.UUID


class SupplierUpdateRequest(CamelModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    region: str | None = Field(None, min_length=1, max_length=100)


class SupplierResponse(CamelModel):
    id: uuid.UUID
    name: str
    type: str
    region: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SupplierListResponse(PaginatedResponse[SupplierResponse]):
    pass
