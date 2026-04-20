"""Queries for ``FormulaVersion`` aggregates."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.modules.pricing.domain.exceptions import FormulaVersionNotFoundError
from src.modules.pricing.domain.formula import FormulaVersion
from src.modules.pricing.domain.interfaces import (
    FormulaVersionListFilter,
    IFormulaVersionRepository,
)
from src.modules.pricing.domain.value_objects import FormulaStatus


@dataclass(frozen=True)
class FormulaVersionReadModel:
    version_id: uuid.UUID
    context_id: uuid.UUID
    version_number: int
    status: str
    ast: dict[str, Any]
    published_at: datetime | None
    published_by: uuid.UUID | None
    version_lock: int
    created_at: datetime
    updated_at: datetime
    updated_by: uuid.UUID | None

    @classmethod
    def from_domain(cls, version: FormulaVersion) -> FormulaVersionReadModel:
        return cls(
            version_id=version.id,
            context_id=version.context_id,
            version_number=version.version_number,
            status=version.status.value,
            ast=dict(version.ast),
            published_at=version.published_at,
            published_by=version.published_by,
            version_lock=version.version_lock,
            created_at=version.created_at,
            updated_at=version.updated_at,
            updated_by=version.updated_by,
        )


@dataclass(frozen=True)
class GetFormulaVersionQuery:
    version_id: uuid.UUID


@dataclass(frozen=True)
class ListFormulaVersionsQuery:
    context_id: uuid.UUID
    status: FormulaStatus | None = None


@dataclass(frozen=True)
class GetFormulaDraftQuery:
    context_id: uuid.UUID


class GetFormulaVersionHandler:
    def __init__(self, repo: IFormulaVersionRepository) -> None:
        self._repo = repo

    async def handle(self, query: GetFormulaVersionQuery) -> FormulaVersionReadModel:
        version = await self._repo.get_by_id(query.version_id)
        if version is None:
            raise FormulaVersionNotFoundError(version_id=query.version_id)
        return FormulaVersionReadModel.from_domain(version)


class ListFormulaVersionsHandler:
    def __init__(self, repo: IFormulaVersionRepository) -> None:
        self._repo = repo

    async def handle(
        self, query: ListFormulaVersionsQuery
    ) -> list[FormulaVersionReadModel]:
        filters = FormulaVersionListFilter(status=query.status)
        versions = await self._repo.list_by_context(query.context_id, filters)
        return [FormulaVersionReadModel.from_domain(v) for v in versions]


class GetFormulaDraftHandler:
    def __init__(self, repo: IFormulaVersionRepository) -> None:
        self._repo = repo

    async def handle(self, query: GetFormulaDraftQuery) -> FormulaVersionReadModel:
        draft = await self._repo.get_draft_for_context(query.context_id)
        if draft is None:
            raise FormulaVersionNotFoundError(
                context_id=query.context_id, status="draft"
            )
        return FormulaVersionReadModel.from_domain(draft)


__all__ = [
    "FormulaVersionReadModel",
    "GetFormulaDraftHandler",
    "GetFormulaDraftQuery",
    "GetFormulaVersionHandler",
    "GetFormulaVersionQuery",
    "ListFormulaVersionsHandler",
    "ListFormulaVersionsQuery",
]
