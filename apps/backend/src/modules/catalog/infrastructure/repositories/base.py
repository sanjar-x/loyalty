"""Catalog-flavoured Data Mapper repository.

Thin alias over the shared kernel's
:class:`src.shared.infrastructure.repositories.base.BaseRepository`,
narrowed to also satisfy :class:`ICatalogRepository[EntityType]`.
The CRUD plumbing lives in shared (REC-031). Existing imports of
``from src.modules.catalog.infrastructure.repositories.base import
BaseRepository`` keep working untouched.

Note:
    Most catalog repositories inherit this base class.
    ``ProductRepository`` and ``MediaAssetRepository`` remain standalone
    implementations due to their specialised query requirements.
"""

from __future__ import annotations

from src.modules.catalog.domain.interfaces import ICatalogRepository
from src.shared.infrastructure.repositories.base import (
    BaseRepository as _SharedBaseRepository,
)
from src.shared.interfaces.entities import IBase


class BaseRepository[EntityType, ModelType: IBase](
    _SharedBaseRepository[EntityType, ModelType], ICatalogRepository[EntityType]
):
    """Catalog Data Mapper base — composes shared CRUD + catalog typing.

    The two parents reach the same abstract methods (``add`` / ``get`` /
    ``update`` / ``delete``); shared provides the implementation,
    ``ICatalogRepository[EntityType]`` keeps catalog-side typing
    contracts (``IBrandRepository(ICatalogRepository[DomainBrand])``)
    intact for downstream consumers.
    """
