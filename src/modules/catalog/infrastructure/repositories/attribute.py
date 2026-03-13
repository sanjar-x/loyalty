# src/modules/catalog/infrastructure/repositories/attribute.py
from typing import Any

from src.modules.catalog.domain.interfaces import IAttributeRepository
from src.modules.catalog.infrastructure.models import Attribute
from src.modules.catalog.infrastructure.repositories.base import BaseRepository


class AttributeRepository(
    BaseRepository[Any, Attribute], IAttributeRepository, model_class=Attribute
):
    """
    Репозиторий атрибутов.
    Пока использует Any в качестве доменной модели, так как она еще не реализована.
    """

    def _to_domain(self, orm: Attribute) -> Any:
        # TODO: Заменить Any на DomainAttribute, когда он будет создан
        return orm

    def _to_orm(self, entity: Any, orm: Attribute | None = None) -> Attribute:
        # TODO: Полноценный маппинг
        if orm is None:
            orm = Attribute()
        return orm
