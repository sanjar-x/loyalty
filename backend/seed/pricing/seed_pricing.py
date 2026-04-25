"""Seed system pricing variables (ADR-005).

DB-only step. Idempotent on the unique ``code`` index of
``pricing_variables`` — re-running updates only the mutable fields
(``name``, ``description``, ``is_required``, ``default_value``,
``max_age_days``). Immutable fields (``code``, ``scope``, ``data_type``,
``unit``, ``is_fx_rate``) are *not* touched on conflict, matching the
domain invariants enforced by ``Variable``.

Reads ``seed/pricing/system_variables.json`` so adding a new system
variable is a one-line edit instead of a code change.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.modules.pricing.infrastructure.models import VariableModel

if TYPE_CHECKING:
    from seed.main import SeedContext


_SPEC_PATH = Path(__file__).parent / "system_variables.json"


def _load_spec() -> list[dict]:
    return json.loads(_SPEC_PATH.read_text(encoding="utf-8"))["variables"]


async def _upsert_variables(factory: async_sessionmaker[AsyncSession]) -> int:
    spec = _load_spec()
    inserted_or_updated = 0
    async with factory() as session:
        for entry in spec:
            await _upsert_one(session, entry)
            inserted_or_updated += 1
        await session.commit()
    return inserted_or_updated


async def _upsert_one(session: AsyncSession, entry: dict) -> None:
    """Idempotent upsert keyed on ``code``.

    Generates a deterministic UUID via ``uuid5`` so re-running the
    seeder against a fresh database produces the same UUID (handy for
    fixtures and test snapshots). The unique index on ``code`` makes
    the ``ON CONFLICT`` clause safe under concurrent runs.

    Pre-flight check: if a variable with the same ``code`` already
    exists with a different ``scope`` / ``data_type`` / ``unit`` /
    ``is_fx_rate`` (all immutable per the domain), the
    ``ON CONFLICT DO UPDATE`` clause silently keeps the old immutable
    fields and the recompute pipeline misroutes — the seed would
    succeed but production would mis-resolve variables. Fail loudly
    with a precise remediation message instead.
    """
    code: str = entry["code"]
    existing = await session.execute(
        select(
            VariableModel.scope,
            VariableModel.data_type,
            VariableModel.unit,
            VariableModel.is_fx_rate,
        ).where(VariableModel.code == code)
    )
    row = existing.one_or_none()
    if row is not None:
        mismatches: list[str] = []
        if row.scope != entry["scope"]:
            mismatches.append(f"scope: {row.scope!r} != {entry['scope']!r}")
        if row.data_type != entry["data_type"]:
            mismatches.append(f"data_type: {row.data_type!r} != {entry['data_type']!r}")
        if row.unit != entry["unit"]:
            mismatches.append(f"unit: {row.unit!r} != {entry['unit']!r}")
        expected_fx = bool(entry.get("is_fx_rate", False))
        if bool(row.is_fx_rate) != expected_fx:
            mismatches.append(
                f"is_fx_rate: {bool(row.is_fx_rate)!r} != {expected_fx!r}"
            )
        if mismatches:
            raise RuntimeError(
                f"Pricing variable {code!r} already exists with conflicting "
                f"immutable fields ({'; '.join(mismatches)}). These fields "
                "cannot change after creation. Resolve manually: either "
                f"DELETE FROM pricing_variables WHERE code = '{code}' "
                "(only safe if no formulas/profiles reference it), or pick "
                "a different code in seed/pricing/system_variables.json."
            )

    default_value = entry.get("default_value")
    payload = {
        "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"loyality.pricing.variable.{code}"),
        "code": code,
        "scope": entry["scope"],
        "data_type": entry["data_type"],
        "unit": entry["unit"],
        "name": entry["name"],
        "description": entry.get("description") or {},
        "is_required": bool(entry.get("is_required", False)),
        "default_value": Decimal(str(default_value))
        if default_value is not None
        else None,
        "is_system": bool(entry.get("is_system", True)),
        "is_fx_rate": bool(entry.get("is_fx_rate", False)),
        "max_age_days": entry.get("max_age_days"),
    }

    stmt = insert(VariableModel).values(**payload)
    # Mutable fields only — preserves the immutable-after-create
    # invariants on ``code``, ``scope``, ``data_type``, ``unit``,
    # ``is_fx_rate``. ``id`` stays put on conflict.
    stmt = stmt.on_conflict_do_update(
        index_elements=["code"],
        set_={
            "name": stmt.excluded.name,
            "description": stmt.excluded.description,
            "is_required": stmt.excluded.is_required,
            "default_value": stmt.excluded.default_value,
            "is_system": stmt.excluded.is_system,
            "max_age_days": stmt.excluded.max_age_days,
        },
    )
    await session.execute(stmt)


async def _run(db_url: str) -> int:
    engine = create_async_engine(db_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        count = await _upsert_variables(factory)
        return count
    finally:
        await engine.dispose()


def seed_pricing(ctx: SeedContext) -> None:
    """Upsert ADR-005 system pricing variables."""
    from src.bootstrap.config import Settings

    del ctx  # DB-only step; SeedContext unused
    settings = Settings()  # type: ignore[call-arg]
    count = asyncio.run(_run(settings.database_url))
    print(f"  Upserted {count} system pricing variable(s).")
