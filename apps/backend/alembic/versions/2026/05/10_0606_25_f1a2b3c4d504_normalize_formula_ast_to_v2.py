"""normalize pricing_formula_versions.ast to v2 contract (T-X / Sprint 4)

v1 → v2 migration:

* Binding's ``name`` + ``component_tag`` collapse into a single ``code``
  field (machine identifier). ``component_tag`` wins when both present
  because it was the admin-facing one; ``name`` is the v1-evaluator
  fallback.
* Each binding gains ``label_i18n: {"ru": <humanised code>}`` so the
  UI can stop transliterating snake_case on the client side.
* ``is_visible`` defaults to ``true`` (v1 had no concept; assume
  every binding is shown).
* Top-level ``final_component_code`` is hoisted from the binding
  named / tagged ``final_price`` (the v1 sentinel) or, failing that,
  the last binding's code.

In-place ``UPDATE pricing_formula_versions``. No DDL — the ``ast``
column is already JSONB. Down-migration is a no-op (would lose data
without recovering: the original v1 form was lossy on labels).

Revision ID: f1a2b3c4d504
Revises: f1a2b3c4d503
Create Date: 2026-05-10 06:06:25
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op

revision: str = "f1a2b3c4d504"
down_revision: str | Sequence[str] | None = "f1a2b3c4d503"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_DEFAULT_FINAL_COMPONENT_CODE = "final_price"


def _humanize_code(code: str) -> str:
    return code.replace("_", " ").capitalize() if code else code


def _normalize_ast_to_v2(ast: dict[str, Any]) -> dict[str, Any]:
    """Inline copy of ``normalize_ast_to_v2`` to keep the migration
    self-contained — Alembic migrations should never import live
    domain code so an out-of-band refactor can't break replay of
    historical migrations.
    """
    if not isinstance(ast, dict):
        return ast
    normalised: dict[str, Any] = json.loads(json.dumps(ast))
    bindings = normalised.get("bindings")
    if not isinstance(bindings, list):
        return normalised

    for binding in bindings:
        if not isinstance(binding, dict):
            continue
        code = binding.get("code")
        if not isinstance(code, str) or not code:
            code = binding.get("component_tag") or binding.get("name")
            if isinstance(code, str) and code:
                binding["code"] = code

        label_i18n = binding.get("label_i18n")
        if not isinstance(label_i18n, dict) or not label_i18n:
            binding["label_i18n"] = {"ru": _humanize_code(code or "")}

        if "is_visible" not in binding:
            binding["is_visible"] = True

    if not isinstance(normalised.get("final_component_code"), str):
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


def upgrade() -> None:
    connection = op.get_bind()
    result = connection.execute(sa.text("SELECT id, ast FROM pricing_formula_versions"))
    rows = list(result.fetchall())

    update_stmt = sa.text(
        "UPDATE pricing_formula_versions SET ast = CAST(:ast AS jsonb) WHERE id = :id"
    )

    migrated = 0
    skipped = 0
    for row in rows:
        ast = row.ast
        # Some Postgres driver / SA combinations return JSONB already
        # decoded into a Python dict; others return a string.
        if isinstance(ast, str):
            try:
                ast = json.loads(ast)
            except ValueError, TypeError:
                skipped += 1
                continue
        if not isinstance(ast, dict):
            skipped += 1
            continue

        # Idempotent check: if already v2 (has final_component_code AND
        # every binding has code+label_i18n) — skip the rewrite to keep
        # the migration cheap on partial re-runs.
        already_v2 = isinstance(ast.get("final_component_code"), str) and all(
            isinstance(b, dict)
            and isinstance(b.get("code"), str)
            and isinstance(b.get("label_i18n"), dict)
            and b["label_i18n"]
            for b in ast.get("bindings", [])
        )
        if already_v2:
            skipped += 1
            continue

        normalised = _normalize_ast_to_v2(ast)
        connection.execute(
            update_stmt,
            {"id": row.id, "ast": json.dumps(normalised, ensure_ascii=False)},
        )
        migrated += 1

    # Side-channel: print into the alembic log so the deploy operator
    # sees the headline counts.
    print(f"[ast-v2-migration] migrated={migrated} skipped={skipped} total={len(rows)}")


def downgrade() -> None:
    # No-op. v2 is a superset of v1; dropping the new fields would
    # leave the evaluator running on v1 fallbacks (it still has the
    # backward-compat code path), but we lose the human-readable
    # labels permanently. Manual rollback only — there's no
    # automated way to recover the original "missing" state.
    pass
