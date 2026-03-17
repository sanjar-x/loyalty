# src/infrastructure/database/session.py
"""
DEPRECATED: Use DatabaseProvider via Dishka DI instead.
This module exists only for backward compatibility during migration.
"""

raise ImportError(
    "Direct import from session.py is deprecated. "
    "Use Dishka DI to inject AsyncSession or async_sessionmaker."
)
