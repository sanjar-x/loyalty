"""Contract tests for :class:`StateMachineMixin` (REFACT-001 PR-1b').

Pure-domain tests: no DB, no Dishka, no module imports. The mixin lives
in ``src.shared.interfaces.fsm`` and any future FSM aggregate consumes
it by declaring four ``ClassVar`` attributes (the four PR-1b'' will
attach to Order / PaymentIntent / Shipment).

Coverage matrix:

* ``__init_subclass__`` enforcement -- omitting any of the four
  required ClassVars raises ``TypeError`` at class-creation time.
* ``abstract=True`` opt-out -- intermediate non-instantiable bases
  may inherit without declaring the ClassVars.
* ``_transition`` happy path -- valid edge applies, returns previous
  state, advances ``updated_at``.
* ``_transition`` invalid edge -- raises the configured
  ``_invalid_transition_exc`` with kwargs ``current=`` / ``target=``.
* ``_transition`` already-terminal source -- raises the configured
  ``_already_terminal_exc`` with kwarg ``status=``.
* ``is_terminal`` property -- True iff ``status`` is in
  ``_TERMINAL_STATES``.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime, timedelta
from typing import ClassVar

import pytest

from src.shared.interfaces.fsm import StateMachineMixin

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Test fixtures: a minimal StrEnum + exception pair + concrete aggregate
# ---------------------------------------------------------------------------


class _State(enum.StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    DONE = "done"
    CANCELLED = "cancelled"


class _InvalidTransitionError(Exception):
    def __init__(self, *, current: str, target: str) -> None:
        super().__init__(f"invalid: {current} -> {target}")
        self.current = current
        self.target = target


class _AlreadyTerminalError(Exception):
    def __init__(self, *, status: str) -> None:
        super().__init__(f"already terminal: {status}")
        self.status = status


class _Aggregate(StateMachineMixin[_State]):
    """Minimal FSM-bearing class for contract tests."""

    _ALLOWED_TRANSITIONS: ClassVar[dict[_State, frozenset[_State]]] = {
        _State.DRAFT: frozenset({_State.ACTIVE, _State.CANCELLED}),
        _State.ACTIVE: frozenset({_State.DONE, _State.CANCELLED}),
    }
    _TERMINAL_STATES: ClassVar[frozenset[_State]] = frozenset(
        {_State.DONE, _State.CANCELLED}
    )
    _invalid_transition_exc: ClassVar[type[Exception]] = _InvalidTransitionError
    _already_terminal_exc: ClassVar[type[Exception]] = _AlreadyTerminalError

    def __init__(self, status: _State) -> None:
        self.status: _State = status
        self.updated_at: datetime = datetime.now(UTC) - timedelta(hours=1)


# ---------------------------------------------------------------------------
# __init_subclass__ enforcement
# ---------------------------------------------------------------------------


class TestSubclassEnforcement:
    def test_missing_all_four_classvars_raises(self):
        with pytest.raises(TypeError) as exc_info:

            class _Bad(StateMachineMixin[_State]):
                pass

        msg = str(exc_info.value)
        assert "_ALLOWED_TRANSITIONS" in msg
        assert "_TERMINAL_STATES" in msg
        assert "_invalid_transition_exc" in msg
        assert "_already_terminal_exc" in msg

    def test_missing_one_classvar_raises_with_specific_name(self):
        with pytest.raises(TypeError) as exc_info:

            class _PartiallyConfigured(StateMachineMixin[_State]):
                _ALLOWED_TRANSITIONS: ClassVar[dict] = {}
                _TERMINAL_STATES: ClassVar[frozenset] = frozenset()
                _invalid_transition_exc: ClassVar[type[Exception]] = (
                    _InvalidTransitionError
                )
                # _already_terminal_exc intentionally missing

        assert "_already_terminal_exc" in str(exc_info.value)

    def test_abstract_opt_out_allows_no_classvars(self):
        # ``abstract=True`` lets an intermediate base skip the four ClassVars
        # so that a non-instantiable shared parent does not have to declare
        # module-specific exception types.
        class _AbstractBase(StateMachineMixin[_State], abstract=True):
            pass

        # Concrete subclass that fills the contract is still required to
        # declare them -- abstract does NOT propagate.
        with pytest.raises(TypeError):

            class _StillBad(_AbstractBase):
                pass


# ---------------------------------------------------------------------------
# _transition behavior
# ---------------------------------------------------------------------------


class TestTransition:
    def test_valid_edge_updates_status_and_returns_previous(self):
        agg = _Aggregate(_State.DRAFT)
        before = agg.updated_at

        previous = agg._transition(_State.ACTIVE)

        assert previous is _State.DRAFT
        assert agg.status is _State.ACTIVE
        assert agg.updated_at > before

    def test_invalid_edge_raises_invalid_transition_exc(self):
        agg = _Aggregate(_State.DRAFT)
        with pytest.raises(_InvalidTransitionError) as exc_info:
            agg._transition(_State.DONE)
        assert exc_info.value.current == "draft"
        assert exc_info.value.target == "done"
        # State must not have been mutated on a rejected transition.
        assert agg.status is _State.DRAFT

    def test_already_terminal_source_raises_already_terminal_exc(self):
        agg = _Aggregate(_State.DONE)
        with pytest.raises(_AlreadyTerminalError) as exc_info:
            agg._transition(_State.ACTIVE)
        assert exc_info.value.status == "done"
        assert agg.status is _State.DONE

    def test_terminal_check_takes_priority_over_invalid_check(self):
        # A terminal source with a non-allowed target should report
        # the terminal failure mode, not the invalid-transition one --
        # the mixin checks _TERMINAL_STATES first by design.
        agg = _Aggregate(_State.CANCELLED)
        with pytest.raises(_AlreadyTerminalError):
            agg._transition(_State.DRAFT)


# ---------------------------------------------------------------------------
# is_terminal property
# ---------------------------------------------------------------------------


class TestIsTerminal:
    def test_returns_true_for_terminal_state(self):
        assert _Aggregate(_State.DONE).is_terminal is True
        assert _Aggregate(_State.CANCELLED).is_terminal is True

    def test_returns_false_for_non_terminal_state(self):
        assert _Aggregate(_State.DRAFT).is_terminal is False
        assert _Aggregate(_State.ACTIVE).is_terminal is False
