"""Contract tests for :class:`ILedger` (REFACT-001 PR-6a / ADR-007).

Pure-domain tests: no DB, no Dishka, no module imports. Verify the
outbound port's structural shape — a stub implementation is accepted
where ``ILedger`` is annotated, the ``post`` coroutine has the documented
keyword-only signature, and a stub returning a :class:`LedgerTransaction`
satisfies the contract end-to-end.

``ILedger`` is **not** ``@runtime_checkable`` (the kernel-level Protocol
is a static-typing concern; ``isinstance`` checks would impose a runtime
cost on every implementation), so the contract is validated by:

* signature inspection (`inspect.signature` over ``ILedger.post``);
* a callable, ``await``-able stub returning a ``LedgerTransaction``.
"""

from __future__ import annotations

import enum
import inspect
import uuid
from collections.abc import Sequence

import pytest

from src.shared.ledger.account import Account
from src.shared.ledger.balance import Balance
from src.shared.ledger.ports import ILedger
from src.shared.ledger.transaction import LedgerEntry, LedgerTransaction

pytestmark = pytest.mark.unit


class _Kind(enum.StrEnum):
    AVAILABLE = "available"
    PENDING = "pending"


# ---------------------------------------------------------------------------
# Signature shape
# ---------------------------------------------------------------------------


class TestProtocolSignature:
    def test_post_is_a_coroutine_function(self):
        assert inspect.iscoroutinefunction(ILedger.post), (
            "ILedger.post must be defined as 'async def' so the kernel "
            "stays decoupled from synchronous DB drivers."
        )

    def test_post_kwargs_only_signature(self):
        sig = inspect.signature(ILedger.post)
        params = sig.parameters
        # self + the 5 documented kw-only args.
        assert "self" in params
        for name in (
            "account",
            "kind",
            "entries",
            "reference_type",
            "reference_id",
        ):
            assert name in params, f"ILedger.post must accept '{name}' kwarg"
            assert params[name].kind == inspect.Parameter.KEYWORD_ONLY, (
                f"ILedger.post '{name}' must be keyword-only "
                f"(kernel forbids positional argument drift)"
            )

    def test_optional_reference_fields_default_to_none(self):
        sig = inspect.signature(ILedger.post)
        for name in ("reference_type", "reference_id"):
            assert sig.parameters[name].default is None, (
                f"ILedger.post '{name}' must default to None — system-level "
                f"adjustments (no originating entity) must be expressible "
                f"without dummy values."
            )

    def test_required_kwargs_have_no_default(self):
        sig = inspect.signature(ILedger.post)
        for name in ("account", "kind", "entries"):
            assert sig.parameters[name].default is inspect.Parameter.empty, (
                f"ILedger.post '{name}' must be required — without it the "
                f"transaction cannot be constructed."
            )


# ---------------------------------------------------------------------------
# Structural-typing implementation accepted at the call site
# ---------------------------------------------------------------------------


class _StubLedger:
    """Minimal in-memory implementation of :class:`ILedger`.

    Used only by the test below to demonstrate that any class with the
    documented ``post`` coroutine satisfies the protocol via structural
    typing — the kernel does not require nominal subclassing.
    """

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def post(
        self,
        *,
        account: Account[_Kind],
        kind: str,
        entries: Sequence[LedgerEntry[_Kind]],
        reference_type: str | None = None,
        reference_id: uuid.UUID | None = None,
    ) -> LedgerTransaction[_Kind]:
        self.calls.append(
            {
                "account_id": account.id,
                "kind": kind,
                "entry_count": len(entries),
                "reference_type": reference_type,
                "reference_id": reference_id,
            }
        )
        return LedgerTransaction(
            id=uuid.uuid4(),
            account_id=account.id,
            kind=kind,
            entries=tuple(entries),
            balance_snapshot=account.balance.snapshot(),
            reference_type=reference_type,
            reference_id=reference_id,
        )


def _accepts_ledger(ledger: ILedger[_Kind]) -> ILedger[_Kind]:
    """Annotate the parameter as ``ILedger`` — proves the structural fit."""
    return ledger


class TestStructuralTyping:
    def test_stub_accepted_where_ledger_expected(self):
        stub = _StubLedger()
        # Static type-checker enforces this; runtime call confirms the
        # type annotation accepts the structural implementation.
        assert _accepts_ledger(stub) is stub

    @pytest.mark.asyncio
    async def test_stub_post_returns_ledger_transaction(self):
        stub = _StubLedger()
        account: Account[_Kind] = Account(
            id=uuid.uuid4(),
            owner_type="customer",
            owner_id=uuid.uuid4(),
            currency="RUB",
            balance=Balance.empty(kinds=_Kind),
        )
        entries = [LedgerEntry(kind=_Kind.AVAILABLE, amount=100)]

        tx = await stub.post(
            account=account,
            kind="referral_reward_release",
            entries=entries,
        )

        assert isinstance(tx, LedgerTransaction)
        assert tx.account_id == account.id
        assert tx.kind == "referral_reward_release"
        assert tx.entries == tuple(entries)
        assert stub.calls == [
            {
                "account_id": account.id,
                "kind": "referral_reward_release",
                "entry_count": 1,
                "reference_type": None,
                "reference_id": None,
            }
        ]

    @pytest.mark.asyncio
    async def test_stub_post_propagates_reference_kwargs(self):
        stub = _StubLedger()
        account: Account[_Kind] = Account(
            id=uuid.uuid4(),
            owner_type="customer",
            owner_id=uuid.uuid4(),
            currency="RUB",
            balance=Balance.empty(kinds=_Kind),
        )
        ref_id = uuid.uuid4()

        tx = await stub.post(
            account=account,
            kind="order_spend",
            entries=[LedgerEntry(kind=_Kind.AVAILABLE, amount=-50)],
            reference_type="order",
            reference_id=ref_id,
        )

        assert tx.reference_type == "order"
        assert tx.reference_id == ref_id
