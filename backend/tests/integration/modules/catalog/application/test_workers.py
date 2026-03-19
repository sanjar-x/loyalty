# tests/integration/modules/catalog/application/test_workers.py
"""Integration test for brand logo processing pipeline.

Tests BrandLogoProcessor.process() directly — the actual business logic
that the TaskIQ worker delegates to.  We bypass the @inject decorator
because it expects a dishka_container kwarg injected by the broker runtime.
"""

import io

from dishka import AsyncContainer
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.constants import raw_logo_key
from src.modules.catalog.application.services.media_processor import BrandLogoProcessor
from src.modules.catalog.domain.entities import Brand
from src.modules.catalog.domain.value_objects import MediaProcessingStatus
from src.modules.catalog.infrastructure.models import Brand as OrmBrand
from src.modules.catalog.infrastructure.repositories.brand import BrandRepository
from src.shared.interfaces.blob_storage import IBlobStorage


def _create_test_png() -> bytes:
    """Create a minimal valid PNG image (10×10 red square)."""
    img = Image.new("RGBA", (10, 10), color=(255, 0, 0, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def test_process_brand_logo_task(app_container: AsyncContainer, db_session: AsyncSession):
    # Arrange — resolve processor and blob storage from the DI container
    async with app_container() as request_container:
        blob_storage = await request_container.get(IBlobStorage)
        processor = await request_container.get(BrandLogoProcessor)
        repo = BrandRepository(db_session)

    brand = Brand.create(
        name="Worker Brand",
        slug="worker-brand",
        logo_status=MediaProcessingStatus.PROCESSING,
    )
    brand = await repo.add(brand)

    # Upload a *valid* PNG to InMemoryBlobStorage at the deterministic raw key
    raw_key = raw_logo_key(brand.id)
    png_bytes = _create_test_png()

    async def png_stream():
        yield png_bytes

    await blob_storage.upload_stream(
        object_name=raw_key, data_stream=png_stream(), content_type="image/png"
    )

    # Act — call the processor directly (bypasses TaskIQ @inject wrapper)
    await processor.process(brand_id=brand.id)

    # Assert — DB state reflects successful processing
    orm_brand = await db_session.get(OrmBrand, brand.id)
    assert orm_brand is not None
    assert orm_brand.logo_status == MediaProcessingStatus.COMPLETED
    assert (
        orm_brand.logo_url
        == f"http://127.0.0.1:9000/test-bucket/public/brands/{brand.id}/logo.webp"
    )

    # Verify processed WebP was uploaded and raw file was cleaned up
    assert await blob_storage.object_exists(f"public/brands/{brand.id}/logo.webp")
    assert not await blob_storage.object_exists(raw_key)
