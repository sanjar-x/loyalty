# src\bootstrap\app.py
from contextlib import asynccontextmanager

import structlog
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from structlog.stdlib import BoundLogger

from src.api.exceptions.handlers import setup_exception_handlers
from src.api.middlewares.logger import AccessLoggerMiddleware
from src.api.router import router
from src.bootstrap.broker import broker
from src.bootstrap.config import settings
from src.bootstrap.container import create_container
from src.bootstrap.logger import setup_logging

setup_logging()

logger: BoundLogger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Запуск Enterprise API",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
    )

    if not broker.is_worker_process:
        logger.info("Запуск TaskIQ брокера в рамках API...")
        await broker.startup()

    yield

    if not broker.is_worker_process:
        logger.info("Остановка TaskIQ брокера...")
        await broker.shutdown()

    if hasattr(app.state, "dishka_container"):
        logger.info("Закрытие IoC контейнера и пулов соединений...")
        await app.state.dishka_container.close()

    logger.info("Остановка Enterprise API. Очистка ресурсов завершена.")


def create_app() -> FastAPI:
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
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.add_middleware(AccessLoggerMiddleware)  # ty:ignore[invalid-argument-type]

    setup_exception_handlers(app)
    app.include_router(router=router, prefix=settings.API_V1_STR)

    @app.get("/health", tags=["System"])
    async def health_check():
        return {"status": "ok", "environment": settings.ENVIRONMENT}

    container = create_container()
    setup_dishka(container, app)

    return app
