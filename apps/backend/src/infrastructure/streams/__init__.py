"""Channel-stream infrastructure package.

Contains the Redis-Streams-backed implementation of
:class:`src.shared.interfaces.channel_stream.IChannelStream` and its
Dishka DI provider. Each ``publish`` lands an entry in a bounded log,
``subscribe`` honours ``Last-Event-ID`` resume — the upgrade path from
fire-and-forget Redis pub/sub documented in the SSE flow section of
the backend CLAUDE.md.
"""
