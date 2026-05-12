# tests/integration/modules/catalog/application/commands/test_create_brand.py
"""Integration tests for CreateBrandHandler — simplified after media architecture split."""

import uuid

from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.commands.create_brand import (
    CreateBrandCommand,
    CreateBrandHandler,
)
from src.modules.catalog.infrastructure.models import Brand as OrmBrand


async def test_create_brand_handler_without_logo(
    app_container: AsyncContainer, db_session: AsyncSession
):
    # Arrange
    async with app_container() as request_container:
        handler = await request_container.get(CreateBrandHandler)
        command = CreateBrandCommand(name="TestBrand", slug="testbrand")

        # Act
        result = await handler.handle(command)

    # Assert
    assert result.brand_id is not None

    # Verify in DB
    orm_brand = await db_session.get(OrmBrand, result.brand_id)
    assert orm_brand is not None
    assert orm_brand.slug == "testbrand"
    assert orm_brand.logo_url is None
    assert orm_brand.logo_storage_object_id is None


async def test_create_brand_handler_with_logo(
    app_container: AsyncContainer, db_session: AsyncSession
):
    """Brand created with logo_url and logo_storage_object_id."""
    storage_object_id = uuid.uuid4()

    async with app_container() as request_container:
        handler = await request_container.get(CreateBrandHandler)

        command = CreateBrandCommand(
            name="TestBrandWithLogo",
            slug="testbrand-logo",
            logo_url="https://cdn.example.com/brands/logo.webp",
            logo_storage_object_id=storage_object_id,
        )
        result = await handler.handle(command)

    # Assert
    assert result.brand_id is not None

    # Verify in DB
    orm_brand = await db_session.get(OrmBrand, result.brand_id)
    assert orm_brand is not None
    assert orm_brand.logo_url == "https://cdn.example.com/brands/logo.webp"
    assert orm_brand.logo_storage_object_id == storage_object_id
