# src/modules/catalog/infrastructure/queries.py
from sqlalchemy.ext.asyncio import AsyncSession


class SqlCategoryQueryService:
    def __init__(self, session: AsyncSession):
        self._session = session
