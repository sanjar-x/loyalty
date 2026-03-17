"""User repository implementations.

Re-exports the concrete SQLAlchemy-based User repository for convenient
access by the dependency injection provider.
"""

from src.modules.user.infrastructure.repositories.user_repository import (
    UserRepository,
)

__all__ = ["UserRepository"]
