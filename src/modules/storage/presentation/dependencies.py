# src\modules\storage\presentation\dependencies.py
from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.uow import IUnitOfWork

