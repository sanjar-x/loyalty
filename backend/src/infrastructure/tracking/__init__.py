"""Specialized Redis-backed tracking services.

These implement the dedicated ports introduced by the ICacheService
research (sorted sets, event buffers, HyperLogLog cardinality) and are
wired via :mod:`src.infrastructure.tracking.provider`.
"""
