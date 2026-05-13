"""Multi-bucket :class:`Balance` value object.

A :class:`Balance` holds a per-balance-kind integer ledger expressed in
the smallest currency unit (kopecks for RUB, cents for USD/EUR, …).
Generic over ``BalanceKindT`` — typically a :class:`StrEnum` declared
by the consumer module:

.. code-block:: python

    class LoyaltyBalanceKind(StrEnum):
        AVAILABLE = "available"
        PENDING = "pending"
        LIFETIME = "lifetime"

    balance = Balance.empty(
        kinds=LoyaltyBalanceKind,
        allow_negative=frozenset({LoyaltyBalanceKind.PENDING}),
    )

The value object is **mutable** (it accumulates state); the immutable
journal of changes lives in :class:`LedgerTransaction`. Mutations are
narrow, named (``credit`` / ``debit`` / ``transfer``), and validate the
non-negative invariant on every kind that is not in ``allow_negative``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Generic, TypeVar

import attrs

from src.shared.ledger.exceptions import InsufficientBalanceError

BalanceKindT = TypeVar("BalanceKindT")


@attrs.define
class Balance(Generic[BalanceKindT]):
    """Multi-bucket integer balance.

    Attributes:
        amounts: Per-kind running totals. Missing kinds default to ``0``.
        allow_negative: Kinds that may go below zero (e.g. ``PENDING``
            when a refund arrives after a release and there is nothing
            available to claw back from).
    """

    amounts: dict[BalanceKindT, int] = attrs.field(factory=dict)
    allow_negative: frozenset[BalanceKindT] = attrs.field(factory=frozenset)

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def empty(
        cls,
        *,
        kinds: Iterable[BalanceKindT],
        allow_negative: Iterable[BalanceKindT] = (),
    ) -> Balance[BalanceKindT]:
        """Construct a Balance with every named kind initialised to zero."""
        return cls(
            amounts={kind: 0 for kind in kinds},
            allow_negative=frozenset(allow_negative),
        )

    # ------------------------------------------------------------------
    # Read API
    # ------------------------------------------------------------------

    def get(self, kind: BalanceKindT) -> int:
        """Return the current amount for ``kind``; ``0`` if untouched."""
        return self.amounts.get(kind, 0)

    def snapshot(self) -> Mapping[BalanceKindT, int]:
        """Defensive copy of the per-kind amounts (read-only contract)."""
        return dict(self.amounts)

    # ------------------------------------------------------------------
    # Mutations (used by ``Account`` and ``Ledger.post``)
    # ------------------------------------------------------------------

    def credit(self, kind: BalanceKindT, amount: int) -> None:
        """Add ``amount`` (must be ``> 0``) to ``kind``."""
        if amount <= 0:
            raise ValueError(
                f"credit amount must be positive (got {amount}); "
                "use debit() for withdrawals"
            )
        self.amounts[kind] = self.amounts.get(kind, 0) + amount

    def debit(self, kind: BalanceKindT, amount: int) -> None:
        """Subtract ``amount`` (must be ``> 0``) from ``kind``.

        Raises:
            InsufficientBalanceError: if the resulting amount would be
                negative and ``kind`` is not listed in
                :attr:`allow_negative`.
        """
        if amount <= 0:
            raise ValueError(
                f"debit amount must be positive (got {amount}); "
                "use credit() for deposits"
            )
        previous = self.amounts.get(kind, 0)
        new_amount = previous - amount
        if new_amount < 0 and kind not in self.allow_negative:
            raise InsufficientBalanceError(
                kind=str(kind),
                requested=amount,
                available=previous,
            )
        self.amounts[kind] = new_amount

    def transfer(
        self,
        *,
        from_kind: BalanceKindT,
        to_kind: BalanceKindT,
        amount: int,
    ) -> None:
        """Move ``amount`` from ``from_kind`` to ``to_kind``.

        Atomic: if the debit would fail, no credit is applied.
        """
        if from_kind == to_kind:
            raise ValueError(
                "transfer requires distinct kinds; got the same on both sides"
            )
        # Debit first so an InsufficientBalanceError leaves both sides untouched.
        self.debit(from_kind, amount)
        self.credit(to_kind, amount)
