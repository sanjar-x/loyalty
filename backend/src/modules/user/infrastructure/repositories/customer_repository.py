"""SQLAlchemy implementation of the Customer repository."""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.user.domain.entities import Customer
from src.modules.user.domain.interfaces import ICustomerRepository
from src.modules.user.infrastructure.models import CustomerModel


class CustomerRepository(ICustomerRepository):
    """Concrete repository for Customer aggregate persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_domain(self, orm: CustomerModel) -> Customer:
        return Customer(
            id=orm.id,
            profile_email=orm.profile_email,
            first_name=orm.first_name,
            last_name=orm.last_name,
            username=orm.username,
            phone=orm.phone,
            referral_code=orm.referral_code or "",
            referred_by=orm.referred_by,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    async def add(self, customer: Customer) -> Customer:
        orm = CustomerModel(
            id=customer.id,
            profile_email=customer.profile_email,
            first_name=customer.first_name,
            last_name=customer.last_name,
            username=customer.username,
            phone=customer.phone,
            referral_code=customer.referral_code or None,
            referred_by=customer.referred_by,
        )
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def get(self, customer_id: uuid.UUID) -> Customer | None:
        orm = await self._session.get(CustomerModel, customer_id)
        return self._to_domain(orm) if orm else None

    async def update(self, customer: Customer) -> None:
        stmt = (
            update(CustomerModel)
            .where(CustomerModel.id == customer.id)
            .values(
                profile_email=customer.profile_email,
                first_name=customer.first_name,
                last_name=customer.last_name,
                username=customer.username,
                phone=customer.phone,
                referral_code=customer.referral_code or None,
            )
        )
        await self._session.execute(stmt)

    async def get_by_referral_code(self, code: str) -> Customer | None:
        stmt = select(CustomerModel).where(CustomerModel.referral_code == code)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None
