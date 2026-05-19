"""Integration tests for ``ListMyPassportsHandler``.

The same handler powers both the customer-scope ``GET /api/v1/passports``
endpoint and the admin-scope ``GET /api/v1/admin/passports?identityId=``
endpoint (ADR-011 follow-up). Both call sites parametrise by
``identity_id`` only — ownership is enforced at the presentation layer.
"""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.passport.application.queries.list_my_passports import (
    ListMyPassportsHandler,
    ListMyPassportsQuery,
)

pytestmark = pytest.mark.integration


async def _seed_passport(
    session: AsyncSession,
    *,
    identity_id: uuid.UUID,
    inn: str,
    is_archived: bool = False,
) -> uuid.UUID:
    passport_id = uuid.uuid4()
    await session.execute(
        text(
            """
            INSERT INTO passports (
                id, identity_id, full_name_ru, full_name_lat,
                passport_serial, passport_number, passport_issue_date,
                birth_date, inn, validation_status, is_archived, version
            ) VALUES (
                :id, :identity, 'Иван Иванов', 'Ivan Ivanov',
                '1234', '567890', :pid, :bd, :inn,
                'pending', :archived, 0
            )
            """
        ),
        {
            "id": passport_id,
            "identity": identity_id,
            "pid": date(2015, 5, 22),
            "bd": date(1990, 1, 1),
            "inn": inn,
            "archived": is_archived,
        },
    )
    await session.flush()
    return passport_id


async def test_returns_only_passports_of_given_identity(
    db_session: AsyncSession,
) -> None:
    target_identity = uuid.uuid4()
    other_identity = uuid.uuid4()
    target_pid = await _seed_passport(
        db_session, identity_id=target_identity, inn="500100732272"
    )
    await _seed_passport(db_session, identity_id=other_identity, inn="500100732259")

    handler = ListMyPassportsHandler(db_session)
    page = await handler.handle(ListMyPassportsQuery(identity_id=target_identity))

    assert [r.passport_id for r in page.items] == [target_pid]


async def test_unknown_identity_returns_empty_page(
    db_session: AsyncSession,
) -> None:
    handler = ListMyPassportsHandler(db_session)
    page = await handler.handle(ListMyPassportsQuery(identity_id=uuid.uuid4()))
    assert page.items == []


async def test_archived_hidden_by_default_but_returned_with_flag(
    db_session: AsyncSession,
) -> None:
    identity = uuid.uuid4()
    active_id = await _seed_passport(
        db_session, identity_id=identity, inn="500100732272"
    )
    archived_id = await _seed_passport(
        db_session,
        identity_id=identity,
        inn="500100732259",
        is_archived=True,
    )

    handler = ListMyPassportsHandler(db_session)
    default_page = await handler.handle(ListMyPassportsQuery(identity_id=identity))
    assert {r.passport_id for r in default_page.items} == {active_id}

    with_archived = await handler.handle(
        ListMyPassportsQuery(identity_id=identity, include_archived=True)
    )
    assert {r.passport_id for r in with_archived.items} == {active_id, archived_id}
