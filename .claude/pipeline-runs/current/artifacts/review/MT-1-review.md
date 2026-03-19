# Code Review -- MT-1: Add ProductStatus and Money value objects

> **Reviewer:** senior-reviewer (9/10)
> **Plan:** arch/MT-1-plan.md
> **Verdict:** APPROVED

---

## Summary

High-quality implementation that matches the architect's plan precisely. Domain purity is maintained (only stdlib + attrs imports). Both `ProductStatus` and `Money` are correctly structured with proper validation, immutability, and comparison logic. One minor lint configuration fix was applied.

## Plan compliance

The implementation matches the architect's plan exactly:
- `ProductStatus` enum has the correct 5 members with lowercase string values matching ORM.
- `Money` is a `@frozen` attrs class with `amount: int` and `currency: str`.
- Validation in `__attrs_post_init__` with exact error messages from the plan.
- `_check_currency` helper and all four comparison methods (`__lt__`, `__le__`, `__gt__`, `__ge__`) implemented as specified.
- Placement after `RequirementLevel` enum as planned.
- Import `from attrs import frozen` added as specified.
- No deviations from plan.

## Findings

### Critical
None.

### Major
None.

### Minor
- `pyproject.toml` ruff config: The `UP042` rule (prefer `StrEnum` over `str, enum.Enum`) was not in the ignore list, causing ruff failures on all 6 enums in the file (5 pre-existing + 1 new). Since the project convention uses `(str, enum.Enum)` throughout, added `UP042` to `ruff.lint.ignore`.
  **Fixed:** Added `"UP042"` to `ignore` list in `pyproject.toml`.

### Suggestions
- Comparison methods could return `NotImplemented` for non-Money types instead of crashing with `AttributeError`. However, the type annotations prevent this at static analysis time, and the architect's plan does not include this pattern. No action taken.

## Acceptance criteria verification

- [x] ProductStatus enum has values: DRAFT, ENRICHING, READY_FOR_REVIEW, PUBLISHED, ARCHIVED -- MET
- [x] Money is a frozen attrs dataclass with `amount: int` and `currency: str` -- MET
- [x] Money validates amount >= 0 and currency is exactly 3 characters -- MET
- [x] Money has comparison methods (__lt__, __le__, __gt__, __ge__) for price validation -- MET
- [x] All existing tests pass after this change -- MET (442 passed)
- [x] Linter/type-checker passes -- MET

## Architecture constraint verification

- [x] Domain layer: zero framework imports (no SQLAlchemy, FastAPI, Pydantic, Redis)
- [x] Money uses attrs @frozen decorator, not stdlib dataclass
- [x] ProductStatus values match ORM ProductStatus enum values exactly

## Post-fix checks

| Check | Result |
|-------|--------|
| ruff | PASS |
| mypy | PASS (no issues found in 1 source file) |
| pytest unit+arch | PASS (442 passed) |

## Verdict

**APPROVED** -- implementation matches plan exactly, all checks pass, ready for QA.
