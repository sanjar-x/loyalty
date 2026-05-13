"""Pydantic request/response schemas for the Supplier API."""

import uuid
from datetime import datetime

from pydantic import Field

from src.shared.schemas import CamelModel


class PaginatedResponse[S](CamelModel):
    items: list[S]
    total: int
    offset: int
    limit: int


class SupplierCreateRequest(CamelModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., pattern=r"^(cross_border|local)$")
    country_code: str = Field(
        ...,
        min_length=2,
        max_length=2,
        pattern=r"^[A-Z]{2}$",
        description="ISO 3166-1 alpha-2 country code",
        examples=["CN", "RU"],
    )
    subdivision_code: str | None = Field(
        None,
        max_length=10,
        pattern=r"^[A-Z]{2}-[A-Z0-9]{1,6}$",
        description="ISO 3166-2 subdivision code (optional)",
        examples=["RU-MOW", "CN-BJ"],
    )


class SupplierCreateResponse(CamelModel):
    id: uuid.UUID


class SupplierUpdateRequest(CamelModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    country_code: str | None = Field(
        None,
        min_length=2,
        max_length=2,
        pattern=r"^[A-Z]{2}$",
        description="ISO 3166-1 alpha-2 country code",
    )
    subdivision_code: str | None = Field(
        None,
        max_length=10,
        pattern=r"^[A-Z]{2}-[A-Z0-9]{1,6}$",
        description="ISO 3166-2 subdivision code; send null to clear",
    )


class SupplierResponse(CamelModel):
    id: uuid.UUID
    name: str
    type: str
    country_code: str
    subdivision_code: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SupplierListResponse(PaginatedResponse[SupplierResponse]):
    pass
