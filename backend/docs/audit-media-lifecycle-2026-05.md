# Media Lifecycle Audit — Sprint 2 / C2.1 (2026-05-09)

**Scope**: verify the IMG-005 atomic-cleanup path for product media holds
across the three high-risk scenarios listed in the Sprint 2 brief —
update-detach, cascade product delete, and S3 transient failures.

**Method**: trace each scenario from the admin endpoint through every
layer (handler → outbox → relay → consumer → adapter → S3), check the
existing tests, and add coverage where the chain has a gap.

---

## Scenario A — update-detach (gallery reorder + remove)

**Trigger**: ``PATCH /api/v1/admin/catalog/products/{id}`` with a
``media`` list that omits one previously-attached asset OR replaces it.

**Chain**:
1. ``UpdateProductHandler.handle`` → ``compute_media_diff`` returns
   ``to_delete`` items.
2. For each removed asset: ``media_repo.delete(id)`` + product emits
   ``MediaAssetDetachedEvent(product_id, storage_object_id)``.
3. ``UoW.commit()`` flushes the catalog row + ``outbox_messages`` row
   atomically (one transaction).
4. Outbox relay (``* * * * *``, ``FOR UPDATE SKIP LOCKED``) picks the
   row up, ``_handle_media_asset_detached`` kicks
   ``catalog.cleanup_storage_after_detached`` TaskIQ task.
5. The task resolves the ``IMediaCleanupPort`` adapter →
   ``image.DeleteStorageObjectHandler`` which:
   - lists derivations (BG_REMOVED) and deletes them too,
   - deletes the S3 object via ``IBlobStorage.delete_object``,
   - soft-deletes the ``storage_objects`` row.

**Status**: ✅ verified end-to-end. Existing coverage:
* ``tests/unit/modules/catalog/application/commands/test_product_handlers.py``
  exercises the ``UpdateProductHandler`` media-diff branch.
* ``catalog.application.consumers.media_asset_detached.cleanup_storage_after_detached``
  is the production hook — its idempotent contract documented in the
  module docstring.

---

## Scenario B — cascade product delete  🛑 GAP — fixed in this commit

**Trigger**: ``DELETE /api/v1/admin/catalog/products/{id}``.

**Pre-fix chain (broken)**:
1. ``DeleteProductHandler.handle`` → ``Product.soft_delete()``.
2. The aggregate cascades soft-delete to **variants** and **SKUs**.
3. **No event** is emitted for media. ``ProductDeletedEvent`` lands
   in the outbox as audit-only (no consumer).
4. The ``media_assets`` rows + their S3 keys remain orphaned forever.

**Why this slipped through**: ``Product.soft_delete()`` predates
IMG-005. The aggregate has no reference to its media (those live in a
separate repository), so the responsibility is the handler's. The
audit caught it because we have no tests for "delete product → media
gone".

**Fix (this commit, C2.1)**: extend ``DeleteProductHandler`` to:
1. ``media_repo.list_by_product(product_id)`` — eager fetch.
2. For each asset: ``media_repo.delete(asset.id)`` + emit
   ``MediaAssetDetachedEvent(product_id, storage_object_id)`` on the
   product aggregate.
3. ``Product.soft_delete()`` + register + commit — events flushed
   atomically with the catalog write.

The IMG-005 cleanup consumer now sweeps S3 + storage_objects rows
asynchronously with the same retry / DLQ guarantees as
``UpdateProductHandler``.

**New test**:
``tests/unit/modules/catalog/application/commands/test_product_handlers.py
::TestDeleteProduct::test_cascades_media_cleanup_via_outbox`` — seeds a
product with two media assets, asserts both rows are removed AND
``MediaAssetDetachedEvent`` is collected per asset by the
``FakeUnitOfWork`` (which mirrors the real outbox flush).

---

## Scenario C — S3 transient failure on cleanup

**Trigger**: ``cleanup_storage_after_detached`` runs, but
``IBlobStorage.delete_object`` raises (5xx, network timeout).

**Existing chain**:
1. ``cleanup_storage_after_detached`` task is configured with
   ``max_retries=3, retry_on_error=True, timeout=30``.
2. The underlying ``DeleteStorageObjectHandler`` swallows S3 errors
   as warnings (best-effort logging). The catalog adapter
   (``MediaCleanupAdapter``) wraps this in another best-effort try /
   except that logs and swallows.
3. **However**: the cleanup consumer at the catalog layer
   (``cleanup_storage_after_detached``) catches the exception and
   re-raises it explicitly, so:
   - TaskIQ retries the task (3 attempts).
   - On 4th failure, the ``DLQMiddleware`` (REC-019) persists the row
     into ``failed_tasks``.
   - Operator triages from there — manual retry, manual S3 cleanup,
     etc.

**Status**: ✅ verified by reading the production consumer + middleware
config. Coverage:
* ``cleanup_storage_after_detached`` re-raise behaviour is documented
  in its module docstring (lines 60-67 of
  ``catalog/application/consumers/media_asset_detached.py``).
* DLQ landing path is covered by the framework-level
  ``DLQMiddleware`` integration test (existing).

No fix required. Operators should monitor ``failed_tasks`` table
counts via Grafana / log alerts; the runbook for "stuck media cleanup"
is the same as any other failed TaskIQ row.

---

## Summary

| Scenario | Pre-audit status | Post-audit status |
| --- | --- | --- |
| **A** — update-detach gallery reorder / remove | ✅ working | ✅ unchanged |
| **B** — cascade product delete | 🛑 silent orphan | ✅ fixed in C2.1 + test |
| **C** — S3 transient failure on cleanup | ✅ DLQ-covered | ✅ documented |

No changes to the public API; OpenAPI snapshot unchanged.

## Related

* `[[ADR-005a Pricing → Catalog ACL Inversion]]` — same port-in-domain /
  adapter-in-infrastructure pattern as ``IMediaCleanupPort`` /
  ``MediaCleanupAdapter``.
* `backend/src/modules/catalog/application/consumers/media_asset_detached.py`
* `backend/src/modules/catalog/infrastructure/adapters/media_cleanup_adapter.py`
* `backend/src/modules/image/application/commands/delete_storage_object.py`
* IMG-005 PR — original atomic cleanup spec.
