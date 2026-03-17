"""
Attribute repository — placeholder Data Mapper implementation.

Currently returns raw ORM instances because the domain Attribute entity
has not been implemented yet.  Replace ``Any`` with a proper domain
model once the Attribute aggregate is built out.
"""

from typing import Any

from src.modules.catalog.domain.interfaces import IAttributeRepository
from src.modules.catalog.infrastructure.models import Attribute
from src.modules.catalog.infrastructure.repositories.base import BaseRepository


class AttributeRepository(
    BaseRepository[Any, Attribute], IAttributeRepository, model_class=Attribute
):
    """Placeholder repository for catalog attributes.

    Uses ``Any`` as the domain type because the Attribute domain entity
    has not been implemented yet.  Mapping methods are stubs.
    """

    def _to_domain(self, orm: Attribute) -> Any:
        """Return the ORM instance as-is (no domain entity exists yet)."""
        # TODO: Replace Any with DomainAttribute once it is created
        return orm

    def _to_orm(self, entity: Any, orm: Attribute | None = None) -> Attribute:
        """Return a bare ORM instance (no domain mapping exists yet)."""
        # TODO: Implement full domain → ORM mapping
        if orm is None:
            orm = Attribute()
        return orm
