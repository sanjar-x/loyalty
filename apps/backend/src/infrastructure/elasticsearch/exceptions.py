"""Translate ``elastic_transport`` / ``elasticsearch`` errors into the
shared ``AppException`` hierarchy.

Adapters that talk to Elasticsearch wrap their client calls with
:func:`translate` (or use the helpers in :mod:`bulk` / :mod:`health`
which already wrap internally). The result is that the global FastAPI
exception handler can render a single, predictable error envelope —
the same one used for SQL / Redis / domain errors — without each
adapter re-implementing status-code mapping.

The ES-specific exception subclasses live in :mod:`src.shared.exceptions`
so they participate in the same import-graph as ``NotFoundError`` /
``ConflictError`` and stay reachable from domain layers that need to
declare them in type hints without pulling infrastructure imports.
"""

from __future__ import annotations

from elastic_transport import (
    ApiError,
    ConnectionTimeout,
    TransportError,
)
from elastic_transport import (
    ConnectionError as ESConnectionError,
)
from elasticsearch import NotFoundError as ESNotFoundError

from src.shared.exceptions import (
    AppException,
    SearchBackendError,
    SearchConflictError,
    SearchIndexNotFoundError,
)


def translate(
    exc: BaseException,
    *,
    index: str | None = None,
    doc_id: str | None = None,
) -> AppException:
    """Map an ``elasticsearch`` / ``elastic_transport`` exception to an
    :class:`AppException` subclass.

    ``index`` / ``doc_id`` are optional hints used to enrich the
    resulting error envelope (e.g. ``SEARCH_DOC_CONFLICT`` references
    them in ``details``). They are passed in by the caller because the
    raw transport error does not always carry the operation context.

    The function returns the translated exception — callers are
    expected to ``raise`` it themselves so the original traceback is
    preserved via ``from exc``.

    Mapping:
    * ``NotFoundError`` (or ``ApiError`` with status 404) →
      :class:`SearchIndexNotFoundError` (or a generic 404 envelope when
      no ``index`` is supplied).
    * ``ApiError`` with status 409 → :class:`SearchConflictError`
      (optimistic-concurrency / version mismatch).
    * ``ConnectionError`` / ``ConnectionTimeout`` / 5xx ``ApiError`` /
      generic ``TransportError`` → :class:`SearchBackendError`
      (transient, retryable).
    * Anything else propagates unchanged — programmer errors
      (malformed query, mapping mismatch) should surface as 500 with
      the original stack so the bug is visible.
    """
    if isinstance(exc, ESNotFoundError):
        return _to_index_not_found(exc, index=index)

    if isinstance(exc, ApiError):
        status = _status_code(exc)
        if status == 404:
            return _to_index_not_found(exc, index=index)
        if status == 409:
            return SearchConflictError(
                index=index or "<unknown>",
                doc_id=doc_id or "<unknown>",
                message=str(exc),
            )
        if status >= 500:
            return SearchBackendError(
                message=f"Elasticsearch responded with HTTP {status}",
                details={"status": status, "index": index}
                if index
                else {"status": status},
            )
        # 4xx other than 404/409 — programmer error (bad query, schema
        # mismatch). Return a generic backend error rather than masking
        # it as a 503; the operator should see the original message.
        return SearchBackendError(
            message=f"Elasticsearch API error: {exc}",
            details={"status": status},
        )

    if isinstance(exc, (ESConnectionError, ConnectionTimeout)):
        return SearchBackendError(
            message="Elasticsearch is unreachable",
            details={"reason": exc.__class__.__name__},
        )

    if isinstance(exc, TransportError):
        return SearchBackendError(
            message=f"Elasticsearch transport error: {exc}",
            details={"reason": exc.__class__.__name__},
        )

    # Not an ES exception we can usefully translate.
    return SearchBackendError(
        message=f"Unexpected error talking to Elasticsearch: {exc}",
        details={"reason": exc.__class__.__name__},
    )


def _to_index_not_found(
    exc: BaseException, *, index: str | None
) -> SearchIndexNotFoundError:
    return SearchIndexNotFoundError(
        index=index or "<unknown>",
        message=str(exc) if not index else None,
    )


def _status_code(exc: ApiError) -> int:
    """Extract the integer HTTP status from an ``ApiError`` safely.

    ``ApiError.status_code`` is the canonical attribute on
    ``elastic_transport>=8``; older transports surfaced it as ``status``.
    Falls back to 0 so the caller's branches still work without raising
    ``AttributeError`` if the transport library shape changes.
    """
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    try:
        return int(status) if status is not None else 0
    except TypeError, ValueError:
        return 0
