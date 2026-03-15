# src/modules/catalog/domain/entities.py
import uuid

from attr import dataclass

from src.modules.catalog.domain.value_objects import MediaProcessingStatus
from src.shared.interfaces.entities import AggregateRoot


@dataclass
class Brand(AggregateRoot):
    id: uuid.UUID
    name: str
    slug: str
    logo_status: MediaProcessingStatus | None = None
    logo_file_id: uuid.UUID | None = None
    logo_url: str | None = None

    @classmethod
    def create(
        cls,
        name: str,
        slug: str,
        logo_file_id: uuid.UUID | None = None,
        logo_status: MediaProcessingStatus | None = None,
    ) -> "Brand":
        return cls(
            id=uuid.uuid4(),
            name=name,
            slug=slug,
            logo_file_id=logo_file_id,
            logo_status=logo_status,
        )

    def init_logo_upload(self, object_key: str, content_type: str) -> None:
        """Инициирует загрузку логотипа и генерирует BrandCreatedEvent."""
        self.logo_status = MediaProcessingStatus.PENDING_UPLOAD

        from src.modules.catalog.domain.events import BrandCreatedEvent

        self.add_domain_event(
            BrandCreatedEvent(
                brand_id=self.id,
                object_key=object_key,
                content_type=content_type,
                aggregate_id=str(self.id),
            )
        )

    def confirm_logo_upload(self) -> None:
        if self.logo_status != MediaProcessingStatus.PENDING_UPLOAD:
            from src.modules.catalog.domain.exceptions import InvalidLogoStateException

            raise InvalidLogoStateException(
                brand_id=self.id,
                current_status=str(self.logo_status) if self.logo_status else "None",
                expected_status=MediaProcessingStatus.PENDING_UPLOAD,
            )
        self.logo_status = MediaProcessingStatus.PROCESSING

        from src.modules.catalog.domain.events import BrandLogoConfirmedEvent

        self.add_domain_event(
            BrandLogoConfirmedEvent(
                brand_id=self.id,
                aggregate_id=str(self.id),
            )
        )

    def complete_logo_processing(self, url: str) -> None:
        self.logo_url = url
        self.logo_status = MediaProcessingStatus.COMPLETED

    def fail_logo_processing(self) -> None:
        self.logo_status = MediaProcessingStatus.FAILED


@dataclass
class Category(AggregateRoot):
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
