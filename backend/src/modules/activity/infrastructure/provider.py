"""
Dishka IoC provider for the activity bounded context.

Wires:
* :class:`RedisActivityTracker` as the app-scoped implementation of
  :class:`IActivityTracker`.
* :class:`SqlAlchemyActivityEventRepository` as the request-scoped
  implementation of :class:`IActivityEventRepository` (used by the
  flush task via ``async_sessionmaker``).
"""

from __future__ import annotations

from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource

from src.modules.activity.domain.interfaces import IActivityEventRepository
from src.modules.activity.infrastructure.co_view_reader import (
    SqlAlchemyCoViewReader,
)
from src.modules.activity.infrastructure.history_reader import (
    SqlAlchemyUserActivityReader,
)
from src.modules.activity.infrastructure.redis_query_service import (
    RedisActivityQueryService,
)
from src.modules.activity.infrastructure.redis_tracker import RedisActivityTracker
from src.modules.activity.infrastructure.repository import (
    SqlAlchemyActivityEventRepository,
)
from src.shared.interfaces.activity import (
    IActivityQueryService,
    IActivityTracker,
    ICoViewReader,
    IUserActivityReader,
)


class ActivityProvider(Provider):
    """DI provider for activity tracker and repository."""

    tracker: CompositeDependencySource = provide(
        RedisActivityTracker,
        scope=Scope.REQUEST,
        provides=IActivityTracker,
    )

    query_service: CompositeDependencySource = provide(
        RedisActivityQueryService,
        scope=Scope.REQUEST,
        provides=IActivityQueryService,
    )

    repository: CompositeDependencySource = provide(
        SqlAlchemyActivityEventRepository,
        scope=Scope.REQUEST,
        provides=IActivityEventRepository,
    )

    history_reader: CompositeDependencySource = provide(
        SqlAlchemyUserActivityReader,
        scope=Scope.REQUEST,
        provides=IUserActivityReader,
    )

    co_view_reader: CompositeDependencySource = provide(
        SqlAlchemyCoViewReader,
        scope=Scope.REQUEST,
        provides=ICoViewReader,
    )
