"""
AttributeTemplate repository -- Data Mapper implementation.

Translates between the domain ``AttributeTemplate`` entity and the
``attribute_templates`` ORM table.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.modules.catalog.domain.entities import (
    AttributeTemplate as DomainAttributeTemplate,
)
from src.modules.catalog.domain.exceptions import (
    AttributeTemplateCodeAlreadyExistsError,
)
from src.modules.catalog.domain.interfaces import IAttributeTemplateRepository
from src.modules.catalog.infrastructure.models import (
    AttributeTemplate as OrmAttributeTemplate,
)
from src.modules.catalog.infrastructure.models import (
    Category as OrmCategory,
)
from src.modules.catalog.infrastructure.repositories.base import BaseRepository


class AttributeTemplateRepository(
    BaseRepository[DomainAttributeTemplate, OrmAttributeTemplate],
    IAttributeTemplateRepository,
    model_class=OrmAttributeTemplate,
):
    """Data Mapper repository for AttributeTemplate aggregate.

    Inherits generic CRUD from BaseRepository.
    """

    def _to_domain(self, orm: OrmAttributeTemplate) -> DomainAttributeTemplate:
        return DomainAttributeTemplate(
            id=orm.id,
            code=orm.code,
            name_i18n=orm.name_i18n or {},
            description_i18n=orm.description_i18n or {},
            sort_order=orm.sort_order,
        )

    def _to_orm(
        self, entity: DomainAttributeTemplate, orm: OrmAttributeTemplate | None = None
    ) -> OrmAttributeTemplate:
        if orm is None:
            orm = OrmAttributeTemplate()
        orm.id = entity.id
        orm.code = entity.code
        orm.name_i18n = entity.name_i18n
        orm.description_i18n = entity.description_i18n
        orm.sort_order = entity.sort_order
        return orm

    async def add(self, entity: DomainAttributeTemplate) -> DomainAttributeTemplate:
        """Persist a new attribute template and return the refreshed copy."""
        orm = self._to_orm(entity)
        self._session.add(orm)
        try:
            await self._session.flush()
        except IntegrityError as e:
            constraint = str(e.orig) if e.orig else str(e)
            if "code" in constraint.lower():
                raise AttributeTemplateCodeAlreadyExistsError(code=entity.code) from e
            raise
        return self._to_domain(orm)

    async def check_code_exists(self, code: str) -> bool:
        return await self._field_exists("code", code)

    async def has_category_references(self, template_id: uuid.UUID) -> bool:
        stmt = select(
            select(OrmCategory.id)
            .where(OrmCategory.template_id == template_id)
            .limit(1)
            .exists()
        )
        result = await self._session.execute(stmt)
        return bool(result.scalar())

    async def get_category_ids_by_template_ids(
        self, template_ids: list[uuid.UUID]
    ) -> list[uuid.UUID]:
        """Return category IDs that reference any of the given template IDs."""
        if not template_ids:
            return []
        stmt = select(OrmCategory.id).where(
            OrmCategory.effective_template_id.in_(template_ids)
        ).limit(10_000)
        result = await self._session.execute(stmt)
        return [row[0] for row in result.all()]
