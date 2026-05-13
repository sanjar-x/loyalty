"""Ledger domain exceptions.

All ledger errors inherit from :class:`AppException` so that the
presentation layer's global exception handler maps them to the right
HTTP status code automatically.
"""

from __future__ import annotations

from src.shared.exceptions import AppException, ConflictError


class LedgerError(AppException):
    """Base class for any ledger-domain error.

    Generic enough to be ``except``-clause-friendly when callers want to
    treat all ledger failures uniformly (e.g. a structured-log catch-all
    in a high-level handler).
    """


class InsufficientBalanceError(LedgerError, ConflictError):
    """A debit was rejected because the post-debit balance would go below
    zero on a balance kind that does not allow negative values.

    Surface as HTTP 409 — the request is well-formed and the account
    exists, but its current state cannot satisfy the operation.
    """

    def __init__(self, *, kind: str, requested: int, available: int) -> None:
        super().__init__(
            message=(
                f"Insufficient balance on '{kind}': "
                f"requested {requested}, available {available}"
            ),
            error_code="LEDGER_INSUFFICIENT_BALANCE",
            details={
                "kind": kind,
                "requested": requested,
                "available": available,
            },
        )


class InvalidLedgerEntryError(LedgerError, ConflictError):
    """An entry was rejected at construction (zero-amount, malformed)."""

    def __init__(self, *, reason: str) -> None:
        super().__init__(
            message=f"Invalid ledger entry: {reason}",
            error_code="LEDGER_INVALID_ENTRY",
            details={"reason": reason},
        )


class EmptyLedgerTransactionError(LedgerError, ConflictError):
    """A transaction was posted with zero entries.

    Every transaction must touch at least one balance — an empty post
    is meaningless and almost certainly a programming error.
    """

    def __init__(self) -> None:
        super().__init__(
            message="Ledger transaction must contain at least one entry",
            error_code="LEDGER_EMPTY_TRANSACTION",
        )
