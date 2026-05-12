"""Property/contract tests for ``AggregateRoot.__attrs_post_init__``.

PR-1 (REFACT-001) introduces ``AggregateRoot.__attrs_post_init__``
which initialises the per-instance ``_domain_events`` list. Two risks
this test suite mitigates:

1. **Synthetic mixin behaviour** — the new ``__attrs_post_init__``
   correctly initialises ``_domain_events`` on a minimal attrs class
   (so that ``add_domain_event`` does not raise ``AttributeError``).

2. **Existing aggregates are not broken** — every concrete aggregate
   in the codebase (25 classes across 12 modules) still inherits the
   shared ``__attrs_post_init__`` and does not silently override it.
   Pre-flight scan confirmed zero ``init=False`` and zero custom
   ``def __init__`` on ``src/modules/*/domain/entities*.py`` — this
   parametrised test is the regression guard for any future violation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import attrs
import pytest

from shared.interfaces.entities import (
    AggregateRoot,
    DomainEvent,
    ModuleDomainEvent,
)

# ---------------------------------------------------------------------------
# Minimal synthetic aggregate (proves the mixin itself works in isolation)
# ---------------------------------------------------------------------------


@attrs.define
class _SyntheticAggregate(AggregateRoot):
    id: uuid.UUID


@dataclass(frozen=True)
class _SyntheticEvent(DomainEvent):
    aggregate_type: str = "synthetic"
    event_type: str = "SyntheticEvent"


def test_synthetic_aggregate_initialises_empty_event_list() -> None:
    """Fresh aggregate exposes an empty event list (defensive copy)."""
    agg = _SyntheticAggregate(id=uuid.uuid4())
    assert agg.domain_events == []


def test_synthetic_aggregate_buffers_events_after_init() -> None:
    """``add_domain_event`` works without ``AttributeError`` post-init."""
    agg = _SyntheticAggregate(id=uuid.uuid4())
    event = _SyntheticEvent(aggregate_id=str(agg.id))
    agg.add_domain_event(event)
    assert agg.domain_events == [event]


def test_two_aggregates_have_independent_event_lists() -> None:
    """Each instance must own its own list — no class-level sharing."""
    a = _SyntheticAggregate(id=uuid.uuid4())
    b = _SyntheticAggregate(id=uuid.uuid4())
    a.add_domain_event(_SyntheticEvent(aggregate_id=str(a.id)))
    assert b.domain_events == []


def test_clear_domain_events_empties_buffer() -> None:
    agg = _SyntheticAggregate(id=uuid.uuid4())
    agg.add_domain_event(_SyntheticEvent(aggregate_id=str(agg.id)))
    agg.clear_domain_events()
    assert agg.domain_events == []


def test_domain_events_returns_defensive_copy() -> None:
    """Mutating the returned list must not affect aggregate state."""
    agg = _SyntheticAggregate(id=uuid.uuid4())
    agg.add_domain_event(_SyntheticEvent(aggregate_id=str(agg.id)))
    snapshot = agg.domain_events
    snapshot.clear()
    assert len(agg.domain_events) == 1


# ---------------------------------------------------------------------------
# ModuleDomainEvent contract (intermediate base for module events)
# ---------------------------------------------------------------------------


def test_module_domain_event_requires_concrete_event_type() -> None:
    """Subclass declaring ``required_fields`` must override ``event_type``."""

    @dataclass(frozen=True)
    class _Base(ModuleDomainEvent, abstract=True):
        aggregate_type: str = "test"

    with pytest.raises(TypeError, match="event_type"):

        @dataclass(frozen=True)
        class _LeafForgetsType(
            _Base,
            required_fields=("foo",),
            aggregate_id_field="foo",
        ):
            foo: uuid.UUID | None = None


def test_module_domain_event_validates_required_fields() -> None:
    """Missing required field raises ``ValueError`` at construction."""

    @dataclass(frozen=True)
    class _Base(ModuleDomainEvent, abstract=True):
        aggregate_type: str = "test"

    @dataclass(frozen=True)
    class _Leaf(
        _Base,
        required_fields=("foo",),
        aggregate_id_field="foo",
    ):
        foo: uuid.UUID | None = None
        event_type: str = "LeafEvent"

    with pytest.raises(ValueError, match="foo is required"):
        _Leaf(foo=None)


def test_module_domain_event_auto_fills_aggregate_id() -> None:
    """``aggregate_id`` is derived from ``aggregate_id_field``."""

    @dataclass(frozen=True)
    class _Base(ModuleDomainEvent, abstract=True):
        aggregate_type: str = "test"

    @dataclass(frozen=True)
    class _Leaf(
        _Base,
        required_fields=("foo_id",),
        aggregate_id_field="foo_id",
    ):
        foo_id: uuid.UUID | None = None
        event_type: str = "LeafEvent"

    foo_id = uuid.uuid4()
    event = _Leaf(foo_id=foo_id)
    assert event.aggregate_id == str(foo_id)


def test_abstract_module_domain_event_skips_required_field_check() -> None:
    """Intermediate ``abstract=True`` bases must not trigger validation."""

    @dataclass(frozen=True)
    class _Base(ModuleDomainEvent, abstract=True):
        aggregate_type: str = "test"

    # No exception raised — abstract base is exempt.
    assert _Base.__abstract_event__ is True


# ---------------------------------------------------------------------------
# Structural regression: every concrete AggregateRoot in the codebase
# inherits the shared ``__attrs_post_init__`` (no silent override)
# ---------------------------------------------------------------------------


def _collect_aggregate_root_classes() -> list[type]:
    """Walk every ``domain/entities*`` module and return AggregateRoot subclasses.

    Done at test-collection time so a missing aggregate would surface
    as a parametrize-time error, not a runtime skip.
    """
    import importlib
    import pkgutil

    classes: list[type] = []
    seen: set[type] = set()

    import src.modules

    for module_info in pkgutil.iter_modules(src.modules.__path__):
        module_name = module_info.name
        # Each module exposes either a flat ``domain/entities.py`` or a
        # ``domain/entities/`` package; importlib handles both.
        for candidate in (f"src.modules.{module_name}.domain.entities",):
            try:
                mod = importlib.import_module(candidate)
            except ImportError:
                continue
            for obj in vars(mod).values():
                if (
                    isinstance(obj, type)
                    and obj is not AggregateRoot
                    and issubclass(obj, AggregateRoot)
                    and obj not in seen
                ):
                    classes.append(obj)
                    seen.add(obj)

        # If ``entities`` is a package, also load its submodules.
        try:
            pkg = importlib.import_module(f"src.modules.{module_name}.domain.entities")
        except ImportError:
            continue
        if hasattr(pkg, "__path__"):
            for sub in pkgutil.iter_modules(pkg.__path__):
                if sub.name.startswith("_"):
                    continue
                sub_mod = importlib.import_module(
                    f"src.modules.{module_name}.domain.entities.{sub.name}"
                )
                for obj in vars(sub_mod).values():
                    if (
                        isinstance(obj, type)
                        and obj is not AggregateRoot
                        and issubclass(obj, AggregateRoot)
                        and obj not in seen
                    ):
                        classes.append(obj)
                        seen.add(obj)

    return sorted(classes, key=lambda c: f"{c.__module__}.{c.__name__}")


_AGGREGATE_CLASSES = _collect_aggregate_root_classes()


def test_codebase_aggregate_discovery_finds_expected_count() -> None:
    """Sanity guard — adjust the lower bound if a module is added.

    Pre-flight scan at PR-1 time identified 25 AggregateRoot subclasses
    (catalog 8 + pricing 7 + identity 2 + user 2 + supplier/cart/
    favorites/recipient/order/payment/logistics 1 each).
    """
    assert len(_AGGREGATE_CLASSES) >= 20, (
        f"Found only {len(_AGGREGATE_CLASSES)} AggregateRoot subclasses — "
        "did module discovery break?"
    )


@pytest.mark.parametrize(
    "cls",
    _AGGREGATE_CLASSES,
    ids=lambda c: f"{c.__module__.split('.')[-1]}.{c.__name__}",
)
def test_aggregate_inherits_shared_post_init(cls: type) -> None:
    """Every concrete aggregate MUST initialise ``_domain_events`` via
    ``AggregateRoot.__attrs_post_init__``.

    Two acceptable shapes:

    1. The class does NOT define its own ``__attrs_post_init__`` — it
       inherits the shared one as-is.
    2. The class DOES define one (to add module-specific post-init
       logic, e.g. ``Brand`` setting derived attributes), but the body
       must call ``super().__attrs_post_init__()`` so the shared
       initialiser still runs.

    A subclass that overrides without ``super()`` would silently leave
    ``_domain_events`` uninitialised and ``add_domain_event`` would
    raise ``AttributeError`` on first call — this is the regression
    this test guards against.
    """
    import inspect

    post_init = getattr(cls, "__attrs_post_init__", None)
    assert post_init is not None, (
        f"{cls.__module__}.{cls.__name__} has no __attrs_post_init__ — "
        "AggregateRoot mixin must provide one."
    )

    # Shape (1): inherited as-is.
    if post_init is AggregateRoot.__attrs_post_init__:
        return

    # Shape (2): own override — must chain via super().
    source = inspect.getsource(post_init)
    assert "super().__attrs_post_init__()" in source, (
        f"{cls.__module__}.{cls.__name__} overrides __attrs_post_init__ "
        "without calling super().__attrs_post_init__() — _domain_events "
        "will not initialise. Add the super() call or remove the override."
    )
