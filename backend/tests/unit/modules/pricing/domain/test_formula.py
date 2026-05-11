"""Unit tests for the FormulaVersion aggregate and AST validator."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from src.modules.pricing.domain.entities.formula import FormulaVersion, _validate_ast
from src.modules.pricing.domain.events import (
    FormulaDraftDiscardedEvent,
    FormulaDraftSavedEvent,
    FormulaPublishedEvent,
    FormulaRolledBackEvent,
)
from src.modules.pricing.domain.exceptions import (
    FormulaValidationError,
    FormulaVersionImmutableError,
    FormulaVersionInvalidStateError,
)
from src.modules.pricing.domain.value_objects import FormulaStatus

ACTOR = uuid.uuid4()
CONTEXT_ID = uuid.uuid4()


def _minimal_ast() -> dict[str, Any]:
    """Minimal v2 AST — one binding, full required metadata."""
    return {
        "version": 1,
        "final_component_code": "final_price",
        "bindings": [
            {
                "code": "final_price",
                "label_i18n": {"ru": "Итоговая цена"},
                "is_visible": True,
                "expr": {"const": "100"},
            }
        ],
    }


def _two_binding_ast() -> dict[str, Any]:
    """Two-binding v2 AST — ``base`` referenced by ``final_price``."""
    return {
        "version": 1,
        "final_component_code": "final_price",
        "bindings": [
            {
                "code": "base",
                "label_i18n": {"ru": "Базовая цена"},
                "is_visible": True,
                "expr": {"var": "purchase_price"},
            },
            {
                "code": "final_price",
                "label_i18n": {"ru": "Итоговая цена"},
                "is_visible": True,
                "expr": {
                    "op": "*",
                    "args": [{"ref": "base"}, {"const": "1.15"}],
                },
            },
        ],
    }


# ---------------------------------------------------------------------------
# AST validator
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidateAst:
    def test_happy_path(self) -> None:
        _validate_ast(_minimal_ast())
        _validate_ast(_two_binding_ast())

    def test_rejects_non_dict(self) -> None:
        with pytest.raises(FormulaValidationError):
            _validate_ast("not a dict")  # ty: ignore[invalid-argument-type]

    def test_rejects_missing_version(self) -> None:
        ast = _minimal_ast()
        del ast["version"]
        with pytest.raises(FormulaValidationError):
            _validate_ast(ast)

    def test_rejects_missing_bindings(self) -> None:
        ast = _minimal_ast()
        del ast["bindings"]
        with pytest.raises(FormulaValidationError):
            _validate_ast(ast)

    def test_rejects_empty_bindings(self) -> None:
        ast = _minimal_ast()
        ast["bindings"] = []
        with pytest.raises(FormulaValidationError):
            _validate_ast(ast)

    def test_rejects_duplicate_binding_codes(self) -> None:
        ast = _two_binding_ast()
        ast["bindings"][1]["code"] = "base"
        with pytest.raises(FormulaValidationError):
            _validate_ast(ast)

    def test_rejects_forward_ref(self) -> None:
        ast = _two_binding_ast()
        # Swap: make first binding reference "final_price" (a later binding).
        ast["bindings"][0]["expr"] = {"ref": "final_price"}
        with pytest.raises(FormulaValidationError):
            _validate_ast(ast)

    def test_rejects_self_ref(self) -> None:
        ast = _minimal_ast()
        # Self-reference: the only binding's code IS ``final_price`` —
        # validator forbids self-ref because the binding's code only
        # enters ``known_refs`` after its expr is checked.
        ast["bindings"][0]["expr"] = {"ref": "final_price"}
        with pytest.raises(FormulaValidationError):
            _validate_ast(ast)

    def test_final_component_code_must_match_a_binding(self) -> None:
        """v2 — ``final_component_code`` must resolve to an existing binding."""
        ast = _two_binding_ast()
        # Rename the would-be final binding without updating the
        # top-level pointer.
        ast["bindings"][1]["code"] = "something_else"
        with pytest.raises(FormulaValidationError):
            _validate_ast(ast)

    def test_missing_final_component_code_is_rejected(self) -> None:
        ast = _minimal_ast()
        del ast["final_component_code"]
        with pytest.raises(FormulaValidationError):
            _validate_ast(ast)

    def test_rejects_unknown_operator(self) -> None:
        ast = _two_binding_ast()
        ast["bindings"][1]["expr"]["op"] = "%"
        with pytest.raises(FormulaValidationError):
            _validate_ast(ast)

    def test_rejects_unknown_function(self) -> None:
        ast = _minimal_ast()
        ast["bindings"][0]["expr"] = {"fn": "sqrt", "args": [{"const": "4"}]}
        with pytest.raises(FormulaValidationError):
            _validate_ast(ast)

    def test_rejects_json_over_length_limit(self) -> None:
        ast = _minimal_ast()
        # Build a 10 KB string in a const — exceeds the v2 limit of 8 KB.
        ast["bindings"][0]["expr"] = {"const": "1" + "0" * 10_000}
        with pytest.raises(FormulaValidationError):
            _validate_ast(ast)

    def test_known_functions_accept_args(self) -> None:
        ast = _minimal_ast()
        ast["bindings"][0]["expr"] = {
            "fn": "max",
            "args": [{"const": "1"}, {"const": "2"}],
        }
        _validate_ast(ast)

    def test_deep_nested_ok_below_limit(self) -> None:
        # Build a chain of 'op' +, 32 deep — well below 64.
        expr: dict[str, Any] = {"const": "1"}
        for _ in range(30):
            expr = {"op": "+", "args": [expr, {"const": "1"}]}
        ast = {
            "version": 1,
            "final_component_code": "final_price",
            "bindings": [
                {
                    "code": "final_price",
                    "label_i18n": {"ru": "Итоговая цена"},
                    "is_visible": True,
                    "expr": expr,
                }
            ],
        }
        _validate_ast(ast)


# ---------------------------------------------------------------------------
# Factory and mutators
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCreateDraft:
    def test_happy_path_emits_draft_saved_event(self) -> None:
        draft = FormulaVersion.create_draft(
            context_id=CONTEXT_ID,
            version_number=1,
            ast=_minimal_ast(),
            actor_id=ACTOR,
        )
        assert draft.status is FormulaStatus.DRAFT
        assert draft.version_number == 1
        assert draft.published_at is None
        assert draft.version_lock == 0
        events = list(draft.domain_events)
        draft.clear_domain_events()
        assert len(events) == 1
        assert isinstance(events[0], FormulaDraftSavedEvent)

    def test_rejects_zero_version_number(self) -> None:
        with pytest.raises(FormulaValidationError):
            FormulaVersion.create_draft(
                context_id=CONTEXT_ID,
                version_number=0,
                ast=_minimal_ast(),
                actor_id=ACTOR,
            )

    def test_validates_ast_at_creation(self) -> None:
        bad = {"version": 1, "bindings": []}
        with pytest.raises(FormulaValidationError):
            FormulaVersion.create_draft(
                context_id=CONTEXT_ID,
                version_number=1,
                ast=bad,
                actor_id=ACTOR,
            )


def _fresh_draft() -> FormulaVersion:
    draft = FormulaVersion.create_draft(
        context_id=CONTEXT_ID,
        version_number=1,
        ast=_minimal_ast(),
        actor_id=ACTOR,
    )
    list(draft.domain_events)
    draft.clear_domain_events()  # clear creation event
    return draft


@pytest.mark.unit
class TestUpdateAst:
    def test_happy_path_bumps_version_lock(self) -> None:
        draft = _fresh_draft()
        starting_lock = draft.version_lock
        draft.update_ast(new_ast=_two_binding_ast(), actor_id=ACTOR)
        assert draft.version_lock == starting_lock + 1
        events = list(draft.domain_events)
        draft.clear_domain_events()
        assert any(isinstance(e, FormulaDraftSavedEvent) for e in events)

    def test_rejects_on_published(self) -> None:
        draft = _fresh_draft()
        draft.publish(actor_id=ACTOR)
        with pytest.raises(FormulaVersionImmutableError):
            draft.update_ast(new_ast=_two_binding_ast(), actor_id=ACTOR)

    def test_validates_new_ast(self) -> None:
        draft = _fresh_draft()
        with pytest.raises(FormulaValidationError):
            draft.update_ast(new_ast={"version": 1, "bindings": []}, actor_id=ACTOR)


@pytest.mark.unit
class TestPublish:
    def test_draft_to_published_emits_event(self) -> None:
        draft = _fresh_draft()
        prev = uuid.uuid4()
        draft.publish(actor_id=ACTOR, previous_version_id=prev)
        assert draft.status is FormulaStatus.PUBLISHED
        assert draft.published_at is not None
        assert draft.published_by == ACTOR
        events = list(draft.domain_events)
        draft.clear_domain_events()
        pub = [e for e in events if isinstance(e, FormulaPublishedEvent)]
        assert len(pub) == 1
        assert pub[0].previous_version_id == prev

    def test_rejects_on_non_draft(self) -> None:
        draft = _fresh_draft()
        draft.publish(actor_id=ACTOR)
        with pytest.raises(FormulaVersionInvalidStateError):
            draft.publish(actor_id=ACTOR)


@pytest.mark.unit
class TestArchive:
    def test_published_to_archived_bumps_lock(self) -> None:
        draft = _fresh_draft()
        draft.publish(actor_id=ACTOR)
        list(draft.domain_events)
        draft.clear_domain_events()
        lock = draft.version_lock
        draft.archive(actor_id=ACTOR)
        assert draft.status is FormulaStatus.ARCHIVED
        assert draft.version_lock == lock + 1

    def test_rejects_on_draft(self) -> None:
        draft = _fresh_draft()
        with pytest.raises(FormulaVersionInvalidStateError):
            draft.archive(actor_id=ACTOR)


@pytest.mark.unit
class TestRestoreAsPublished:
    def test_archived_to_published_emits_rollback(self) -> None:
        draft = _fresh_draft()
        draft.publish(actor_id=ACTOR)
        draft.archive(actor_id=ACTOR)
        list(draft.domain_events)
        draft.clear_domain_events()
        other = uuid.uuid4()
        draft.restore_as_published(actor_id=ACTOR, rolled_back_from_version_id=other)
        assert draft.status is FormulaStatus.PUBLISHED
        events = list(draft.domain_events)
        draft.clear_domain_events()
        rb = [e for e in events if isinstance(e, FormulaRolledBackEvent)]
        assert len(rb) == 1
        assert rb[0].rolled_back_from_version_id == other

    def test_rejects_on_published(self) -> None:
        draft = _fresh_draft()
        draft.publish(actor_id=ACTOR)
        with pytest.raises(FormulaVersionInvalidStateError):
            draft.restore_as_published(actor_id=ACTOR, rolled_back_from_version_id=None)


@pytest.mark.unit
class TestDiscard:
    def test_draft_emits_discard_event(self) -> None:
        draft = _fresh_draft()
        draft.discard(actor_id=ACTOR)
        events = list(draft.domain_events)
        draft.clear_domain_events()
        assert any(isinstance(e, FormulaDraftDiscardedEvent) for e in events)

    def test_rejects_on_published(self) -> None:
        draft = _fresh_draft()
        draft.publish(actor_id=ACTOR)
        with pytest.raises(FormulaVersionInvalidStateError):
            draft.discard(actor_id=ACTOR)
