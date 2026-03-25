"""ORM model registry for Alembic auto-generation.

Importing this module ensures that all ORM models are registered with
the shared ``Base.metadata``, so Alembic's ``--autogenerate`` can
detect schema changes.
"""

from src.infrastructure.database.base import Base
from src.infrastructure.database.models.failed_task import FailedTask
from src.modules.storage.infrastructure.models import StorageObject

__all__ = [
    "Base",
    "FailedTask",
    "StorageObject",
]
