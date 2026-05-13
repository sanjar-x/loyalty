"""Central router registry.

Collects all feature routers in priority order.  The first matching
handler wins (depth-first traversal), so admin routes must come
before general-purpose ones.

Convention: import routers lazily inside the function to avoid
circular imports and keep startup explicit.
"""

from aiogram import Router


def get_all_routers() -> list[Router]:
    """Return routers in registration order (highest priority first)."""
    from src.bot.handlers.common import router as common_router
    from src.bot.handlers.errors import router as error_router
    from src.bot.handlers.nav import router as nav_router

    # Order matters: first match wins.
    # Future feature routers (catalog, orders, profile, admin) go between
    # common and error routers.
    return [
        common_router,  # /start, /help, /cancel
        nav_router,  # inline nav (back / home) + noop callback
        # --- feature routers will be inserted here ---
        error_router,  # global error handler + fallback (must be last)
    ]
