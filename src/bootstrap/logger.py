"""Structured logging configuration using structlog.

Sets up a dual-mode logging pipeline:
- **Development** (``ENVIRONMENT=dev`` or ``DEBUG=True``): coloured console
  output with call-site information (file, function, line number).
- **Production**: machine-readable JSON lines written to stdout for
  ingestion by a log aggregator.

Third-party loggers (uvicorn, FastAPI) are reconfigured to propagate
through the same pipeline so that all output is uniformly formatted.
"""

import logging
import sys
from collections.abc import Iterable
from typing import Any, TextIO

import structlog
from structlog.types import Processor

from src.bootstrap.config import settings


def _get_shared_processors() -> Iterable[Processor]:
    """Return the ordered list of structlog processors shared by all formatters.

    These processors run before the final renderer, regardless of
    whether the log event originates from structlog or the stdlib
    ``logging`` module.

    Returns:
        An iterable of structlog processors.
    """
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
    """Redirect third-party library loggers through the structlog pipeline.

    Uvicorn and FastAPI loggers have their handlers removed and
    propagation enabled so that their output is captured by the root
    logger.  ``uvicorn.access`` is silenced entirely to avoid duplicate
    access logs (the application emits its own via middleware).
    """
    for _log in ["uvicorn", "uvicorn.error", "fastapi"]:
        logger_instance = logging.getLogger(_log)
        logger_instance.handlers.clear()
        logger_instance.propagate = True

    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers.clear()
    uvicorn_access.propagate = False


def setup_logging() -> None:
    """Initialise the application-wide logging configuration.

    Must be called once at process startup, before any loggers are used.
    Configures structlog, selects the appropriate renderer based on the
    current environment, and attaches a single ``StreamHandler`` to the
    root logger.
    """
    shared_processors = list(_get_shared_processors())

    structlog.configure(
        processors=shared_processors + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
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

    handler: logging.StreamHandler[TextIO | Any] = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)
    _configure_third_party_loggers()
