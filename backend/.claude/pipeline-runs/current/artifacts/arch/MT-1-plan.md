# Architecture Plan -- MT-1: Add ProductStatus and Money value objects

> **Pipeline run:** 20260318-121109
> **Micro-task:** MT-1
> **Layer:** Domain
> **Module:** catalog
> **FR Reference:** FR-001, FR-002, FR-004
> **Depends on:** none

---

## Research findings

- **attrs** (current): `@frozen` decorator creates immutable dataclasses. Validators run at init time via `attrs.field(validator=...)`. Ordering comparisons (`__lt__`, `__le__`, `__gt__`, `__ge__`) are generated automatically when the class or individual fields use `order=True`. For a Money VO where comparison should be based on amount only (within same currency), use `order_key` on the `amount` field and set `order=False` on `currency`.
- **attrs**: `@frozen` is equivalent to `@define(frozen=True)` -- prevents attribute modification after init, enabling hash-by-value semantics suitable for value objects.
- **Existing codebase convention**: Domain enums in `value_objects.py` inherit from `(str, enum.Enum)`. Entities use `@dataclass` from `attr` (i.e., `from attr import dataclass`). Value objects that need immutability should use `@frozen` from `attrs`.

---

## Design decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| ProductStatus representation | `str, enum.Enum` with UPPER_CASE values matching ORM | Consistent with existing domain enums (MediaProcessingStatus, AttributeDataType). Values use lowercase strings to match ORM ProductStatus enum values for easy mapping. |
| Money immutability | `@frozen` attrs class | Value objects must be immutable per DDD. `@frozen` prevents mutation after creation. |
| Money validation approach | `__attrs_post_init__` | attrs frozen classes cannot use `on_setattr` validators. Validation in `__attrs_post_init__` is the standard pattern for frozen classes. |
| Money comparison | Custom `__lt__` and `__le__` methods with currency guard | Comparing prices across different currencies is meaningless and must raise ValueError. Using auto-generated `order=True` would compare by (amount, currency) tuple which is incorrect semantics. Manual methods give proper domain logic. |
| Money equality | Include both amount and currency via default attrs eq | Money(100, "USD") != Money(100, "RUB") -- correct domain semantics. Default attrs `eq=True` on both fields handles this. |
| ProductStatus enum values | Lowercase strings: "draft", "enriching", etc. | Mirrors the ORM `ProductStatus` enum values exactly (see `models.py` lines 55-59), enabling simple string-based mapping in repositories. |

---

## File plan

### `src/modules/catalog/domain/value_objects.py` -- MODIFY

**Purpose:** Add `ProductStatus` enum and `Money` frozen value object to the existing domain value objects module.

**Layer:** Domain

#### New types to add:

**`ProductStatus`** (new)
- Inherits from: `str, enum.Enum` (stdlib only, consistent with other domain enums)
- Members:
  - `DRAFT = "draft"`
  - `ENRICHING = "enriching"`
  - `READY_FOR_REVIEW = "ready_for_review"`
  - `PUBLISHED = "published"`
  - `ARCHIVED = "archived"`
- Docstring: Document the lifecycle FSM states. Reference allowed transitions (detailed FSM logic lives in Product entity, MT-2).
- Placement: After the existing `RequirementLevel` enum, before any helper functions at end of file (or logically grouped with other enums).

**`Money`** (new)
- Decorator: `@frozen` from `attrs`
- Fields:
  - `amount: int` -- price in smallest currency units (e.g., kopecks). Must be >= 0.
  - `currency: str` -- ISO 4217 3-character code (e.g., "RUB", "USD"). Must be exactly 3 characters.
- Validation (in `__attrs_post_init__`):
  - `amount < 0` raises `ValueError("Money amount must be non-negative")`
  - `len(currency) != 3` raises `ValueError("Currency must be a 3-character ISO code")`
- Comparison methods:
  - `__lt__(self, other: Money) -> bool` -- raises `ValueError` if currencies differ; returns `self.amount < other.amount`
  - `__le__(self, other: Money) -> bool` -- raises `ValueError` if currencies differ; returns `self.amount <= other.amount`
  - `__gt__(self, other: Money) -> bool` -- raises `ValueError` if currencies differ; returns `self.amount > other.amount`
  - `__ge__(self, other: Money) -> bool` -- raises `ValueError` if currencies differ; returns `self.amount >= other.amount`
- Note: Because `@frozen` with `eq=True` (default) auto-generates `__eq__` and `__hash__`, we get correct equality. We must set `order=False` (which is the default for `@frozen`) to avoid conflict with our custom comparison methods. Actually `@frozen` does NOT auto-generate order methods by default, so custom `__lt__`/`__le__`/`__gt__`/`__ge__` are safe to define.
- DI scope: N/A (value object, no DI)
- Events raised: none
- Error conditions: `ValueError` on invalid amount or currency at construction; `ValueError` on cross-currency comparison

#### New imports to add:

```python
from attrs import frozen
```

This import is added at the top of the file alongside the existing `import enum` and `from typing import Any`.

#### Structural sketch (pseudo-code only):

```python
# After RequirementLevel enum, before EOF

class ProductStatus(str, enum.Enum):
    """Product lifecycle states.

    States:
        DRAFT: ...
        ENRICHING: ...
        READY_FOR_REVIEW: ...
        PUBLISHED: ...
        ARCHIVED: ...
    """
    DRAFT = "draft"
    ENRICHING = "enriching"
    READY_FOR_REVIEW = "ready_for_review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


@frozen
class Money:
    """Immutable value object representing a monetary amount.

    Stores amount in smallest currency units (e.g., kopecks for RUB).
    Supports ordering comparisons only between same-currency instances.

    Attributes:
        amount: Non-negative integer in smallest currency units.
        currency: 3-character ISO 4217 currency code.
    """
    amount: int
    currency: str

    def __attrs_post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Money amount must be non-negative")
        if len(self.currency) != 3:
            raise ValueError("Currency must be a 3-character ISO code")

    def _check_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise ValueError(
                f"Cannot compare Money with different currencies: "
                f"{self.currency} vs {other.currency}"
            )

    def __lt__(self, other: "Money") -> bool:
        self._check_currency(other)
        return self.amount < other.amount

    def __le__(self, other: "Money") -> bool:
        self._check_currency(other)
        return self.amount <= other.amount

    def __gt__(self, other: "Money") -> bool:
        self._check_currency(other)
        return self.amount > other.amount

    def __ge__(self, other: "Money") -> bool:
        self._check_currency(other)
        return self.amount >= other.amount
```

---

## Dependency registration

No DI changes required for this micro-task.

## Migration plan

No database changes required for this micro-task.

## Integration points

No cross-module integration in this micro-task.

## Risks & edge cases

| Risk | Impact | Mitionale/Mitigation |
|------|--------|------------|
| `@frozen` prevents `__attrs_post_init__` from setting attributes | Validation-only `__attrs_post_init__` does not set any attributes, so this is safe. If it tried to set attrs, it would raise `FrozenInstanceError`. | Only read fields in post-init; never assign. |
| Custom `__lt__` etc. conflict with attrs-generated order methods | attrs `@frozen` defaults to `order=False`, so no auto-generated ordering methods exist. Custom methods are safe. | Verify `@frozen` does not set `order=True` by default (confirmed: it does not). |
| Money(0, "RUB") edge case | Zero-amount money is valid (free items, discounts to zero). | amount >= 0 allows zero. |
| Currency validation too loose (allows "XYZ") | 3-char check is intentional for MVP; full ISO 4217 validation is deferred. Repositories and presentation layer can enforce stricter rules. | Document in docstring that only length is validated. |
| Existing tests may import from value_objects | Adding new types is additive; no existing imports break. | Run full test suite to confirm. |

## Acceptance verification

How senior-backend should verify this MT is correctly implemented:

```bash
uv run pytest tests/unit/ tests/architecture/ -v
uv run ruff check .
uv run mypy .
```

**Specific checks:**
- [ ] ProductStatus enum has exactly 5 values: DRAFT, ENRICHING, READY_FOR_REVIEW, PUBLISHED, ARCHIVED
- [ ] ProductStatus values are lowercase strings matching ORM enum: "draft", "enriching", "ready_for_review", "published", "archived"
- [ ] Money is a frozen attrs dataclass with `amount: int` and `currency: str`
- [ ] `Money(-1, "RUB")` raises `ValueError`
- [ ] `Money(100, "RU")` raises `ValueError` (not 3 chars)
- [ ] `Money(100, "RUBB")` raises `ValueError` (not 3 chars)
- [ ] `Money(100, "RUB") < Money(200, "RUB")` returns `True`
- [ ] `Money(100, "RUB") < Money(100, "USD")` raises `ValueError`
- [ ] `Money(100, "RUB") == Money(100, "RUB")` returns `True`
- [ ] `Money(100, "RUB") == Money(100, "USD")` returns `False` (different VOs)
- [ ] `Money(0, "RUB")` is valid (zero amount allowed)
- [ ] Attempting to mutate `Money` fields raises `FrozenInstanceError`
- [ ] Domain layer has zero framework imports (no SQLAlchemy, FastAPI, Pydantic, Redis)
- [ ] All existing tests pass after this change
- [ ] Linter and type-checker pass
