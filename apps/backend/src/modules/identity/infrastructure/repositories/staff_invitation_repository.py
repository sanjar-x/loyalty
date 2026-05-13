"""SQLAlchemy implementation of the StaffInvitation repository."""

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities import StaffInvitation
from src.modules.identity.domain.interfaces import IStaffInvitationRepository
from src.modules.identity.domain.value_objects import InvitationStatus
from src.modules.identity.infrastructure.models import (
    StaffInvitationModel,
    StaffInvitationRoleModel,
)


class StaffInvitationRepository(IStaffInvitationRepository):
    """Concrete repository for StaffInvitation aggregate persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_domain(
        self, orm: StaffInvitationModel, role_ids: list[uuid.UUID]
    ) -> StaffInvitation:
        return StaffInvitation(
            id=orm.id,
            email=orm.email,
            token_hash=orm.token_hash,
            role_ids=role_ids,
            invited_by=orm.invited_by,
            status=InvitationStatus(orm.status),
            created_at=orm.created_at,
            expires_at=orm.expires_at,
            accepted_at=orm.accepted_at,
            accepted_identity_id=orm.accepted_identity_id,
        )

    async def _get_role_ids(self, invitation_id: uuid.UUID) -> list[uuid.UUID]:
        stmt = select(StaffInvitationRoleModel.role_id).where(
            StaffInvitationRoleModel.invitation_id == invitation_id
        )
        result = await self._session.execute(stmt)
        return [row[0] for row in result.all()]

    async def add(self, invitation: StaffInvitation) -> StaffInvitation:
        orm = StaffInvitationModel(
            id=invitation.id,
            email=invitation.email,
            token_hash=invitation.token_hash,
            invited_by=invitation.invited_by,
            status=invitation.status.value,
            expires_at=invitation.expires_at,
            accepted_at=invitation.accepted_at,
            accepted_identity_id=invitation.accepted_identity_id,
        )
        self._session.add(orm)
        for role_id in invitation.role_ids:
            role_orm = StaffInvitationRoleModel(
                invitation_id=invitation.id,
                role_id=role_id,
            )
            self._session.add(role_orm)
        await self._session.flush()
        return invitation

    async def get(self, invitation_id: uuid.UUID) -> StaffInvitation | None:
        orm = await self._session.get(StaffInvitationModel, invitation_id)
        if orm is None:
            return None
        role_ids = await self._get_role_ids(invitation_id)
        return self._to_domain(orm, role_ids)

    async def get_by_token_hash(self, token_hash: str) -> StaffInvitation | None:
        stmt = select(StaffInvitationModel).where(
            StaffInvitationModel.token_hash == token_hash
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        role_ids = await self._get_role_ids(orm.id)
        return self._to_domain(orm, role_ids)

    async def get_pending_by_email(self, email: str) -> StaffInvitation | None:
        stmt = select(StaffInvitationModel).where(
            StaffInvitationModel.email == email,
            StaffInvitationModel.status == InvitationStatus.PENDING.value,
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        role_ids = await self._get_role_ids(orm.id)
        return self._to_domain(orm, role_ids)

    async def update(self, invitation: StaffInvitation) -> None:
        stmt = (
            update(StaffInvitationModel)
            .where(StaffInvitationModel.id == invitation.id)
            .values(
                status=invitation.status.value,
                accepted_at=invitation.accepted_at,
                accepted_identity_id=invitation.accepted_identity_id,
            )
        )
        await self._session.execute(stmt)

    async def list_all(
        self,
        offset: int = 0,
        limit: int = 20,
        status: InvitationStatus | None = None,
    ) -> tuple[list[StaffInvitation], int]:
        count_stmt = select(func.count()).select_from(StaffInvitationModel)
        list_stmt = select(StaffInvitationModel)

        if status is not None:
            count_stmt = count_stmt.where(StaffInvitationModel.status == status.value)
            list_stmt = list_stmt.where(StaffInvitationModel.status == status.value)

        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar() or 0

        list_stmt = (
            list_stmt.order_by(StaffInvitationModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        list_result = await self._session.execute(list_stmt)
        orms = list_result.scalars().all()

        if not orms:
            return [], total

        # Batch-fetch role_ids for all invitations in a single query
        invitation_ids = [orm.id for orm in orms]
        roles_stmt = select(
            StaffInvitationRoleModel.invitation_id,
            StaffInvitationRoleModel.role_id,
        ).where(StaffInvitationRoleModel.invitation_id.in_(invitation_ids))
        roles_result = await self._session.execute(roles_stmt)

        role_map: dict[uuid.UUID, list[uuid.UUID]] = {iid: [] for iid in invitation_ids}
        for row in roles_result.all():
            role_map[row[0]].append(row[1])

        items = [self._to_domain(orm, role_map[orm.id]) for orm in orms]
        return items, total
