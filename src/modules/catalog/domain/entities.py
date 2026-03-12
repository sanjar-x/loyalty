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
