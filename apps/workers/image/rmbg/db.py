"""DB infrastructure — async SQLAlchemy engine + session factory.

Same shape as the image-storage worker's ``db.py``. Schema (storage
objects + outbox tables) is owned by backend's alembic migrations.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool

from config import settings

engine = create_async_engine(
    settings.database_url,
    poolclass=AsyncAdaptedQueuePool,
    pool_size=4,
    max_overflow=2,
    pool_pre_ping=True,
    pool_recycle=3600,
)

session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)
