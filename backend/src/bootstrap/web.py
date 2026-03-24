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
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from structlog.stdlib import BoundLogger

from src.api.exceptions.handlers import setup_exception_handlers
from src.api.middlewares.logger import AccessLoggerMiddleware
from src.api.router import router
from src.bootstrap.broker import broker
from src.bootstrap.config import settings
from src.bootstrap.container import create_container
from src.bootstrap.logger import setup_logging
from src.modules.catalog.management.sync_attributes import sync_attributes
from src.modules.catalog.management.sync_brands import sync_brands
from src.modules.catalog.management.sync_categories import sync_categories
from src.modules.identity.management.sync_system_roles import sync_system_roles
from src.modules.supplier.management.sync_suppliers import sync_suppliers

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

    # Sync system roles/permissions on every startup (idempotent upsert)
    container = app.state.dishka_container
    async with container() as app_scope:
        factory = await app_scope.get(async_sessionmaker[AsyncSession])
        await sync_system_roles(factory)
        await sync_categories(factory)
        await sync_brands(factory)
        await sync_attributes(factory)
        await sync_suppliers(factory)

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
            CORSMiddleware,  # ty:ignore[invalid-argument-type]
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        )

    app.add_middleware(AccessLoggerMiddleware)  # ty:ignore[invalid-argument-type]

    setup_exception_handlers(app)
    app.include_router(router=router, prefix=settings.API_V1_STR)

    @app.get("/health", tags=["System"])
    async def health_check() -> dict[str, str]:
        """Return a simple health-check response."""
        return {"status": "ok", "environment": settings.ENVIRONMENT}

    container = create_container()
    setup_dishka(container, app)

    return app
