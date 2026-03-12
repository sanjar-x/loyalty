# domain/entities/brand.py
import uuid

from attr import dataclass

from src.modules.catalog.domain.value_objects import MediaProcessingStatus


@dataclass
class Brand:
    id: uuid.UUID
    name: str
    slug: str
    logo_status: MediaProcessingStatus

    @classmethod
    def create(cls, name: str, slug: str) -> "Brand":
        return cls(
            id=uuid.uuid4(),
            name=name,
            slug=slug,
            logo_status=MediaProcessingStatus.PENDING_UPLOAD,
        )

@dataclass
class Category:
    id: uuid.UUID
    parent_id: uuid.UUID | None
    name: str
    slug: str
    full_slug: str
    level: int
    sort_order: int

    @classmethod
    def create(
        cls,
        name: str,
        slug: str,
        parent_id: uuid.UUID | None,
        level: int,
        full_slug: str,
        sort_order: int,
    ) -> "Category":
        return cls(
            id=uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4(),
            parent_id=parent_id,
            name=name,
            slug=slug,
            full_slug=full_slug,
            level=level,
            sort_order=sort_order,
        )
