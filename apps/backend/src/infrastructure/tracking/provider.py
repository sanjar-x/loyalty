"""Dishka provider for specialized Redis tracking ports (research §4.2).

Binds :class:`ISortedSetService`, :class:`IEventBufferService` and
:class:`ICardinalityService` to their Redis-backed implementations.
All three share the Redis client owned by :class:`CacheProvider`.
"""

from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource

from src.infrastructure.tracking.redis_cardinality import RedisCardinalityService
from src.infrastructure.tracking.redis_event_buffer import RedisEventBufferService
from src.infrastructure.tracking.redis_sorted_set import RedisSortedSetService
from src.shared.interfaces.cardinality import ICardinalityService
from src.shared.interfaces.event_buffer import IEventBufferService
from src.shared.interfaces.sorted_set import ISortedSetService


class TrackingProvider(Provider):
    """Specialized sorted-set / event-buffer / cardinality ports."""

    sorted_set: CompositeDependencySource = provide(
        source=RedisSortedSetService, scope=Scope.APP, provides=ISortedSetService
    )
    event_buffer: CompositeDependencySource = provide(
        source=RedisEventBufferService, scope=Scope.APP, provides=IEventBufferService
    )
    cardinality: CompositeDependencySource = provide(
        source=RedisCardinalityService, scope=Scope.APP, provides=ICardinalityService
    )
