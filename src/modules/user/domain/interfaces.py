# src/modules/user/domain/interfaces.py
import uuid
from abc import ABC, abstractmethod

from src.modules.user.domain.entities import User


class IUserRepository(ABC):
    @abstractmethod
    async def add(self, user: User) -> User:
        pass

    @abstractmethod
    async def get(self, user_id: uuid.UUID) -> User | None:
        pass

    @abstractmethod
    async def update(self, user: User) -> None:
        pass
