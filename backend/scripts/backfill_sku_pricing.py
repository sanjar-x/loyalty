"""One-shot backfill of ``SKU.purchase_price`` for legacy rows (ADR-005).

Runs after the ADR-005 migrations in production. For every SKU that
still has the migration's default ``pricing_status='legacy'``:

1. If ``sku.price`` is already set, copy ``sku.price`` →
   ``sku.purchase_price`` and the SKU's ``currency`` →
   ``purchase_currency`` (RUB or CNY only — anything else is left
   alone for manual review).
2. Flip ``pricing_status`` to ``pending`` so the recompute pipeline
   takes ownership at the next outbox poll.

Usage::

    uv run python -m scripts.backfill_sku_pricing            # dry run
    uv run python -m scripts.backfill_sku_pricing --apply    # commit
    uv run python -m scripts.backfill_sku_pricing --apply --batch-size 500

The script does **not** enqueue recompute jobs directly; it relies on
``set_purchase_price`` semantics (PENDING status hides the SKU from
storefront listings) plus the autonomous pipeline kicked from a manual
``POST /api/v1/pricing/recompute/contexts/{id}`` once admins are ready.
This keeps the backfill non-disruptive — admins gate the rebuild.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.modules.catalog.infrastructure.models import SKU

_ALLOWED_CURRENCIES = ("RUB", "CNY")


async def _backfill(
    factory: async_sessionmaker[AsyncSession],
    *,
    apply: bool,
    batch_size: int,
) -> dict[str, int]:
    counters = {"scanned": 0, "candidates": 0, "applied": 0, "skipped": 0}
    last_id: uuid.UUID | None = None

    while True:
        async with factory() as session:
            stmt = (
                select(
                    SKU.id,
                    SKU.price,
                    SKU.currency,
                    SKU.pricing_status,
                    SKU.deleted_at,
                )
                .where(
                    SKU.deleted_at.is_(None),
                    SKU.pricing_status == "legacy",
                    SKU.purchase_price.is_(None),
                )
                .order_by(SKU.id.asc())
                .limit(batch_size)
            )
            if last_id is not None:
                stmt = stmt.where(SKU.id > last_id)

            rows = list((await session.execute(stmt)).all())
            if not rows:
                break

            for row in rows:
                counters["scanned"] += 1
                if row.price is None or row.currency not in _ALLOWED_CURRENCIES:
                    counters["skipped"] += 1
                    last_id = row.id
                    continue

                counters["candidates"] += 1
                if not apply:
                    last_id = row.id
                    continue

                upd = (
                    update(SKU)
                    .where(
                        SKU.id == row.id,
                        SKU.pricing_status == "legacy",
                        SKU.purchase_price.is_(None),
                    )
                    .values(
                        purchase_price=row.price,
                        purchase_currency=row.currency,
                        pricing_status="pending",
                    )
                )
                result = await session.execute(upd)
                counters["applied"] += result.rowcount or 0
                last_id = row.id

            if apply:
                await session.commit()
            if last_id is None:
                break

    return counters


async def _run(*, apply: bool, batch_size: int) -> dict[str, int]:
    from src.bootstrap.config import Settings

    settings = Settings()  # type: ignore[call-arg]
    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        return await _backfill(factory, apply=apply, batch_size=batch_size)
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit the backfill (default is dry-run with no writes).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="Rows per batch (default: 200).",
    )
    args = parser.parse_args()

    counters = asyncio.run(
        _run(apply=args.apply, batch_size=args.batch_size)
    )
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[{mode}] {counters}")
    if not args.apply and counters["candidates"] > 0:
        print("Re-run with --apply to commit.")


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
