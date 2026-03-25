"""
FamilyAttributeExclusion repository -- Data Mapper implementation.

Translates between the domain ``FamilyAttributeExclusion`` entity and the
``family_attribute_exclusions`` ORM table. Provides pair-uniqueness checks
and batch loading for effective attribute resolution.
"""

import uuid
from collections import defaultdict

from sqlalchemy import select

from src.modules.catalog.domain.entities import (
    FamilyAttributeExclusion as DomainExclusion,
)
from src.modules.catalog.domain.interfaces import IFamilyAttributeExclusionRepository
from src.modules.catalog.infrastructure.models import (
    FamilyAttributeExclusion as OrmExclusion,
)
from src.modules.catalog.infrastructure.repositories.base import BaseRepository


class FamilyAttributeExclusionRepository(
    BaseRepository[DomainExclusion, OrmExclusion],
    IFamilyAttributeExclusionRepository,
    model_class=OrmExclusion,
):
    """Data Mapper repository for FamilyAttributeExclusion."""

    def _to_domain(self, orm: OrmExclusion) -> DomainExclusion:
        return DomainExclusion(
            id=orm.id,
            family_id=orm.family_id,
            attribute_id=orm.attribute_id,
        )

    def _to_orm(
        self, entity: DomainExclusion, orm: OrmExclusion | None = None
    ) -> OrmExclusion:
        if orm is None:
            orm = OrmExclusion()
        orm.id = entity.id
        orm.family_id = entity.family_id
        orm.attribute_id = entity.attribute_id
        return orm

    async def check_exclusion_exists(
        self, family_id: uuid.UUID, attribute_id: uuid.UUID
    ) -> bool:
        stmt = (
            select(OrmExclusion.id)
            .where(
                OrmExclusion.family_id == family_id,
                OrmExclusion.attribute_id == attribute_id,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def get_exclusions_for_families(
        self, family_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, set[uuid.UUID]]:
        """Batch-load all exclusions for a list of family IDs.

        Returns dict mapping family_id -> set of excluded attribute_ids.
        """
        if not family_ids:
            return {}
        stmt = select(
            OrmExclusion.family_id, OrmExclusion.attribute_id
        ).where(OrmExclusion.family_id.in_(family_ids))
        result = await self._session.execute(stmt)
        exclusions_map: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
        for row in result.all():
            exclusions_map[row.family_id].add(row.attribute_id)
        return dict(exclusions_map)
