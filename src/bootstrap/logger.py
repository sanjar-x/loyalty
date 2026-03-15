# src/bootstrap/logger.py
import logging
import sys
from typing import Any, Iterable, TextIO

import structlog
from structlog.types import Processor

from src.bootstrap.config import settings


def _get_shared_processors() -> Iterable[Processor]:
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.stdlib.ExtraAdder(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.ENVIRONMENT == "dev" or settings.DEBUG:
        processors.append(
            structlog.processors.CallsiteParameterAdder(
                {
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                }
            )
        )

    processors.append(structlog.processors.UnicodeDecoder())
    return processors


def _configure_third_party_loggers() -> None:
    for _log in ["uvicorn", "uvicorn.error", "fastapi"]:
        logger_instance = logging.getLogger(_log)
        logger_instance.handlers.clear()
        logger_instance.propagate = True

    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers.clear()
    uvicorn_access.propagate = False


def setup_logging() -> None:
    shared_processors = list(_get_shared_processors())

    structlog.configure(
        processors=shared_processors
        + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    if settings.ENVIRONMENT == "dev" or settings.DEBUG:
        renderer = structlog.dev.ConsoleRenderer(colors=True)
        log_level = logging.DEBUG
    else:
        renderer = structlog.processors.JSONRenderer()
        log_level = logging.INFO

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler: logging.StreamHandler[TextIO | Any] = logging.StreamHandler(
        stream=sys.stdout
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)
    _configure_third_party_loggers()
