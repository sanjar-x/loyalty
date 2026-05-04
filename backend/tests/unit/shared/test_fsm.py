"""Tests for :class:`src.shared.interfaces.fsm.StateMachineMixin`.

Covers:

* declaration-time integrity (missing ClassVars are caught immediately);
* transition primitive semantics (terminal-first guard, then allowed-set);
* ``is_terminal`` property;
* exception parameter contracts (``current=`` / ``target=`` / ``status=``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import ClassVar

import pytest

from src.shared.interfaces.fsm import StateMachineMixin

# ---------------------------------------------------------------------------
# Fixtures: a tiny three-state FSM with two terminals
# ---------------------------------------------------------------------------


class _State(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    DONE = "done"
    FAILED = "failed"


class _SampleInvalidTransitionError(Exception):
    def __init__(self, *, current: str, target: str) -> None:
        super().__init__(f"{current} → {target}")
        self.current = current
        self.target = target


class _SampleAlreadyTerminalError(Exception):
    def __init__(self, *, status: str) -> None:
        super().__init__(f"already terminal: {status}")
        self.status = status


@dataclass
class _SampleAggregate(StateMachineMixin[_State]):
    _ALLOWED_TRANSITIONS: ClassVar[dict[_State, frozenset[_State]]] = {
        _State.DRAFT: frozenset({_State.ACTIVE, _State.FAILED}),
        _State.ACTIVE: frozenset({_State.DONE, _State.FAILED}),
        _State.DONE: frozenset(),
        _State.FAILED: frozenset(),
    }
    _TERMINAL_STATES: ClassVar[frozenset[_State]] = frozenset(
        {_State.DONE, _State.FAILED}
    )
    _invalid_transition_exc: ClassVar[type[Exception]] = _SampleInvalidTransitionError
    _already_terminal_exc: ClassVar[type[Exception]] = _SampleAlreadyTerminalError

    status: _State = _State.DRAFT
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Declaration-time integrity
# ---------------------------------------------------------------------------


class TestDeclarationContract:
    def test_missing_allowed_transitions_raises(self) -> None:
        with pytest.raises(TypeError, match="_ALLOWED_TRANSITIONS"):

            class _Bad(StateMachineMixin[_State]):
                _TERMINAL_STATES: ClassVar[frozenset[_State]] = frozenset()
                _invalid_transition_exc = _SampleInvalidTransitionError
                _already_terminal_exc = _SampleAlreadyTerminalError

    def test_missing_exception_classes_raises(self) -> None:
        with pytest.raises(TypeError, match="_invalid_transition_exc"):

            class _Bad(StateMachineMixin[_State]):
                _ALLOWED_TRANSITIONS: ClassVar[dict[_State, frozenset[_State]]] = {}
                _TERMINAL_STATES: ClassVar[frozenset[_State]] = frozenset()

    def test_abstract_intermediate_skips_check(self) -> None:
        """``abstract=True`` opts an intermediate base out of the check."""

        class _IntermediateAggregate(StateMachineMixin[_State], abstract=True):
            pass

        assert _IntermediateAggregate.__abstract_fsm__ is True


# ---------------------------------------------------------------------------
# Runtime semantics
# ---------------------------------------------------------------------------


class TestTransitionSemantics:
    def test_legal_transition_updates_status_and_timestamp(self) -> None:
        agg = _SampleAggregate()
        before = agg.updated_at

        previous = agg._transition(_State.ACTIVE)

        assert previous == _State.DRAFT
        assert agg.status == _State.ACTIVE
        assert agg.updated_at >= before

    def test_returns_previous_state(self) -> None:
        agg = _SampleAggregate(status=_State.ACTIVE)
        assert agg._transition(_State.DONE) == _State.ACTIVE

    def test_disallowed_transition_raises_invalid_transition(self) -> None:
        agg = _SampleAggregate()
        with pytest.raises(_SampleInvalidTransitionError) as exc_info:
            agg._transition(_State.DONE)  # DRAFT → DONE not allowed
        assert exc_info.value.current == "draft"
        assert exc_info.value.target == "done"
        # status must not have changed
        assert agg.status == _State.DRAFT

    def test_terminal_state_raises_already_terminal_first(self) -> None:
        # The terminal check fires *before* the allowed-set check, so
        # an attempt to leave a terminal state surfaces the dedicated
        # AlreadyTerminal error rather than the generic InvalidTransition.
        agg = _SampleAggregate(status=_State.DONE)
        with pytest.raises(_SampleAlreadyTerminalError) as exc_info:
            agg._transition(_State.ACTIVE)
        assert exc_info.value.status == "done"
        assert agg.status == _State.DONE  # unchanged

    def test_is_terminal_reflects_terminal_states(self) -> None:
        assert _SampleAggregate(status=_State.DRAFT).is_terminal is False
        assert _SampleAggregate(status=_State.ACTIVE).is_terminal is False
        assert _SampleAggregate(status=_State.DONE).is_terminal is True
        assert _SampleAggregate(status=_State.FAILED).is_terminal is True
