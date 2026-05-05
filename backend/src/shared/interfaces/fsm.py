"""Reusable Finite State Machine mixin for domain aggregates.

Aggregates whose lifecycle is a directed graph of named states (Cart,
Order, Payment, Shipment, Product, Referral, ...) all share the same
mechanical contract:

* a ``status`` attribute typed as a ``StrEnum`` member;
* an ``_ALLOWED_TRANSITIONS`` mapping that lists which target states a
  given source state may move to;
* a ``_TERMINAL_STATES`` set whose members are sinks (no outgoing edge);
* a private ``_transition()`` helper that validates and applies a move.

This mixin centralizes that mechanic so every aggregate gets:

* identical edge-validation semantics (terminal-first, then allowed),
* identical exception parameter naming (``current=`` / ``target=``),
* an ``is_terminal`` property,
* zero hand-written boilerplate per aggregate.

Module-specific behaviour stays in the subclass: each aggregate
declares its own pair of exception classes (so that
``OrderInvalidTransitionError`` and ``PaymentIntentInvalidTransitionError``
can carry module-specific context and HTTP-status mapping) and points
at them via two ``ClassVar`` attributes.

Typical usage::

    @dataclass
    class Order(AggregateRoot, StateMachineMixin[OrderStatus]):
        _ALLOWED_TRANSITIONS = { ... }
        _TERMINAL_STATES = TERMINAL_STATUSES
        _invalid_transition_exc = OrderInvalidTransitionError
        _already_terminal_exc = OrderAlreadyTerminalError

        status: OrderStatus
        updated_at: datetime
        ...

        def mark_paid(self, ...) -> None:
            self._transition(OrderStatus.PAID)
            ...

The mixin requires the host aggregate to expose two attributes —
``status`` (the current state) and ``updated_at`` (a UTC datetime that
the mixin advances on every successful transition). It does **not**
manage optimistic-locking ``version`` — that is the repository's
responsibility on persistence.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import ClassVar, Generic, Protocol, TypeVar


class _StateValueLike(Protocol):
    """Structural type for a state — usually a ``StrEnum`` member.

    The mixin only relies on ``.value`` to format error messages, so any
    object whose ``value`` is a string works.
    """

    @property
    def value(self) -> str: ...  # pragma: no cover — Protocol member


# Bound to ``_StateValueLike`` so the mixin can rely on ``.value`` for
# error formatting at type-check time.
StateT = TypeVar("StateT", bound=_StateValueLike)


class _InvalidTransitionExc(Protocol):
    """Constructor signature for module-specific invalid-transition errors."""

    def __call__(
        self, *, current: str, target: str
    ) -> Exception: ...  # pragma: no cover — Protocol member


class _AlreadyTerminalExc(Protocol):
    """Constructor signature for module-specific already-terminal errors."""

    def __call__(
        self, *, status: str
    ) -> Exception: ...  # pragma: no cover — Protocol member


class StateMachineMixin(Generic[StateT]):
    """Reusable FSM implementation for aggregates.

    Subclasses MUST set four ``ClassVar`` attributes:

    * ``_ALLOWED_TRANSITIONS`` — directed graph of legal moves.
    * ``_TERMINAL_STATES``    — frozenset of sink states.
    * ``_invalid_transition_exc`` — exception class raised when a move
      is not in ``_ALLOWED_TRANSITIONS[current]``.
    * ``_already_terminal_exc`` — exception class raised when a move
      is attempted from a state in ``_TERMINAL_STATES``.

    Both exception classes MUST accept the keyword arguments shown in
    :class:`_InvalidTransitionExc` and :class:`_AlreadyTerminalExc`.
    ``__init_subclass__`` enforces the presence of all four attributes
    at class-creation time so that a forgotten declaration fails fast.
    """

    # ``ClassVar[...]`` containing the class TypeVar ``StateT`` is rejected
    # by strict type-checkers (PEP 526 — ClassVar must not capture
    # generic class parameters). The intent is conveyed at the docstring
    # level: each subclass declares the concrete enum's mapping shape;
    # at runtime these are plain class attributes.
    _ALLOWED_TRANSITIONS: ClassVar[Mapping[StateT, frozenset[StateT]]]  # ty: ignore[invalid-type-form]
    _TERMINAL_STATES: ClassVar[frozenset[StateT]]  # ty: ignore[invalid-type-form]
    # Typed as ``Callable[..., Exception]`` rather than ``type[Exception]``
    # because subclasses MUST conform to the ``_InvalidTransitionExc`` /
    # ``_AlreadyTerminalExc`` Protocols (kwargs-only ``current=``/``target=``
    # / ``status=``) — broader than what ``BaseException.__init__(*args)``
    # accepts. The Protocols document the contract; the ``Callable`` typing
    # tells the type-checker the call shape is module-controlled.
    _invalid_transition_exc: ClassVar[Callable[..., Exception]]
    _already_terminal_exc: ClassVar[Callable[..., Exception]]

    # Subclass-controlled opt-out for intermediate / abstract bases that
    # do not yet have the four ClassVars set (e.g. a module-internal
    # AbstractAggregate that is itself never instantiated).
    __abstract_fsm__: ClassVar[bool] = False

    def __init_subclass__(cls, *, abstract: bool = False, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        cls.__abstract_fsm__ = abstract
        if abstract:
            return

        missing = [
            name
            for name in (
                "_ALLOWED_TRANSITIONS",
                "_TERMINAL_STATES",
                "_invalid_transition_exc",
                "_already_terminal_exc",
            )
            if not hasattr(cls, name)
        ]
        if missing:
            raise TypeError(
                f"{cls.__name__} inherits StateMachineMixin but does not "
                f"declare: {', '.join(missing)}. Either set them on the "
                "class or pass ``abstract=True`` to the inheritance."
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_terminal(self) -> bool:
        """``True`` iff ``self.status`` is a terminal sink."""
        return self.status in self._TERMINAL_STATES  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Transition primitive
    # ------------------------------------------------------------------

    def _transition(self, target: StateT) -> StateT:
        """Validate ``current → target`` and apply the move.

        Returns the previous state so callers can branch on it without
        re-reading ``self.status``.

        Args:
            target: The desired next state.

        Returns:
            The state that was current immediately before the move
            (i.e. the value of ``self.status`` before the assignment).

        Raises:
            self._already_terminal_exc: if the aggregate is already in
                a terminal state — no further moves are permitted.
            self._invalid_transition_exc: if ``target`` is not present
                in ``self._ALLOWED_TRANSITIONS[current]``.
        """
        previous: StateT = self.status  # type: ignore[attr-defined]
        if previous in self._TERMINAL_STATES:
            raise self._already_terminal_exc(status=previous.value)  # type: ignore[arg-type]
        allowed = self._ALLOWED_TRANSITIONS.get(previous, frozenset())
        if target not in allowed:
            raise self._invalid_transition_exc(  # type: ignore[arg-type]
                current=previous.value,
                target=target.value,  # type: ignore[arg-type]
            )
        self.status = target  # type: ignore[attr-defined]
        self.updated_at = datetime.now(UTC)  # type: ignore[attr-defined]
        return previous
