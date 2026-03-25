import asyncio
import json
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.modules.storage.presentation.sse import SSEManager


@pytest.fixture
def mock_redis():
    return AsyncMock()


def test_channel_name_contains_uuid():
    redis = AsyncMock()
    mgr = SSEManager(redis=redis)
    sid = uuid.uuid4()
    channel = mgr.channel_name(sid)
    assert str(sid) in channel
    assert channel.startswith("media:status:")


@pytest.mark.asyncio
async def test_publish_sends_to_redis(mock_redis):
    mgr = SSEManager(redis=mock_redis)
    sid = uuid.uuid4()
    data = {"status": "completed", "url": "https://cdn.example.com/x.webp"}

    await mgr.publish(sid, data)

    mock_redis.publish.assert_called_once()
    call_args = mock_redis.publish.call_args
    assert str(sid) in call_args[0][0]  # channel name
    assert json.loads(call_args[0][1]) == data  # payload
