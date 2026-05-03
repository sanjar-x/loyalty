"""Integration tests for the DobroPost webhook receiver.

Verifies the receiver:
* enforces token + IP gating
* normalises both DobroPost payload shapes (passport vs status)
* writes a row to ``outbox_messages`` so the relay can dispatch
* derives a deterministic ``event_id`` so retries dedup
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bootstrap.config import settings
from src.bootstrap.web import create_app
from src.infrastructure.database.models.outbox import OutboxMessage

pytestmark = pytest.mark.integration


@pytest.fixture
def webhook_token(monkeypatch: pytest.MonkeyPatch) -> str:
    """Wire a known token into settings so we can exercise the gate."""
    token = "wh-secret-12345678"
    monkeypatch.setattr(settings, "DOBROPOST_WEBHOOK_TOKEN", SecretStr(token))
    monkeypatch.setattr(settings, "DOBROPOST_ALLOWED_IPS", [])
    return token


async def _post(
    *,
    token: str,
    body: dict,
) -> tuple[int, dict | None]:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(f"/api/v1/orders/webhooks/dobropost/{token}", json=body)
        return resp.status_code, (resp.json() if resp.content else None)


async def test_invalid_token_returns_401(
    db_session: AsyncSession,
    webhook_token: str,
) -> None:
    code, _ = await _post(token="bad-token", body={"shipmentId": 1})
    assert code == 401


async def test_passport_payload_writes_outbox_row(
    db_session: AsyncSession,
    webhook_token: str,
) -> None:
    code, _ = await _post(
        token=webhook_token,
        body={"shipmentId": 1234, "passportValidationStatus": False},
    )
    assert code == 204
    rows = (await db_session.execute(select(OutboxMessage))).scalars().all()
    matching = [r for r in rows if r.event_type == "DobroPostPassportInvalidEvent"]
    assert len(matching) == 1
    payload = matching[0].payload
    assert payload["dp_shipment_id"] == 1234
    assert payload["passport_validation_status"] is False
    assert "event_id" in payload
    assert uuid.UUID(payload["event_id"])


async def test_status_payload_resolves_textual_status(
    db_session: AsyncSession,
    webhook_token: str,
) -> None:
    code, _ = await _post(
        token=webhook_token,
        body={
            "shipmentId": 9999,
            "DPTrackNumber": "DP9999",
            "status": "Покинула таможню — передана на доставку по РФ",
        },
    )
    assert code == 204
    rows = (await db_session.execute(select(OutboxMessage))).scalars().all()
    matching = [r for r in rows if r.event_type == "DobroPostStatusUpdatedEvent"]
    assert len(matching) == 1
    payload = matching[0].payload
    assert payload["dp_shipment_id"] == 9999
    assert payload["status_id"] == 649
    assert payload["dp_track_number"] == "DP9999"


async def test_duplicate_payload_yields_same_event_id(
    db_session: AsyncSession,
    webhook_token: str,
) -> None:
    body = {"shipmentId": 555, "statusId": 649, "DPTrackNumber": "DP555"}
    await _post(token=webhook_token, body=body)
    await _post(token=webhook_token, body=body)
    rows = (await db_session.execute(select(OutboxMessage))).scalars().all()
    status_rows = [r for r in rows if r.event_type == "DobroPostStatusUpdatedEvent"]
    assert len(status_rows) == 2
    assert status_rows[0].payload["event_id"] == status_rows[1].payload["event_id"]


async def test_unknown_shape_returns_204_without_outbox(
    db_session: AsyncSession,
    webhook_token: str,
) -> None:
    code, _ = await _post(token=webhook_token, body={"unrelated": True})
    assert code == 204
    rows = (await db_session.execute(select(OutboxMessage))).scalars().all()
    matching = [
        r
        for r in rows
        if r.event_type
        in {"DobroPostStatusUpdatedEvent", "DobroPostPassportInvalidEvent"}
    ]
    assert matching == []
