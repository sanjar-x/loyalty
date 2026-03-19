"""Central router registry.

Collects all feature routers in priority order.  The first matching
handler wins (depth-first traversal), so admin routes must come
before general-purpose ones.
"""

from aiogram import Router


def get_all_routers() -> list[Router]:
    """Return routers in registration order (highest priority first)."""
    from src.bot.handlers.common import router as common_router
    from src.bot.handlers.errors import router as error_router

    # Order matters: first match wins.
    # Future feature routers (catalog, orders, profile) go between
    # common and error routers.
    return [
        common_router,  # /start, /help, /cancel
        # ... feature routers will be added here ...
        error_router,  # global error handler (must be last)
    ]
