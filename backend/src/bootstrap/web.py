"""FastAPI application factory and lifespan management.

This module is the composition root for the web process.  It wires
together middleware, exception handlers, routers, and the DI container,
then exposes ``create_app()`` for the ASGI server.
"""

from contextlib import asynccontextmanager

import structlog
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from structlog.stdlib import BoundLogger

# Outbox event handlers register at import time via ``register_event_handler``;
# TaskIQ tasks register via the ``@broker.task`` decorator at import time too.
# Importing the framework-level outbox tasks AND every module's declared
# ``task_modules`` (REFACT-001 PR-5) makes the registry identical across
# web / worker / scheduler processes. Without this the relay's
# "unknown event_type" branch silently drops events whenever the relay
# runs in a process that did not import the emitter's task module.
import src.infrastructure.outbox.tasks  # noqa: F401
from src.api.exceptions.handlers import setup_exception_handlers
from src.api.middlewares.legacy_redirects import LegacyRedirectsMiddleware
from src.api.middlewares.logger import AccessLoggerMiddleware
from src.api.router import router
from src.bootstrap.broker import broker
from src.bootstrap.config import settings
from src.bootstrap.container import create_container
from src.bootstrap.logger import setup_logging
from src.bootstrap.module_registry import import_task_modules
from src.bootstrap.modules import MODULES

import_task_modules(MODULES)

setup_logging()

logger: BoundLogger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle events.

    On startup the TaskIQ broker is connected (when running outside a
    worker process).  On shutdown the broker, DI container, and all
    connection pools are closed gracefully.

    Args:
        app: The FastAPI application instance.

    Yields:
        Control back to the ASGI server for the duration of the
        application's lifetime.
    """
    logger.info(
        "Starting Enterprise API",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
    )

    if not broker.is_worker_process:
        logger.info("Starting TaskIQ broker within the API process...")
        await broker.startup()

    yield

    if not broker.is_worker_process:
        logger.info("Shutting down TaskIQ broker...")
        await broker.shutdown()

    if hasattr(app.state, "dishka_container"):
        logger.info("Closing IoC container and connection pools...")
        await app.state.dishka_container.close()

    logger.info("Enterprise API stopped. Resource cleanup complete.")


def create_app() -> FastAPI:
    """Build and fully configure the FastAPI application.

    Assembles middleware (CORS, access logging), exception handlers,
    API routers, a health-check endpoint, and the Dishka DI container.

    Returns:
        A ready-to-serve ``FastAPI`` application instance.
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        docs_url="/docs" if settings.ENVIRONMENT != "prod" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.ENVIRONMENT != "prod" else None,
        lifespan=lifespan,
    )

    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        )

    app.add_middleware(AccessLoggerMiddleware)
    # 308 redirects for the 2026-05 router restructure. Remove after
    # 2026-05-09 — see docs/api/router-restructure-2026-05.md.
    app.add_middleware(LegacyRedirectsMiddleware)

    setup_exception_handlers(app)
    app.include_router(router=router, prefix=settings.API_V1_STR)

    @app.get("/health", tags=["System"])
    async def health_check() -> dict[str, str]:
        """Return a simple health-check response."""
        return {"status": "ok", "environment": settings.ENVIRONMENT}

    container = create_container()
    setup_dishka(container, app)

    return app
