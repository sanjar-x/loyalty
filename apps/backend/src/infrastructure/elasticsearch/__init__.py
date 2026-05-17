"""Elasticsearch infrastructure: client lifecycle + bulk / health / management helpers.

Public surface re-exported here so module-level imports stay readable:

    from src.infrastructure.elasticsearch import bulk_index, BulkResult
    from src.infrastructure.elasticsearch import check_health, alias_swap

The Dishka provider is intentionally NOT re-exported — bootstrap code
imports it directly from :mod:`provider` to keep the container assembly
explicit.
"""

from src.infrastructure.elasticsearch.bulk import BulkResult, bulk_index
from src.infrastructure.elasticsearch.exceptions import translate
from src.infrastructure.elasticsearch.health import (
    ElasticsearchHealth,
    check_health,
    ping,
)
from src.infrastructure.elasticsearch.management import (
    alias_swap,
    create_index,
    current_alias_target,
    delete_index,
    index_exists,
    refresh,
)

__all__ = [
    "BulkResult",
    "ElasticsearchHealth",
    "alias_swap",
    "bulk_index",
    "check_health",
    "create_index",
    "current_alias_target",
    "delete_index",
    "index_exists",
    "ping",
    "refresh",
    "translate",
]
