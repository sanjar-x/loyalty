# tests/integration/modules/identity/application/commands/test_register.py
"""Integration tests for RegisterHandler — full CQRS command flow."""

import pytest
from dishka import AsyncContainer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.outbox import OutboxMessage
from src.modules.identity.application.commands.register import (
    RegisterCommand,
    RegisterHandler,
)
from src.modules.identity.domain.exceptions import IdentityAlreadyExistsError
from src.modules.identity.infrastructure.models import IdentityModel


async def test_register_creates_identity_and_credentials(
    app_container: AsyncContainer, db_session: AsyncSession
):
    async with app_container() as request:
        handler = await request.get(RegisterHandler)
        result = await handler.handle(
            RegisterCommand(email="new@example.com", password="S3cure!Pass")
        )

    assert result.identity_id is not None
    orm = await db_session.get(IdentityModel, result.identity_id)
    assert orm is not None
    assert orm.type == "LOCAL"


async def test_register_emits_identity_registered_event_to_outbox(
    app_container: AsyncContainer, db_session: AsyncSession
):
    async with app_container() as request:
        handler = await request.get(RegisterHandler)
        result = await handler.handle(
            RegisterCommand(email="outbox@example.com", password="S3cure!Pass")
        )

    outbox_result = await db_session.execute(
        select(OutboxMessage).where(
            OutboxMessage.aggregate_type == "Identity",
            OutboxMessage.aggregate_id == str(result.identity_id),
            OutboxMessage.event_type == "IdentityRegisteredEvent",
        )
    )
    outbox_row = outbox_result.scalar_one_or_none()
    assert outbox_row is not None


async def test_register_raises_conflict_on_duplicate_email(
    app_container: AsyncContainer, db_session: AsyncSession
):
    async with app_container() as request:
        handler = await request.get(RegisterHandler)
        await handler.handle(RegisterCommand(email="dupe@example.com", password="S3cure!Pass"))

    with pytest.raises(IdentityAlreadyExistsError):
        async with app_container() as request:
            handler = await request.get(RegisterHandler)
            await handler.handle(RegisterCommand(email="dupe@example.com", password="S3cure!Pass"))
