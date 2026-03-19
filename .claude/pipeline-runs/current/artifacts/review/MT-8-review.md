# Code Review -- MT-8: Add UpdateProduct command handler

> **Reviewer:** senior-reviewer (9/10)
> **Plan:** arch/MT-8-plan.md
> **Verdict:** APPROVED

---

## Summary

The implementation is clean, well-structured, and follows the architect's plan precisely. The sentinel pattern, optimistic locking, slug uniqueness check, CQRS compliance, and UoW pattern are all correctly implemented. No Critical or Major issues found. All quality gates pass.

## Plan compliance

The implementation matches the architect's revised plan exactly:

- File created at `src/modules/catalog/application/commands/update_product.py` -- correct path.
- `_SENTINEL` is a module-level `object()` local to the command module -- matches plan's final decision.
- `UpdateProductCommand` is a `@dataclass(frozen=True)` with all planned fields and correct types/defaults.
- `UpdateProductResult` is a `@dataclass(frozen=True)` with `id: uuid.UUID` only -- CQRS minimal return.
- `UpdateProductHandler` constructor takes `product_repo: IProductRepository` and `uow: IUnitOfWork` -- matches plan.
- Handler logic follows the revised pseudo-code: fetch -> version check -> slug check -> build kwargs conditionally -> `product.update(**update_kwargs)` -> `repo.update` -> `uow.commit`.
- Imports match the plan's updated import list exactly (includes `Any` from typing).
- No DI registration changes (deferred to MT-23) -- correct per plan.
- No domain events emitted -- correct per plan (P2 deferral).

No deviations from the architect's plan.

## Findings

### Critical

None.

### Major

None.

### Minor

None.

### Suggestions

- The `dict[str, Any]` type for `update_kwargs` uses `Any` which is justified here since the kwargs are forwarded to `Product.update()` which accepts heterogeneous types. No action needed.

## Acceptance criteria verification

From PM spec (MT-8) and architect's plan:

- [x] UpdateProductCommand with product_id and all updatable fields as optional, plus optional version field -- MET
- [x] Handler fetches product via repo.get, raises ProductNotFoundError if missing -- MET (lines 110-112)
- [x] If version is provided and does not match product.version, raises ConcurrencyError -- MET (lines 118-124)
- [x] Handler calls product.update() with only the fields that were explicitly provided -- MET (kwargs built conditionally, lines 141-160)
- [x] Handler validates slug uniqueness if slug is being changed (and differs from current) -- MET (lines 127-134)
- [x] UoW commit pattern used (async with self._uow -> repo.update -> uow.commit) -- MET (lines 109, 162-163)
- [x] Domain layer has zero framework imports -- MET (handler imports only domain + shared + stdlib)
- [x] No cross-module imports -- MET
- [x] All writes go through UoW -- MET
- [x] File is at `src/modules/catalog/application/commands/update_product.py` -- MET

## Post-fix checks

| Check | Result |
|-------|--------|
| ruff | PASS |
| mypy | PASS |
| pytest unit+arch | PASS (869 passed) |

## Verdict

**APPROVED** -- implementation matches architect's plan exactly, all acceptance criteria met, all quality gates pass. Ready for QA.
