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
_AST_MAX_JSON_LEN = 8192
"""Doubled vs v1 (was 4096) because v2 carries i18n labels per binding
(``label_i18n``) — a formula with 8 bindings × 60 chars of RU/EN labels
adds ~1 KB on its own.

The cap still protects against malicious payloads; it just no longer
penalises documented formulas."""
_OPERATOR_OPS = frozenset({"+", "-", "*", "/"})
_FUNCTIONS = frozenset({"min", "max", "round", "ceil", "floor", "abs", "if"})

_DEFAULT_FINAL_COMPONENT_CODE = "final_price"
"""Sentinel name retained for AST v1 backward compatibility.

v2 makes the final-component code an explicit top-level
``final_component_code`` field so the evaluator no longer hard-codes
the string. v1 ASTs (pre-migration) implicitly required the last
binding to be named ``final_price`` — the normaliser hoists that
into the new top-level field for them."""

_REQUIRED_LABEL_LOCALES: frozenset[str] = frozenset({"ru"})
"""Locales every binding's ``label_i18n`` MUST carry. Loyality is
RU-first today; ``en`` is welcomed but not enforced. Mirrors the
project-wide REQUIRED_LOCALES policy on Product / Brand / Category."""


# ---------------------------------------------------------------------------
# AST v2 normaliser — fills v2-only fields when reading a v1 payload
# ---------------------------------------------------------------------------


def _humanize_code(code: str) -> str:
    """Build a fallback display label from a snake_case binding code.

    Used when migrating v1 ASTs (no ``label_i18n``) and as a runtime
    safety net — the admin UI should never render the raw snake_case
    key.
    """
    return code.replace("_", " ").capitalize() if code else code


def normalize_ast_to_v2(ast: dict[str, Any]) -> dict[str, Any]:
    """Return a deep-copied AST upgraded in place to the v2 contract.

    v1 → v2 changes:

    * Binding's ``name`` + ``component_tag`` collapse into a single
      ``code`` field. The normaliser prefers ``component_tag`` when
      both are present (it's the admin-facing identifier); falls
      back to ``name``.
    * Each binding gains ``label_i18n: dict[str, str]`` with a
      humanised fallback for the required ``ru`` locale.
    * ``description_i18n`` left absent (optional).
    * ``is_visible`` defaults to ``True`` so v1 ASTs render the
      whole pipeline by default.
    * Top-level ``final_component_code`` is hoisted from whichever
      binding has ``component_tag == "final_price"`` (or ``name`` if
      tag absent); defaults to the sentinel
      :data:`_DEFAULT_FINAL_COMPONENT_CODE` otherwise.

    Idempotent — calling on an already-v2 AST is a no-op.
    """
    normalised: dict[str, Any] = json.loads(json.dumps(ast))

    bindings = normalised.get("bindings")
    if not isinstance(bindings, list):
        return normalised

    for binding in bindings:
        if not isinstance(binding, dict):
            continue
        # v1 → v2: derive ``code`` from ``component_tag`` first, then ``name``.
        code = binding.get("code")
        if not isinstance(code, str) or not code:
            code = binding.get("component_tag") or binding.get("name")
            if isinstance(code, str) and code:
                binding["code"] = code

        # Backfill ``label_i18n`` from a humanised code so the UI
        # never renders raw snake_case.
        label_i18n = binding.get("label_i18n")
        if not isinstance(label_i18n, dict) or not label_i18n:
            binding["label_i18n"] = {"ru": _humanize_code(code or "")}

        # Default visibility — v1 ASTs render every binding.
        if "is_visible" not in binding:
            binding["is_visible"] = True

    # Top-level final component pointer.
    if not isinstance(normalised.get("final_component_code"), str):
        # Pick the binding whose code (v2) / component_tag (v1) /
        # name (legacy) equals ``final_price``; otherwise the last
        # binding wins (last-binding-is-final was the v1 rule).
        chosen: str | None = None
        for binding in bindings:
            if not isinstance(binding, dict):
                continue
            for candidate_key in ("code", "component_tag", "name"):
                value = binding.get(candidate_key)
                if isinstance(value, str) and value == _DEFAULT_FINAL_COMPONENT_CODE:
                    chosen = value
                    break
            if chosen is not None:
                break
        if chosen is None and bindings:
            tail = bindings[-1]
            if isinstance(tail, dict):
                chosen = (
                    tail.get("code") or tail.get("component_tag") or tail.get("name")
                )
        normalised["final_component_code"] = chosen or _DEFAULT_FINAL_COMPONENT_CODE

    return normalised


def _binding_code(binding: dict[str, Any]) -> str | None:
    """Extract the canonical binding identifier under v1 OR v2.

    Used in places that read existing AST without normalising first
    (the evaluator, tests). The normaliser is the canonical place
    for write-time fix-up.
    """
    for candidate_key in ("code", "component_tag", "name"):
        value = binding.get(candidate_key)
        if isinstance(value, str) and value:
            return value
    return None


# ---------------------------------------------------------------------------
# AST validator — shape-only (no unit algebra, no type inference).
# ---------------------------------------------------------------------------


def _validate_label_i18n(binding_code: str, raw: Any) -> None:
    """Enforce v2 ``label_i18n`` contract.

    * Must be a non-empty dict[str, str].
    * Must cover every locale in :data:`_REQUIRED_LABEL_LOCALES`.
    * Empty / whitespace-only values rejected.
    """
    if not isinstance(raw, dict) or not raw:
        raise FormulaValidationError(
            message=(
                f"Binding {binding_code!r} is missing required 'label_i18n' "
                f"(non-empty mapping of locale → label)."
            ),
            error_code="PRICING_FORMULA_LABEL_I18N_MISSING",
            details={"binding": binding_code},
        )
    missing = sorted(_REQUIRED_LABEL_LOCALES - set(raw.keys()))
    if missing:
        raise FormulaValidationError(
            message=(
                f"Binding {binding_code!r} 'label_i18n' is missing required "
                f"locales: {missing}."
            ),
            error_code="PRICING_FORMULA_LABEL_I18N_INCOMPLETE",
            details={"binding": binding_code, "missing": missing},
        )
    for locale, value in raw.items():
        if not isinstance(locale, str) or not locale:
            raise FormulaValidationError(
                message=(
                    f"Binding {binding_code!r} 'label_i18n' has a non-string "
                    "locale key."
                ),
                error_code="PRICING_FORMULA_LABEL_I18N_INVALID",
                details={"binding": binding_code},
            )
        if not isinstance(value, str) or not value.strip():
            raise FormulaValidationError(
                message=(
                    f"Binding {binding_code!r} 'label_i18n[{locale!r}]' must "
                    "be a non-blank string."
                ),
                error_code="PRICING_FORMULA_LABEL_I18N_INVALID",
                details={"binding": binding_code, "locale": locale},
            )


def _validate_ast(ast: dict[str, Any]) -> None:
    """Validate the lightweight shape of a formula AST.

    Enforces the v2 contract on every binding:

    * top-level dict with integer ``version`` and non-empty ``bindings`` list,
    * top-level ``final_component_code`` (str) — explicit pointer to the
      binding that produces the final selling price,
    * each binding is a dict with string ``code``, non-empty
      ``label_i18n`` mapping (must cover ``ru``), boolean ``is_visible``,
      and dict ``expr``,
    * binding codes are unique,
    * ``ref`` nodes point to an earlier binding (prevents cycles),
    * the binding identified by ``final_component_code`` exists,
    * expression depth ≤ 64,
    * serialized JSON length ≤ 8192 chars.

    v1 ASTs (``name`` + ``component_tag``, no ``label_i18n``) are
    normalised in-place by :func:`normalize_ast_to_v2` before
    validation — repositories MUST call the normaliser on read so
    a fresh validate of a pre-migration row keeps passing.
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

    final_component_code = ast.get("final_component_code")
    if not isinstance(final_component_code, str) or not final_component_code:
        raise FormulaValidationError(
            message=(
                "AST must include a non-empty 'final_component_code' string "
                "pointing at the binding that produces the final price."
            ),
            error_code="PRICING_FORMULA_FINAL_COMPONENT_MISSING",
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

    seen_codes: set[str] = set()
    for idx, raw_binding in enumerate(bindings):
        if not isinstance(raw_binding, dict):
            raise FormulaValidationError(
                message=f"Binding at index {idx} must be an object.",
                error_code="PRICING_FORMULA_AST_INVALID",
            )
        binding = cast("dict[str, Any]", raw_binding)
        code = binding.get("code")
        expr = binding.get("expr")
        is_visible = binding.get("is_visible", True)
        if not isinstance(code, str) or not code:
            raise FormulaValidationError(
                message=(
                    f"Binding at index {idx} is missing required string 'code' "
                    "(machine identifier, snake_case)."
                ),
                error_code="PRICING_FORMULA_AST_BINDING_CODE_INVALID",
                details={"index": idx},
            )
        if code in seen_codes:
            raise FormulaValidationError(
                message=f"Duplicate binding code {code!r}.",
                error_code="PRICING_FORMULA_AST_BINDING_CODE_DUPLICATE",
                details={"code": code},
            )
        if not isinstance(is_visible, bool):
            raise FormulaValidationError(
                message=(
                    f"Binding {code!r} 'is_visible' must be a boolean if "
                    "supplied (defaults to true)."
                ),
                error_code="PRICING_FORMULA_AST_VISIBILITY_INVALID",
                details={"binding": code},
            )
        _validate_label_i18n(code, binding.get("label_i18n"))
        if not isinstance(expr, dict):
            raise FormulaValidationError(
                message=f"Binding {code!r} 'expr' must be an object.",
                error_code="PRICING_FORMULA_AST_EXPR_INVALID",
                details={"binding": code},
            )

        depth = _check_expr(expr, known_refs=seen_codes, binding_name=code)
        if depth > _AST_MAX_DEPTH:
            raise FormulaValidationError(
                message=(
                    f"Binding {code!r} expression depth {depth} exceeds "
                    f"{_AST_MAX_DEPTH}."
                ),
                error_code="PRICING_FORMULA_AST_DEPTH_EXCEEDED",
                details={"binding": code, "depth": depth},
            )

        seen_codes.add(code)

    if final_component_code not in seen_codes:
        raise FormulaValidationError(
            message=(
                f"final_component_code={final_component_code!r} does not match "
                "any binding's 'code'."
            ),
            error_code="PRICING_FORMULA_FINAL_COMPONENT_UNRESOLVED",
            details={"final_component_code": final_component_code},
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

    # TYPE-003 — guard ``status`` against direct mutation; the
    # ``publish`` / ``archive`` / ``republish`` methods bypass via
    # ``object.__setattr__``.

    def __setattr__(self, name: str, value: object) -> None:
        if name == "status" and getattr(self, "_FormulaVersion__initialized", False):
            raise AttributeError(
                "Cannot set 'status' directly on FormulaVersion. "
                "Use publish() / archive() / republish() instead."
            )
        super().__setattr__(name, value)

    def __attrs_post_init__(self) -> None:
        super().__attrs_post_init__()
        object.__setattr__(self, "_FormulaVersion__initialized", True)

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
        # T-X / AST v2 — accept v1 author payloads, normalise into v2 on
        # write (label_i18n humanised, final_component_code hoisted).
        # The author UI is migrated lazily; the canonical persisted form
        # is always v2 so reads never deal with the legacy shape.
        normalised_ast = normalize_ast_to_v2(ast)
        _validate_ast(normalised_ast)
        now = datetime.now(UTC)
        draft = cls(
            id=uuid.uuid4(),
            context_id=context_id,
            version_number=version_number,
            status=FormulaStatus.DRAFT,
            ast=normalised_ast,
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
        # T-X / AST v2 — same lazy-migration policy as ``create_draft``:
        # author may post v1, storage is always v2.
        normalised_ast = normalize_ast_to_v2(new_ast)
        _validate_ast(normalised_ast)
        self.ast = normalised_ast
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
        object.__setattr__(self, "status", FormulaStatus.PUBLISHED)
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
        object.__setattr__(self, "status", FormulaStatus.ARCHIVED)
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
        object.__setattr__(self, "status", FormulaStatus.PUBLISHED)
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
