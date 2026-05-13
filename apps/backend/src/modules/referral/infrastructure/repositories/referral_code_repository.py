"""SQLAlchemy implementation of :class:`IReferralCodeRepository`."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.referral.domain.aggregates import ReferralCode
from src.modules.referral.domain.exceptions import (
    ReferralCodeAlreadyIssuedError,
)
from src.modules.referral.domain.ports import IReferralCodeRepository
from src.modules.referral.infrastructure.models import ReferralCodeModel


class ReferralCodeRepository(IReferralCodeRepository):
    """Data-mapper repository for :class:`ReferralCode`.

    Translates ``IntegrityError`` on the unique
    ``(customer_id)`` index into the domain-level
    :class:`ReferralCodeAlreadyIssuedError` so callers do not depend on
    SQLAlchemy.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _to_domain(orm: ReferralCodeModel) -> ReferralCode:
        return ReferralCode(
            id=orm.id,
            customer_id=orm.customer_id,
            code=orm.code,
            issued_at=orm.issued_at,
            is_revoked=orm.is_revoked,
            revoked_at=orm.revoked_at,
            revocation_reason=orm.revocation_reason,
            version=orm.version,
        )

    @staticmethod
    def _to_orm(entity: ReferralCode) -> ReferralCodeModel:
        return ReferralCodeModel(
            id=entity.id,
            customer_id=entity.customer_id,
            code=entity.code,
            issued_at=entity.issued_at,
            is_revoked=entity.is_revoked,
            revoked_at=entity.revoked_at,
            revocation_reason=entity.revocation_reason,
            version=entity.version,
        )

    # ------------------------------------------------------------------
    # Repository contract
    # ------------------------------------------------------------------

    async def add(self, code: ReferralCode) -> ReferralCode:
        row = self._to_orm(code)
        self._session.add(row)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            # Whether the violation hit ``customer_id`` or ``code`` is
            # decided at the application layer; both surface to the
            # caller as "code already issued / collision retry needed".
            raise ReferralCodeAlreadyIssuedError() from exc
        return code

    async def get(self, code_id: uuid.UUID) -> ReferralCode | None:
        orm = await self._session.get(ReferralCodeModel, code_id)
        return self._to_domain(orm) if orm else None

    async def get_by_customer(self, customer_id: uuid.UUID) -> ReferralCode | None:
        stmt = select(ReferralCodeModel).where(
            ReferralCodeModel.customer_id == customer_id
        )
        orm = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def find_by_code(self, code: str) -> ReferralCode | None:
        stmt = select(ReferralCodeModel).where(ReferralCodeModel.code == code)
        orm = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def update(self, code: ReferralCode) -> None:
        orm = await self._session.get(ReferralCodeModel, code.id, with_for_update=True)
        if orm is None:
            return
        orm.is_revoked = code.is_revoked
        orm.revoked_at = code.revoked_at
        orm.revocation_reason = code.revocation_reason
        orm.version = code.version
        await self._session.flush()
