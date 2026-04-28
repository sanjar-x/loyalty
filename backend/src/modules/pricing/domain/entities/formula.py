"""``FormulaVersion`` aggregate — a single version of a pricing formula.

A ``FormulaVersion`` belongs to a ``PricingContext`` and carries the AST
(Abstract Syntax Tree) that computes ``final_price`` from input variables.

State machine (FRD §FormulaVersion FSM):

- ``draft``      — mutable, at most one per context
- ``published``  — active, AST is immutable; at most one per context
- ``archived``   — history, can be restored via rollback

Transitions are driven by application-level commands that coordinate two or
more versions atomically (e.g. publishing a draft both archives the current
published version and updates ``PricingContext.active_formula_version_id``).
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any, cast

import attrs

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
from src.shared.interfaces.entities import AggregateRoot

_AST_MAX_DEPTH = 64
_AST_MAX_JSON_LEN = 4096
_OPERATOR_OPS = frozenset({"+", "-", "*", "/"})
_FUNCTIONS = frozenset({"min", "max", "round", "ceil", "floor", "abs", "if"})


# ---------------------------------------------------------------------------
# AST validator — shape-only (no unit algebra, no type inference).
# ---------------------------------------------------------------------------


def _validate_ast(ast: dict[str, Any]) -> None:
    """Validate the lightweight shape of a formula AST.

    Enforced:
    - top-level dict with integer ``version`` and non-empty ``bindings`` list
    - each binding is a dict with string ``name``, string ``component_tag``,
      and dict ``expr``
    - binding names are unique
    - ``ref`` nodes point to an earlier binding (prevents cycles)
    - the last binding has ``name == "final_price"`` and
      ``component_tag == "final_price"``
    - expression depth ≤ 64
    - serialized JSON length ≤ 4096 chars
    """
    if not isinstance(ast, dict):
        raise FormulaValidationError(
            message="AST must be a JSON object.",
            error_code="PRICING_FORMULA_AST_INVALID",
        )

    version = ast.get("version")
    if not isinstance(version, int) or version < 1:
        raise FormulaValidationError(
            message="AST must include positive integer 'version'.",
            error_code="PRICING_FORMULA_AST_VERSION_INVALID",
            details={"version": version},
        )

    bindings = ast.get("bindings")
    if not isinstance(bindings, list) or not bindings:
        raise FormulaValidationError(
            message="AST must include a non-empty 'bindings' list.",
            error_code="PRICING_FORMULA_AST_BINDINGS_EMPTY",
        )

    # Check total size first — cheap guard against malicious payloads.
    try:
        serialized = json.dumps(ast, separators=(",", ":"), sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise FormulaValidationError(
            message=f"AST is not JSON-serializable: {exc}.",
            error_code="PRICING_FORMULA_AST_INVALID",
        ) from exc
    if len(serialized) > _AST_MAX_JSON_LEN:
        raise FormulaValidationError(
            message=(
                f"AST serialized length {len(serialized)} exceeds "
                f"{_AST_MAX_JSON_LEN} chars."
            ),
            error_code="PRICING_FORMULA_EXPRESSION_TOO_LONG",
            details={"length": len(serialized), "max": _AST_MAX_JSON_LEN},
        )

    seen_names: set[str] = set()
    for idx, raw_binding in enumerate(bindings):
        if not isinstance(raw_binding, dict):
            raise FormulaValidationError(
                message=f"Binding at index {idx} must be an object.",
                error_code="PRICING_FORMULA_AST_INVALID",
            )
        binding = cast("dict[str, Any]", raw_binding)
        name = binding.get("name")
        tag = binding.get("component_tag")
        expr = binding.get("expr")
        if not isinstance(name, str) or not name:
            raise FormulaValidationError(
                message=f"Binding at index {idx} is missing string 'name'.",
                error_code="PRICING_FORMULA_AST_BINDING_NAME_INVALID",
                details={"index": idx},
            )
        if name in seen_names:
            raise FormulaValidationError(
                message=f"Duplicate binding name {name!r}.",
                error_code="PRICING_FORMULA_AST_BINDING_NAME_DUPLICATE",
                details={"name": name},
            )
        if not isinstance(tag, str) or not tag:
            raise FormulaValidationError(
                message=(f"Binding {name!r} is missing required 'component_tag'."),
                error_code="PRICING_FORMULA_COMPONENT_TAG_MISSING",
                details={"binding": name},
            )
        if not isinstance(expr, dict):
            raise FormulaValidationError(
                message=f"Binding {name!r} 'expr' must be an object.",
                error_code="PRICING_FORMULA_AST_EXPR_INVALID",
                details={"binding": name},
            )

        depth = _check_expr(expr, known_refs=seen_names, binding_name=name)
        if depth > _AST_MAX_DEPTH:
            raise FormulaValidationError(
                message=(
                    f"Binding {name!r} expression depth {depth} exceeds "
                    f"{_AST_MAX_DEPTH}."
                ),
                error_code="PRICING_FORMULA_AST_DEPTH_EXCEEDED",
                details={"binding": name, "depth": depth},
            )

        seen_names.add(name)

    last = bindings[-1]
    if last.get("name") != "final_price" or last.get("component_tag") != "final_price":
        raise FormulaValidationError(
            message=(
                "Last binding must have name='final_price' and "
                "component_tag='final_price'."
            ),
            error_code="PRICING_FORMULA_COMPONENT_TAG_MISSING",
            details={"missing": "final_price"},
        )


def _check_expr(
    expr: Any,
    *,
    known_refs: set[str],
    binding_name: str,
    depth: int = 1,
) -> int:
    """Recursively validate an expression and return its depth."""
    if not isinstance(expr, dict):
        raise FormulaValidationError(
            message=f"Expression in {binding_name!r} must be a JSON object.",
            error_code="PRICING_FORMULA_AST_EXPR_INVALID",
            details={"binding": binding_name},
        )

    if "var" in expr:
        code = expr["var"]
        if not isinstance(code, str) or not code:
            raise FormulaValidationError(
                message=f"{binding_name}: 'var' must be a non-empty string.",
                error_code="PRICING_FORMULA_AST_VAR_INVALID",
                details={"binding": binding_name},
            )
        return depth

    if "ref" in expr:
        name = expr["ref"]
        if not isinstance(name, str) or not name:
            raise FormulaValidationError(
                message=f"{binding_name}: 'ref' must be a non-empty string.",
                error_code="PRICING_FORMULA_AST_REF_INVALID",
                details={"binding": binding_name},
            )
        if name not in known_refs:
            raise FormulaValidationError(
                message=(
                    f"{binding_name}: ref {name!r} must refer to an "
                    "earlier binding (forward or self references are forbidden)."
                ),
                error_code="PRICING_FORMULA_AST_REF_UNRESOLVED",
                details={"binding": binding_name, "ref": name},
            )
        return depth

    if "const" in expr:
        value = expr["const"]
        if not isinstance(value, str):
            raise FormulaValidationError(
                message=f"{binding_name}: 'const' must be a string (decimal).",
                error_code="PRICING_FORMULA_AST_CONST_INVALID",
                details={"binding": binding_name},
            )
        return depth

    op = expr.get("op")
    if op is not None:
        if op not in _OPERATOR_OPS:
            raise FormulaValidationError(
                message=f"{binding_name}: unsupported operator {op!r}.",
                error_code="PRICING_FORMULA_AST_OP_INVALID",
                details={"binding": binding_name, "op": op},
            )
        args = expr.get("args")
        if not isinstance(args, list) or len(args) < 2:
            raise FormulaValidationError(
                message=(f"{binding_name}: operator {op!r} requires at least 2 args."),
                error_code="PRICING_FORMULA_AST_ARGS_INVALID",
                details={"binding": binding_name, "op": op},
            )
        child_depths = [
            _check_expr(
                arg, known_refs=known_refs, binding_name=binding_name, depth=depth + 1
            )
            for arg in args
        ]
        return max(child_depths)

    fn = expr.get("fn")
    if fn is not None:
        if fn not in _FUNCTIONS:
            raise FormulaValidationError(
                message=f"{binding_name}: unsupported function {fn!r}.",
                error_code="PRICING_FORMULA_AST_FN_INVALID",
                details={"binding": binding_name, "fn": fn},
            )
        args = expr.get("args")
        if not isinstance(args, list) or not args:
            raise FormulaValidationError(
                message=f"{binding_name}: function {fn!r} requires args.",
                error_code="PRICING_FORMULA_AST_ARGS_INVALID",
                details={"binding": binding_name, "fn": fn},
            )
        child_depths = [
            _check_expr(
                arg, known_refs=known_refs, binding_name=binding_name, depth=depth + 1
            )
            for arg in args
        ]
        return max(child_depths)

    raise FormulaValidationError(
        message=(
            f"{binding_name}: expression must have one of 'var', 'ref', "
            "'const', 'op', 'fn'."
        ),
        error_code="PRICING_FORMULA_AST_EXPR_UNKNOWN",
        details={"binding": binding_name, "keys": sorted(expr.keys())},
    )


# ---------------------------------------------------------------------------
# Aggregate
# ---------------------------------------------------------------------------


@attrs.define(kw_only=True)
class FormulaVersion(AggregateRoot):
    """A single version of a pricing formula bound to a ``PricingContext``."""

    id: uuid.UUID
    context_id: uuid.UUID
    version_number: int
    status: FormulaStatus
    ast: dict[str, Any] = attrs.field(factory=dict)
    published_at: datetime | None = None
    published_by: uuid.UUID | None = None
    version_lock: int = 0
    created_at: datetime = attrs.field(factory=lambda: datetime.now(UTC))
    updated_at: datetime = attrs.field(factory=lambda: datetime.now(UTC))
    updated_by: uuid.UUID | None = None

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create_draft(
        cls,
        *,
        context_id: uuid.UUID,
        version_number: int,
        ast: dict[str, Any],
        actor_id: uuid.UUID,
    ) -> FormulaVersion:
        if version_number < 1:
            raise FormulaValidationError(
                message="version_number must be >= 1.",
                error_code="PRICING_FORMULA_VERSION_NUMBER_INVALID",
                details={"version_number": version_number},
            )
        _validate_ast(ast)
        now = datetime.now(UTC)
        draft = cls(
            id=uuid.uuid4(),
            context_id=context_id,
            version_number=version_number,
            status=FormulaStatus.DRAFT,
            ast=dict(ast),
            published_at=None,
            published_by=None,
            version_lock=0,
            created_at=now,
            updated_at=now,
            updated_by=actor_id,
        )
        draft.add_domain_event(
            FormulaDraftSavedEvent(
                version_id=draft.id,
                context_id=draft.context_id,
                version_number=draft.version_number,
                updated_by=actor_id,
            )
        )
        return draft

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def update_ast(
        self,
        *,
        new_ast: dict[str, Any],
        actor_id: uuid.UUID,
    ) -> None:
        if self.status is not FormulaStatus.DRAFT:
            raise FormulaVersionImmutableError(
                version_id=self.id, status=self.status.value
            )
        _validate_ast(new_ast)
        self.ast = dict(new_ast)
        self._touch(actor_id)
        self.add_domain_event(
            FormulaDraftSavedEvent(
                version_id=self.id,
                context_id=self.context_id,
                version_number=self.version_number,
                updated_by=actor_id,
            )
        )

    def publish(
        self,
        *,
        actor_id: uuid.UUID,
        previous_version_id: uuid.UUID | None = None,
    ) -> None:
        """Draft → Published. Caller must also archive any current published."""
        if self.status is not FormulaStatus.DRAFT:
            raise FormulaVersionInvalidStateError(
                message=(
                    f"Only draft versions can be published (current status: "
                    f"{self.status.value})."
                ),
                details={"version_id": str(self.id), "status": self.status.value},
            )
        now = datetime.now(UTC)
        self.status = FormulaStatus.PUBLISHED
        self.published_at = now
        self.published_by = actor_id
        self._touch(actor_id)
        self.add_domain_event(
            FormulaPublishedEvent(
                version_id=self.id,
                context_id=self.context_id,
                version_number=self.version_number,
                previous_version_id=previous_version_id,
                published_by=actor_id,
            )
        )

    def archive(self, *, actor_id: uuid.UUID) -> None:
        """Published → Archived (called on the old published during publish/rollback)."""
        if self.status is not FormulaStatus.PUBLISHED:
            raise FormulaVersionInvalidStateError(
                message=(
                    "Only published versions can be archived "
                    f"(current status: {self.status.value})."
                ),
                details={"version_id": str(self.id), "status": self.status.value},
            )
        self.status = FormulaStatus.ARCHIVED
        self._touch(actor_id)

    def restore_as_published(
        self,
        *,
        actor_id: uuid.UUID,
        rolled_back_from_version_id: uuid.UUID | None,
    ) -> None:
        """Archived → Published (rollback)."""
        if self.status is not FormulaStatus.ARCHIVED:
            raise FormulaVersionInvalidStateError(
                message=(
                    "Only archived versions can be restored via rollback "
                    f"(current status: {self.status.value})."
                ),
                details={"version_id": str(self.id), "status": self.status.value},
            )
        now = datetime.now(UTC)
        self.status = FormulaStatus.PUBLISHED
        self.published_at = now
        self.published_by = actor_id
        self._touch(actor_id)
        self.add_domain_event(
            FormulaRolledBackEvent(
                version_id=self.id,
                context_id=self.context_id,
                version_number=self.version_number,
                rolled_back_from_version_id=rolled_back_from_version_id,
                updated_by=actor_id,
            )
        )

    def discard(self, *, actor_id: uuid.UUID) -> None:
        """Emit a discard event; the caller is responsible for repo-level delete."""
        if self.status is not FormulaStatus.DRAFT:
            raise FormulaVersionInvalidStateError(
                message=(
                    "Only draft versions can be discarded "
                    f"(current status: {self.status.value})."
                ),
                details={"version_id": str(self.id), "status": self.status.value},
            )
        self.add_domain_event(
            FormulaDraftDiscardedEvent(
                version_id=self.id,
                context_id=self.context_id,
                version_number=self.version_number,
                updated_by=actor_id,
            )
        )

    def _touch(self, actor_id: uuid.UUID) -> None:
        self.updated_at = datetime.now(UTC)
        self.updated_by = actor_id
        self.version_lock += 1
