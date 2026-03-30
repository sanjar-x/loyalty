"""
Integration tests for AttributeTemplateRepository Data Mapper roundtrips.

Proves that AttributeTemplate entities survive CRUD cycles with JSONB
i18n fields, code uniqueness, and category reference checks.

Part of Phase 07 -- Repository & Data Integrity (REPO-02, REPO-05).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.entities import AttributeTemplate
from src.modules.catalog.infrastructure.repositories.attribute_template import (
    AttributeTemplateRepository,
)


class TestAttributeTemplateRoundtrip:
    """Verify AttributeTemplate entity survives full create-read roundtrip."""

    async def test_template_basic_roundtrip(
        self,
        db_session: AsyncSession,
    ) -> None:
        """All AttributeTemplate fields survive roundtrip."""
        repo = AttributeTemplateRepository(session=db_session)
        template = AttributeTemplate.create(
            code="electronics",
            name_i18n={"en": "Electronics", "ru": "Электроника"},
            description_i18n={
                "en": "Template for electronics",
                "ru": "Шаблон для электроники",
            },
            sort_order=1,
        )
        await repo.add(template)
        await db_session.flush()

        fetched = await repo.get(template.id)

        assert fetched is not None
        assert fetched.code == "electronics"
        assert fetched.name_i18n == {"en": "Electronics", "ru": "Электроника"}
        assert fetched.description_i18n == {
            "en": "Template for electronics",
            "ru": "Шаблон для электроники",
        }
        assert fetched.sort_order == 1

    async def test_template_check_code_exists(
        self,
        db_session: AsyncSession,
    ) -> None:
        """check_code_exists returns True/False correctly."""
        repo = AttributeTemplateRepository(session=db_session)
        template = AttributeTemplate.create(
            code="clothing",
            name_i18n={"en": "Clothing", "ru": "Одежда"},
        )
        await repo.add(template)
        await db_session.flush()

        assert await repo.check_code_exists("clothing") is True
        assert await repo.check_code_exists("furniture") is False

    async def test_template_has_category_references_false(
        self,
        db_session: AsyncSession,
    ) -> None:
        """has_category_references returns False when no categories reference template."""
        repo = AttributeTemplateRepository(session=db_session)
        template = AttributeTemplate.create(
            code="no-cats",
            name_i18n={"en": "No Categories", "ru": "Без категорий"},
        )
        await repo.add(template)
        await db_session.flush()

        assert await repo.has_category_references(template.id) is False
