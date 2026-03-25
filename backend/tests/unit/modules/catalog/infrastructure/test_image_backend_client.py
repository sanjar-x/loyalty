import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.modules.catalog.infrastructure.image_backend_client import ImageBackendClient

pytestmark = pytest.mark.asyncio


async def test_delete_sends_correct_request():
    client = ImageBackendClient(
        base_url="http://image-backend:8001",
        api_key="test-key",
    )
    sid = uuid.uuid4()

    mock_response = MagicMock(status_code=200)
    with patch(
        "httpx.AsyncClient.delete",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_delete:
        await client.delete(sid)

    mock_delete.assert_called_once()
    call_args = mock_delete.call_args
    assert str(sid) in call_args[0][0]
    assert call_args[1]["headers"]["X-API-Key"] == "test-key"


async def test_delete_best_effort_on_network_error():
    """delete() should not raise even if ImageBackend is unreachable."""
    client = ImageBackendClient(
        base_url="http://unreachable:9999",
        api_key="test-key",
    )
    sid = uuid.uuid4()

    with patch(
        "httpx.AsyncClient.delete",
        new_callable=AsyncMock,
        side_effect=httpx.ConnectError("connection refused"),
    ):
        await client.delete(sid)  # Should NOT raise


async def test_delete_best_effort_on_server_error():
    """delete() should not raise on 500 response."""
    client = ImageBackendClient(
        base_url="http://image-backend:8001",
        api_key="test-key",
    )
    sid = uuid.uuid4()

    mock_response = MagicMock(status_code=500)
    with patch(
        "httpx.AsyncClient.delete",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        await client.delete(sid)  # Should NOT raise


async def test_delete_url_construction():
    """Verify the DELETE URL is correctly constructed."""
    client = ImageBackendClient(
        base_url="http://image-backend:8001/",  # trailing slash
        api_key="key",
    )
    sid = uuid.UUID("01961234-0000-0000-0000-000000000000")

    mock_response = MagicMock(status_code=200)
    with patch(
        "httpx.AsyncClient.delete",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_delete:
        await client.delete(sid)

    expected_url = (
        "http://image-backend:8001/api/v1/media/01961234-0000-0000-0000-000000000000"
    )
    assert mock_delete.call_args[0][0] == expected_url
