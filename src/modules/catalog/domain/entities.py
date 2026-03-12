# domain/entities/brand.py
import uuid

from attr import dataclass

from src.modules.catalog.domain.value_objects import MediaProcessingStatus


@dataclass
class Brand:
    id: uuid.UUID
    name: str
    slug: str
    logo_status: MediaProcessingStatus | None = None
    logo_file_id: uuid.UUID | None = None
    logo_url: str | None = None

    @classmethod
    def create(cls, name: str, slug: str) -> "Brand":
        return cls(
            id=uuid.uuid4(),
            name=name,
            slug=slug,
            logo_status=None,
        )

    def init_logo_upload(self) -> None:
        self.logo_status = MediaProcessingStatus.PENDING_UPLOAD

    def confirm_logo_upload(self) -> None:
        if self.logo_status != MediaProcessingStatus.PENDING_UPLOAD:
            from src.modules.catalog.domain.exceptions import InvalidLogoStateException

            raise InvalidLogoStateException(
                brand_id=self.id,
                current_status=str(self.logo_status) if self.logo_status else "None",
                expected_status=MediaProcessingStatus.PENDING_UPLOAD,
            )
        self.logo_status = MediaProcessingStatus.PROCESSING

    def complete_logo_processing(self, file_id: uuid.UUID, url: str) -> None:
        self.logo_file_id = file_id
        self.logo_url = url
        self.logo_status = MediaProcessingStatus.COMPLETED

    def fail_logo_processing(self) -> None:
        self.logo_status = MediaProcessingStatus.FAILED


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
