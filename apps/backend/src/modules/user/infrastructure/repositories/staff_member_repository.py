"""SQLAlchemy implementation of the StaffMember repository."""

import uuid

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.user.domain.entities import StaffMember
from src.modules.user.domain.interfaces import IStaffMemberRepository
from src.modules.user.infrastructure.models import StaffMemberModel


class StaffMemberRepository(IStaffMemberRepository):
    """Concrete repository for StaffMember aggregate persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_domain(self, orm: StaffMemberModel) -> StaffMember:
        return StaffMember(
            id=orm.id,
            first_name=orm.first_name,
            last_name=orm.last_name,
            username=orm.username,
            profile_email=orm.profile_email,
            position=orm.position,
            department=orm.department,
            invited_by=orm.invited_by,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    async def add(self, staff: StaffMember) -> StaffMember:
        orm = StaffMemberModel(
            id=staff.id,
            first_name=staff.first_name,
            last_name=staff.last_name,
            username=staff.username,
            profile_email=staff.profile_email,
            position=staff.position,
            department=staff.department,
            invited_by=staff.invited_by,
        )
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def get(self, staff_id: uuid.UUID) -> StaffMember | None:
        orm = await self._session.get(StaffMemberModel, staff_id)
        return self._to_domain(orm) if orm else None

    async def update(self, staff: StaffMember) -> None:
        stmt = (
            update(StaffMemberModel)
            .where(StaffMemberModel.id == staff.id)
            .values(
                first_name=staff.first_name,
                last_name=staff.last_name,
                username=staff.username,
                profile_email=staff.profile_email,
                position=staff.position,
                department=staff.department,
            )
        )
        await self._session.execute(stmt)
