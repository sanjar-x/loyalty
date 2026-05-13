"""Fixtures for supplier integration tests.

Seeds minimal geo reference data (countries and subdivisions) required by
supplier FK constraints before each test.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture(autouse=True)
async def _seed_geo(db_session: AsyncSession) -> None:
    """Insert the countries and subdivisions referenced by supplier fixtures."""
    await db_session.execute(
        text(
            """
            INSERT INTO countries (alpha2, alpha3, numeric) VALUES
                ('RU', 'RUS', '643'),
                ('CN', 'CHN', '156'),
                ('US', 'USA', '840')
            ON CONFLICT (alpha2) DO NOTHING
            """
        )
    )
    await db_session.execute(
        text(
            """
            INSERT INTO subdivision_types (code) VALUES
                ('city'),
                ('region')
            ON CONFLICT (code) DO NOTHING
            """
        )
    )
    await db_session.execute(
        text(
            """
            INSERT INTO subdivisions (code, country_code, type_code) VALUES
                ('RU-MOW', 'RU', 'city'),
                ('RU-SPE', 'RU', 'city')
            ON CONFLICT (code) DO NOTHING
            """
        )
    )
    await db_session.flush()
