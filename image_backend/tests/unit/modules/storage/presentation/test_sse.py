"""Tests for SSEManager.channel_name (pure logic, no Redis needed)."""

import uuid

from src.modules.storage.presentation.sse import SSEManager


class TestSSEManagerChannelName:
    """Verify the channel_name method produces correct Redis key patterns."""

    @staticmethod
    def _make_manager() -> SSEManager:
        """Create an SSEManager without a Redis connection.

        ``channel_name`` is a pure function — it only formats a string
        and never touches the network.  Bypassing ``__init__`` avoids
        the need for a live (or mocked) Redis instance.
        """
        return SSEManager.__new__(SSEManager)

    def test_channel_format_matches_spec(self) -> None:
        """Channel name must follow 'media:status:{uuid}'."""
        mgr = self._make_manager()
        sid = uuid.uuid4()
        channel = mgr.channel_name(sid)

        assert channel == f"media:status:{sid}"

    def test_channel_starts_with_prefix(self) -> None:
        """Channel name must start with 'media:status:'."""
        mgr = self._make_manager()
        sid = uuid.uuid4()
        channel = mgr.channel_name(sid)

        assert channel.startswith("media:status:")

    def test_channel_contains_uuid(self) -> None:
        """The UUID must appear verbatim in the channel name."""
        mgr = self._make_manager()
        sid = uuid.uuid4()
        channel = mgr.channel_name(sid)

        assert str(sid) in channel

    def test_different_ids_produce_different_channels(self) -> None:
        """Two distinct storage-object IDs must map to distinct channels."""
        mgr = self._make_manager()
        id_a = uuid.uuid4()
        id_b = uuid.uuid4()

        assert mgr.channel_name(id_a) != mgr.channel_name(id_b)

    def test_same_id_produces_same_channel(self) -> None:
        """The same UUID must always produce the same channel name."""
        mgr = self._make_manager()
        sid = uuid.uuid4()

        assert mgr.channel_name(sid) == mgr.channel_name(sid)
