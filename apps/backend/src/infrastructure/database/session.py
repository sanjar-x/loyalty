"""DEPRECATED: Direct session import is no longer supported.

Use ``DatabaseProvider`` via Dishka DI to inject ``AsyncSession`` or
``async_sessionmaker`` instead. This module exists only as a guard
during migration.
"""

raise ImportError(
    "Direct import from session.py is deprecated. "
    "Use Dishka DI to inject AsyncSession or async_sessionmaker."
)
