# AttributeFamily Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace direct category-attribute bindings with `AttributeFamily` — a standalone aggregate supporting unlimited-depth polymorphic inheritance, per-level overrides, and attribute exclusions.

**Architecture:** Three new aggregates (`AttributeFamily`, `FamilyAttributeBinding`, `FamilyAttributeExclusion`) following the existing DDD/CQRS patterns. Category gains an optional `family_id` FK. Storefront queries resolve attributes through Family instead of direct bindings. Old `category_attribute_rules` table and all related code are removed.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.1 (async), PostgreSQL (recursive CTEs), Redis (caching), Dishka DI, attrs (entities), Pydantic v2 (schemas), Alembic (migrations), pytest + testcontainers.

**Spec:** `docs/superpowers/specs/2026-03-25-attribute-family-design.md`

---

## File Map

### New Files

| File                                                                            | Responsibility                                                                                           |
| ------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `src/modules/catalog/domain/entities.py` (additions)                            | `AttributeFamily`, `FamilyAttributeBinding`, `FamilyAttributeExclusion` aggregate roots                  |
| `src/modules/catalog/domain/interfaces.py` (additions)                          | `IAttributeFamilyRepository`, `IFamilyAttributeBindingRepository`, `IFamilyAttributeExclusionRepository` |
| `src/modules/catalog/domain/events.py` (additions)                              | 8 new `CatalogEvent` subclasses                                                                          |
| `src/modules/catalog/domain/exceptions.py` (additions)                          | 9 new exception classes                                                                                  |
| `src/modules/catalog/infrastructure/models.py` (additions)                      | 3 ORM models                                                                                             |
| `src/modules/catalog/infrastructure/repositories/attribute_family.py`           | Repository with recursive CTE queries                                                                    |
| `src/modules/catalog/infrastructure/repositories/family_attribute_binding.py`   | Binding repository                                                                                       |
| `src/modules/catalog/infrastructure/repositories/family_attribute_exclusion.py` | Exclusion repository                                                                                     |
| `src/modules/catalog/application/commands/create_attribute_family.py`           | Create handler                                                                                           |
| `src/modules/catalog/application/commands/update_attribute_family.py`           | Update handler                                                                                           |
| `src/modules/catalog/application/commands/delete_attribute_family.py`           | Delete handler                                                                                           |
| `src/modules/catalog/application/commands/bind_attribute_to_family.py`          | Bind handler                                                                                             |
| `src/modules/catalog/application/commands/unbind_attribute_from_family.py`      | Unbind handler                                                                                           |
| `src/modules/catalog/application/commands/update_family_attribute_binding.py`   | Update binding handler                                                                                   |
| `src/modules/catalog/application/commands/reorder_family_bindings.py`           | Reorder handler                                                                                          |
| `src/modules/catalog/application/commands/add_family_exclusion.py`              | Add exclusion handler                                                                                    |
| `src/modules/catalog/application/commands/remove_family_exclusion.py`           | Remove exclusion handler                                                                                 |
| `src/modules/catalog/application/queries/resolve_family_attributes.py`          | Effective attribute resolution + caching                                                                 |
| `src/modules/catalog/application/queries/list_attribute_families.py`            | List + tree queries                                                                                      |
| `src/modules/catalog/presentation/router_attribute_families.py`                 | All family REST endpoints                                                                                |
| `src/modules/catalog/presentation/schemas.py` (additions)                       | Family request/response schemas                                                                          |
| `alembic/versions/2026/03/25_*_attribute_family.py`                             | Migration                                                                                                |

### Files to Modify

| File                                                                | Change                                                                                  |
| ------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `src/modules/catalog/domain/entities.py`                            | Add `family_id` to `Category` entity + `_UPDATABLE_FIELDS`                              |
| `src/modules/catalog/infrastructure/models.py`                      | Add `family_id` column to `Category` ORM, add `attribute_bindings` relationship removal |
| `src/modules/catalog/application/queries/storefront.py`             | Rewrite `_load_bindings_with_attributes()` → resolve via Family                         |
| `src/modules/catalog/application/commands/create_category.py`       | Accept optional `family_id`                                                             |
| `src/modules/catalog/application/commands/update_category.py`       | Accept optional `family_id`                                                             |
| `src/modules/catalog/application/commands/delete_attribute.py`      | Check `family_attribute_bindings` instead of `category_attribute_rules`                 |
| `src/modules/catalog/domain/interfaces.py` → `IAttributeRepository` | Remove `has_category_bindings()` method                                                 |
| `src/modules/catalog/infrastructure/repositories/attribute.py`      | Remove `has_category_bindings()` implementation                                         |
| `src/modules/catalog/infrastructure/repositories/__init__.py`       | Remove old binding repo export, add new repos                                           |
| `src/modules/catalog/presentation/schemas.py`                       | Add `familyId` to `CategoryCreateRequest` / `CategoryUpdateRequest`                     |
| `src/modules/catalog/presentation/router_products.py`               | Remove any old binding imports                                                          |
| `src/modules/catalog/presentation/dependencies.py`                  | Replace `CategoryAttributeBindingProvider` with `AttributeFamilyProvider`               |
| `src/bootstrap/container.py`                                        | Replace `CategoryAttributeBindingProvider()` with `AttributeFamilyProvider()`           |
| `src/api/router.py`                                                 | Replace `category_binding_router` with `attribute_family_router`                        |

### Files to Delete

| File                                                                            |
| ------------------------------------------------------------------------------- |
| `src/modules/catalog/infrastructure/repositories/category_attribute_binding.py` |
| `src/modules/catalog/application/commands/bind_attribute_to_category.py`        |
| `src/modules/catalog/application/commands/unbind_attribute_from_category.py`    |
| `src/modules/catalog/application/commands/update_category_attribute_binding.py` |
| `src/modules/catalog/application/commands/reorder_category_bindings.py`         |
| `src/modules/catalog/application/commands/bulk_update_requirement_levels.py`    |
| `src/modules/catalog/application/queries/list_category_bindings.py`             |
| `src/modules/catalog/presentation/router_category_bindings.py`                  |

---

## Phase 1: Domain Layer (Entities, Exceptions, Events, Interfaces)

### Task 1: Add Exception Classes

**Files:**

- Modify: `src/modules/catalog/domain/exceptions.py`

- [ ] **Step 1: Add all new exception classes at the end of the file**

```python
# ---------------------------------------------------------------------------
# AttributeFamily exceptions
# ---------------------------------------------------------------------------


class AttributeFamilyNotFoundError(NotFoundError):
    """Raised when an attribute family lookup yields no result."""

    def __init__(self, family_id: uuid.UUID | str):
        super().__init__(
            message=f"Attribute family with ID {family_id} not found.",
            error_code="ATTRIBUTE_FAMILY_NOT_FOUND",
            details={"family_id": str(family_id)},
        )


class AttributeFamilyCodeAlreadyExistsError(ConflictError):
    """Raised when a family code conflicts with an existing one."""

    def __init__(self, code: str):
        super().__init__(
            message=f"Attribute family with code '{code}' already exists.",
            error_code="ATTRIBUTE_FAMILY_CODE_CONFLICT",
            details={"code": code},
        )


class AttributeFamilyHasChildrenError(ConflictError):
    """Raised when attempting to delete a family that has children."""

    def __init__(self, family_id: uuid.UUID):
        super().__init__(
            message="Cannot delete attribute family: it has child families.",
            error_code="ATTRIBUTE_FAMILY_HAS_CHILDREN",
            details={"family_id": str(family_id)},
        )


class AttributeFamilyHasCategoryReferencesError(ConflictError):
    """Raised when attempting to delete a family referenced by categories."""

    def __init__(self, family_id: uuid.UUID):
        super().__init__(
            message="Cannot delete attribute family: it is referenced by categories.",
            error_code="ATTRIBUTE_FAMILY_HAS_CATEGORY_REFERENCES",
            details={"family_id": str(family_id)},
        )


class AttributeFamilyParentImmutableError(UnprocessableEntityError):
    """Raised when attempting to change parent_id or level after creation."""

    def __init__(self, family_id: uuid.UUID):
        super().__init__(
            message="Cannot change parent_id or level after family creation.",
            error_code="ATTRIBUTE_FAMILY_PARENT_IMMUTABLE",
            details={"family_id": str(family_id)},
        )


# ---------------------------------------------------------------------------
# FamilyAttributeBinding exceptions
# ---------------------------------------------------------------------------


class FamilyAttributeBindingNotFoundError(NotFoundError):
    """Raised when a family-attribute binding lookup yields no result."""

    def __init__(self, binding_id: uuid.UUID):
        super().__init__(
            message=f"Family attribute binding with ID {binding_id} not found.",
            error_code="FAMILY_ATTRIBUTE_BINDING_NOT_FOUND",
            details={"binding_id": str(binding_id)},
        )


class FamilyAttributeBindingAlreadyExistsError(ConflictError):
    """Raised when a family-attribute binding pair already exists."""

    def __init__(self, family_id: uuid.UUID, attribute_id: uuid.UUID):
        super().__init__(
            message="This attribute is already bound to the family.",
            error_code="FAMILY_ATTRIBUTE_BINDING_ALREADY_EXISTS",
            details={
                "family_id": str(family_id),
                "attribute_id": str(attribute_id),
            },
        )


# ---------------------------------------------------------------------------
# FamilyAttributeExclusion exceptions
# ---------------------------------------------------------------------------


class FamilyAttributeExclusionNotFoundError(NotFoundError):
    """Raised when a family attribute exclusion lookup yields no result."""

    def __init__(self, exclusion_id: uuid.UUID):
        super().__init__(
            message=f"Family attribute exclusion with ID {exclusion_id} not found.",
            error_code="FAMILY_ATTRIBUTE_EXCLUSION_NOT_FOUND",
            details={"exclusion_id": str(exclusion_id)},
        )


class AttributeNotInheritedError(ValidationError):
    """Raised when trying to exclude an attribute not inherited from ancestors."""

    def __init__(self, family_id: uuid.UUID, attribute_id: uuid.UUID):
        super().__init__(
            message="Cannot exclude: attribute is not inherited from any ancestor family.",
            error_code="ATTRIBUTE_NOT_INHERITED",
            details={
                "family_id": str(family_id),
                "attribute_id": str(attribute_id),
            },
        )


class FamilyExclusionConflictsWithOwnBindingError(ConflictError):
    """Raised when trying to exclude an attribute that has a direct binding on the same family."""

    def __init__(self, family_id: uuid.UUID, attribute_id: uuid.UUID):
        super().__init__(
            message="Cannot exclude: attribute has a direct binding on this family. Remove the binding first.",
            error_code="FAMILY_EXCLUSION_CONFLICTS_WITH_OWN_BINDING",
            details={
                "family_id": str(family_id),
                "attribute_id": str(attribute_id),
            },
        )


class AttributeHasFamilyBindingsError(ConflictError):
    """Raised when attempting to delete an attribute bound to families."""

    def __init__(self, attribute_id: uuid.UUID):
        super().__init__(
            message="Cannot delete attribute: it is bound to one or more attribute families.",
            error_code="ATTRIBUTE_HAS_FAMILY_BINDINGS",
            details={"attribute_id": str(attribute_id)},
        )
```

- [ ] **Step 2: Replace `AttributeHasCategoryBindingsError` with `AttributeHasFamilyBindingsError`**

Find `AttributeHasCategoryBindingsError` in the file and remove it. Grep for all usages across the codebase and update them to `AttributeHasFamilyBindingsError`.

Run: `grep -r "AttributeHasCategoryBindingsError" src/`

- [ ] **Step 3: Commit**

```bash
git add src/modules/catalog/domain/exceptions.py
git commit -m "feat(catalog): add AttributeFamily exception classes"
```

---

### Task 2: Add Domain Events

**Files:**

- Modify: `src/modules/catalog/domain/events.py`

- [ ] **Step 1: Add 8 new event classes after the existing `RequirementLevelsUpdatedEvent`**

Replace the entire `CategoryAttributeBinding events` section (lines 385-456) with:

```python
# ---------------------------------------------------------------------------
# AttributeFamily events
# ---------------------------------------------------------------------------


@dataclass
class AttributeFamilyCreatedEvent(
    CatalogEvent,
    required_fields=("family_id",),
    aggregate_id_field="family_id",
):
    """Emitted when a new attribute family is created."""

    family_id: uuid.UUID | None = None
    code: str = ""
    parent_id: uuid.UUID | None = None
    aggregate_type: str = "AttributeFamily"
    event_type: str = "AttributeFamilyCreatedEvent"


@dataclass
class AttributeFamilyUpdatedEvent(
    CatalogEvent,
    required_fields=("family_id",),
    aggregate_id_field="family_id",
):
    """Emitted when an attribute family is updated."""

    family_id: uuid.UUID | None = None
    aggregate_type: str = "AttributeFamily"
    event_type: str = "AttributeFamilyUpdatedEvent"


@dataclass
class AttributeFamilyDeletedEvent(
    CatalogEvent,
    required_fields=("family_id",),
    aggregate_id_field="family_id",
):
    """Emitted when an attribute family is deleted."""

    family_id: uuid.UUID | None = None
    code: str = ""
    aggregate_type: str = "AttributeFamily"
    event_type: str = "AttributeFamilyDeletedEvent"


# ---------------------------------------------------------------------------
# FamilyAttributeBinding events
# ---------------------------------------------------------------------------


@dataclass
class FamilyAttributeBindingCreatedEvent(
    CatalogEvent,
    required_fields=("binding_id",),
    aggregate_id_field="binding_id",
):
    """Emitted when an attribute is bound to a family."""

    family_id: uuid.UUID | None = None
    attribute_id: uuid.UUID | None = None
    binding_id: uuid.UUID | None = None
    aggregate_type: str = "FamilyAttributeBinding"
    event_type: str = "FamilyAttributeBindingCreatedEvent"


@dataclass
class FamilyAttributeBindingUpdatedEvent(
    CatalogEvent,
    required_fields=("binding_id",),
    aggregate_id_field="binding_id",
):
    """Emitted when a family-attribute binding is updated."""

    binding_id: uuid.UUID | None = None
    aggregate_type: str = "FamilyAttributeBinding"
    event_type: str = "FamilyAttributeBindingUpdatedEvent"


@dataclass
class FamilyAttributeBindingDeletedEvent(
    CatalogEvent,
    required_fields=("binding_id",),
    aggregate_id_field="binding_id",
):
    """Emitted when an attribute is unbound from a family."""

    family_id: uuid.UUID | None = None
    attribute_id: uuid.UUID | None = None
    binding_id: uuid.UUID | None = None
    aggregate_type: str = "FamilyAttributeBinding"
    event_type: str = "FamilyAttributeBindingDeletedEvent"


# ---------------------------------------------------------------------------
# FamilyAttributeExclusion events
# ---------------------------------------------------------------------------


@dataclass
class FamilyAttributeExclusionAddedEvent(
    CatalogEvent,
    required_fields=("exclusion_id",),
    aggregate_id_field="exclusion_id",
):
    """Emitted when an inherited attribute is excluded from a family."""

    family_id: uuid.UUID | None = None
    attribute_id: uuid.UUID | None = None
    exclusion_id: uuid.UUID | None = None
    aggregate_type: str = "FamilyAttributeExclusion"
    event_type: str = "FamilyAttributeExclusionAddedEvent"


@dataclass
class FamilyAttributeExclusionRemovedEvent(
    CatalogEvent,
    required_fields=("exclusion_id",),
    aggregate_id_field="exclusion_id",
):
    """Emitted when an attribute exclusion is removed from a family."""

    family_id: uuid.UUID | None = None
    attribute_id: uuid.UUID | None = None
    exclusion_id: uuid.UUID | None = None
    aggregate_type: str = "FamilyAttributeExclusion"
    event_type: str = "FamilyAttributeExclusionRemovedEvent"
```

- [ ] **Step 2: Remove old CategoryAttributeBinding events**

Delete: `CategoryAttributeBindingCreatedEvent`, `CategoryAttributeBindingUpdatedEvent`, `CategoryAttributeBindingDeletedEvent`, `CategoryBindingsReorderedEvent`, `RequirementLevelsUpdatedEvent`.

- [ ] **Step 3: Update module docstring** to mention AttributeFamily aggregates.

- [ ] **Step 4: Commit**

```bash
git add src/modules/catalog/domain/events.py
git commit -m "feat(catalog): add AttributeFamily domain events, remove category binding events"
```

---

### Task 3: Add Domain Entities

**Files:**

- Modify: `src/modules/catalog/domain/entities.py`

- [ ] **Step 1: Add guarded fields constant near existing ones (around line 98)**

```python
_FAMILY_GUARDED_FIELDS: frozenset[str] = frozenset({"code", "parent_id", "level"})
```

- [ ] **Step 2: Add `AttributeFamily` entity after `Category` class**

Follow the exact pattern from `Category` (create_root / create_child, **setattr** guard, \_UPDATABLE_FIELDS). See spec for all fields and methods.

Key: `AttributeFamily` must have:

- `__setattr__` guard for `_FAMILY_GUARDED_FIELDS`
- `__attrs_post_init__` that sets `_AttributeFamily__initialized = True`
- `create_root()` and `create_child(parent)` factory methods
- `update(**kwargs)` method restricted to `_UPDATABLE_FIELDS = frozenset({"name_i18n", "description_i18n", "sort_order"})`
- `validate_deletable(has_children, has_category_refs)` method

- [ ] **Step 3: Add `FamilyAttributeBinding` entity**

Follow exact pattern from `CategoryAttributeBinding`:

- Standalone `AggregateRoot`
- `create()` factory method
- `update(**kwargs)` with `_UPDATABLE_FIELDS = frozenset({"sort_order", "requirement_level", "flag_overrides", "filter_settings"})`

- [ ] **Step 4: Add `FamilyAttributeExclusion` entity**

Simple aggregate:

- `create(family_id, attribute_id)` factory
- No update method (immutable — create or delete only)

- [ ] **Step 5: Add `family_id` field to `Category` entity**

Add `family_id: uuid.UUID | None = None` field. Add `"family_id"` to Category's `_UPDATABLE_FIELDS`.

- [ ] **Step 6: Remove `CategoryAttributeBinding` entity**

Delete the entire `CategoryAttributeBinding` class and related imports.

- [ ] **Step 7: Update imports at top of file** — add new event imports, remove old ones.

- [ ] **Step 8: Commit**

```bash
git add src/modules/catalog/domain/entities.py
git commit -m "feat(catalog): add AttributeFamily/Binding/Exclusion entities, modify Category"
```

---

### Task 4: Add Repository Interfaces

**Files:**

- Modify: `src/modules/catalog/domain/interfaces.py`

- [ ] **Step 1: Add `IAttributeFamilyRepository`**

```python
class IAttributeFamilyRepository(ICatalogRepository[DomainAttributeFamily]):
    """Repository contract for the AttributeFamily aggregate."""

    @abstractmethod
    async def check_code_exists(self, code: str) -> bool: ...

    @abstractmethod
    async def check_code_exists_excluding(self, code: str, exclude_id: uuid.UUID) -> bool: ...

    @abstractmethod
    async def has_children(self, family_id: uuid.UUID) -> bool: ...

    @abstractmethod
    async def has_category_references(self, family_id: uuid.UUID) -> bool: ...

    @abstractmethod
    async def get_all_ordered(self) -> list[DomainAttributeFamily]: ...

    @abstractmethod
    async def get_ancestor_chain(self, family_id: uuid.UUID) -> list[DomainAttributeFamily]: ...

    @abstractmethod
    async def get_descendant_ids(self, family_id: uuid.UUID) -> list[uuid.UUID]: ...
```

- [ ] **Step 2: Add `IFamilyAttributeBindingRepository`**

```python
class IFamilyAttributeBindingRepository(ICatalogRepository[DomainFamilyAttributeBinding]):

    @abstractmethod
    async def check_binding_exists(self, family_id: uuid.UUID, attribute_id: uuid.UUID) -> bool: ...

    @abstractmethod
    async def get_by_family_and_attribute(self, family_id: uuid.UUID, attribute_id: uuid.UUID) -> DomainFamilyAttributeBinding | None: ...

    @abstractmethod
    async def list_ids_by_family(self, family_id: uuid.UUID) -> set[uuid.UUID]: ...

    @abstractmethod
    async def get_bindings_for_families(self, family_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[DomainFamilyAttributeBinding]]: ...

    @abstractmethod
    async def bulk_update_sort_order(self, updates: list[tuple[uuid.UUID, int]]) -> None: ...

    @abstractmethod
    async def has_bindings_for_attribute(self, attribute_id: uuid.UUID) -> bool: ...
```

- [ ] **Step 3: Add `IFamilyAttributeExclusionRepository`**

```python
class IFamilyAttributeExclusionRepository(ICatalogRepository[DomainFamilyAttributeExclusion]):

    @abstractmethod
    async def check_exclusion_exists(self, family_id: uuid.UUID, attribute_id: uuid.UUID) -> bool: ...

    @abstractmethod
    async def get_exclusions_for_families(self, family_ids: list[uuid.UUID]) -> dict[uuid.UUID, set[uuid.UUID]]: ...
```

- [ ] **Step 4: Remove `ICategoryAttributeBindingRepository`**

- [ ] **Step 5: Commit**

```bash
git add src/modules/catalog/domain/interfaces.py
git commit -m "feat(catalog): add AttributeFamily repository interfaces"
```

---

## Phase 2: Infrastructure Layer (ORM Models, Repositories, Migration)

### Task 5: Add ORM Models

**Files:**

- Modify: `src/modules/catalog/infrastructure/models.py`

- [ ] **Step 1: Add `AttributeFamily` ORM model** after existing `Category` model

```python
class AttributeFamily(Base):
    """ORM model for the attribute family hierarchy."""

    __tablename__ = "attribute_families"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid7)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("attribute_families.id", ondelete="RESTRICT"), index=True
    )
    code: Mapped[str] = mapped_column(String(100), unique=True)
    name_i18n: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    description_i18n: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    sort_order: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    level: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    children: Mapped[list[AttributeFamily]] = relationship("AttributeFamily", back_populates="parent", cascade="all, delete-orphan")
    parent: Mapped[AttributeFamily] = relationship("AttributeFamily", back_populates="children", remote_side="AttributeFamily.id")
    bindings: Mapped[list[FamilyAttributeBinding]] = relationship("FamilyAttributeBinding", back_populates="family", cascade="all, delete-orphan")
    exclusions: Mapped[list[FamilyAttributeExclusion]] = relationship("FamilyAttributeExclusion", back_populates="family", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_attribute_families_level_sort", "level", "sort_order"),
    )
```

- [ ] **Step 2: Add `FamilyAttributeBinding` ORM model**

Follow existing `CategoryAttributeBinding` ORM pattern exactly. Unique constraint on `(family_id, attribute_id)`.

- [ ] **Step 3: Add `FamilyAttributeExclusion` ORM model**

Unique constraint on `(family_id, attribute_id)`.

- [ ] **Step 4: Add `family_id` column to `Category` ORM model**

```python
family_id: Mapped[uuid.UUID | None] = mapped_column(
    ForeignKey("attribute_families.id", ondelete="SET NULL"), index=True
)
```

Add relationship: `family: Mapped[AttributeFamily | None] = relationship("AttributeFamily")`

- [ ] **Step 5: Remove `CategoryAttributeBinding` ORM model** and its relationship from `Category`.

- [ ] **Step 6: Commit**

```bash
git add src/modules/catalog/infrastructure/models.py
git commit -m "feat(catalog): add AttributeFamily ORM models, modify Category"
```

---

### Task 6: Create Alembic Migration

**Files:**

- Create: `alembic/versions/2026/03/25_*_attribute_family.py`

- [ ] **Step 1: Generate migration**

Run: `cd C:/Users/Sanjar/Desktop/loyality/backend && uv run alembic revision --autogenerate -m "add attribute families replace category bindings"`

- [ ] **Step 2: Verify the generated migration contains:**

1. `CREATE TABLE attribute_families` with all columns and indexes
2. `CREATE TABLE family_attribute_bindings` with unique constraint
3. `CREATE TABLE family_attribute_exclusions` with unique constraint
4. `ALTER TABLE categories ADD COLUMN family_id` with FK and index
5. `DROP TABLE category_attribute_rules`

- [ ] **Step 3: Manually add `DROP TABLE category_attribute_rules`** to upgrade() if autogenerate missed it.

- [ ] **Step 4: Add downgrade()** that reverses all changes (recreate `category_attribute_rules`, drop new tables, remove `family_id` from categories).

- [ ] **Step 5: Run migration**

Run: `uv run alembic upgrade head`

- [ ] **Step 6: Commit**

```bash
git add alembic/
git commit -m "feat(catalog): add migration for attribute families"
```

---

### Task 7: Implement AttributeFamily Repository

**Files:**

- Create: `src/modules/catalog/infrastructure/repositories/attribute_family.py`

- [ ] **Step 1: Implement `AttributeFamilyRepository`** extending `BaseRepository[DomainAttributeFamily, OrmAttributeFamily]` and `IAttributeFamilyRepository`.

Must include:

- `_to_domain()` / `_to_orm()` mappings
- `check_code_exists()` and `check_code_exists_excluding()` using `_field_exists()`
- `has_children()` — check `parent_id = family_id` exists
- `has_category_references()` — check `categories.family_id = family_id` exists
- `get_all_ordered()` — `ORDER BY level, sort_order`
- `get_ancestor_chain(family_id)` — `WITH RECURSIVE` CTE walking parent_id up to root, ORDER BY level ASC
- `get_descendant_ids(family_id)` — `WITH RECURSIVE` CTE walking parent_id down, excluding self

- [ ] **Step 2: Commit**

```bash
git add src/modules/catalog/infrastructure/repositories/attribute_family.py
git commit -m "feat(catalog): implement AttributeFamilyRepository with CTE queries"
```

---

### Task 8: Implement FamilyAttributeBinding Repository

**Files:**

- Create: `src/modules/catalog/infrastructure/repositories/family_attribute_binding.py`

- [ ] **Step 1: Implement repository** following `CategoryAttributeBindingRepository` pattern.

Must include:

- Standard `_to_domain()` / `_to_orm()`
- `check_binding_exists()`
- `get_by_family_and_attribute()`
- `list_ids_by_family()`
- `get_bindings_for_families(family_ids)` — batch load all bindings for a list of family UUIDs, return `dict[UUID, list[...]]`
- `bulk_update_sort_order()`
- `has_bindings_for_attribute(attribute_id)` — for attribute deletion guard

- [ ] **Step 2: Commit**

```bash
git add src/modules/catalog/infrastructure/repositories/family_attribute_binding.py
git commit -m "feat(catalog): implement FamilyAttributeBindingRepository"
```

---

### Task 9: Implement FamilyAttributeExclusion Repository

**Files:**

- Create: `src/modules/catalog/infrastructure/repositories/family_attribute_exclusion.py`

- [ ] **Step 1: Implement repository**

Must include:

- Standard `_to_domain()` / `_to_orm()`
- `check_exclusion_exists()`
- `get_exclusions_for_families(family_ids)` — batch load, return `dict[UUID, set[UUID]]`

- [ ] **Step 2: Commit**

```bash
git add src/modules/catalog/infrastructure/repositories/family_attribute_exclusion.py
git commit -m "feat(catalog): implement FamilyAttributeExclusionRepository"
```

---

### Task 10: Delete Old Category Binding Code

**Files:**

- Delete: `src/modules/catalog/infrastructure/repositories/category_attribute_binding.py`
- Delete: `src/modules/catalog/application/commands/bind_attribute_to_category.py`
- Delete: `src/modules/catalog/application/commands/unbind_attribute_from_category.py`
- Delete: `src/modules/catalog/application/commands/update_category_attribute_binding.py`
- Delete: `src/modules/catalog/application/commands/reorder_category_bindings.py`
- Delete: `src/modules/catalog/application/commands/bulk_update_requirement_levels.py`
- Delete: `src/modules/catalog/presentation/router_category_bindings.py`

- [ ] **Step 1: Delete all 8 files**

```bash
rm src/modules/catalog/infrastructure/repositories/category_attribute_binding.py
rm src/modules/catalog/application/commands/bind_attribute_to_category.py
rm src/modules/catalog/application/commands/unbind_attribute_from_category.py
rm src/modules/catalog/application/commands/update_category_attribute_binding.py
rm src/modules/catalog/application/commands/reorder_category_bindings.py
rm src/modules/catalog/application/commands/bulk_update_requirement_levels.py
rm src/modules/catalog/application/queries/list_category_bindings.py
rm src/modules/catalog/presentation/router_category_bindings.py
```

- [ ] **Step 2: Remove old binding schemas from `presentation/schemas.py`**

Delete: `BindAttributeToCategoryRequest`, `BindAttributeToCategoryResponse`, `CategoryAttributeBindingResponse`, `CategoryAttributeBindingListResponse`, `ReorderBindingsRequest`, `BulkUpdateRequirementLevelsRequest` and related classes.

- [ ] **Step 3: Update `infrastructure/repositories/__init__.py`**

Remove `CategoryAttributeBindingRepository` from imports and `__all__`. (New repos will be added in Tasks 7-9.)

- [ ] **Step 4: Remove `has_category_bindings()` from `IAttributeRepository` and `AttributeRepository`**

This method queries the now-deleted `category_attribute_rules` table. Remove from:

- `src/modules/catalog/domain/interfaces.py` → `IAttributeRepository.has_category_bindings()`
- `src/modules/catalog/infrastructure/repositories/attribute.py` → implementation

- [ ] **Step 5: Clean up `router_products.py`** — remove any imports from deleted modules.

- [ ] **Step 6: Grep for any remaining imports of deleted code**

Run: `grep -rn "category_attribute_binding\|CategoryAttributeBinding\|bind_attribute_to_category\|unbind_attribute_from_category\|reorder_category_bindings\|bulk_update_requirement_levels\|category_binding_router\|list_category_bindings\|ListCategoryBindingsHandler\|has_category_bindings" src/`

Fix any broken imports found.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor(catalog): remove old category-attribute binding code"
```

---

> **Ordering note:** Task 10 deletes old code that `storefront.py` still imports (`CategoryAttributeBinding as OrmBinding`). Task 16 rewrites storefront.py. To avoid a broken import state between commits, execute Task 16 (rewrite storefront.py) immediately after or atomically with Task 10. The commits can be separate, but run them in the same session.

## Phase 3: Application Layer (Command Handlers, Queries)

### Task 11: Create AttributeFamily Command Handlers

**Files:**

- Create: `src/modules/catalog/application/commands/create_attribute_family.py`
- Create: `src/modules/catalog/application/commands/update_attribute_family.py`
- Create: `src/modules/catalog/application/commands/delete_attribute_family.py`

- [ ] **Step 1: Implement `CreateAttributeFamilyHandler`**

Follow `CreateCategoryHandler` pattern:

1. Check `code` uniqueness via `family_repo.check_code_exists()`
2. If `parent_id` provided → load parent, call `AttributeFamily.create_child(parent, ...)`
3. If no `parent_id` → call `AttributeFamily.create_root(...)`
4. Emit `AttributeFamilyCreatedEvent`
5. Persist, register with UoW, commit

- [ ] **Step 2: Implement `UpdateAttributeFamilyHandler`**

Follow `UpdateCategoryHandler` pattern:

1. Load family, validate exists
2. Call `family.update(**safe_fields)` — only `name_i18n`, `description_i18n`, `sort_order`
3. Emit `AttributeFamilyUpdatedEvent`
4. Persist, commit

- [ ] **Step 3: Implement `DeleteAttributeFamilyHandler`**

1. Load family
2. Check `has_children()` → raise `AttributeFamilyHasChildrenError`
3. Check `has_category_references()` → raise `AttributeFamilyHasCategoryReferencesError`
4. Emit `AttributeFamilyDeletedEvent`
5. Delete, commit

- [ ] **Step 4: Commit**

```bash
git add src/modules/catalog/application/commands/create_attribute_family.py \
        src/modules/catalog/application/commands/update_attribute_family.py \
        src/modules/catalog/application/commands/delete_attribute_family.py
git commit -m "feat(catalog): add AttributeFamily CRUD command handlers"
```

---

### Task 12: Create Family Binding Command Handlers

**Files:**

- Create: `src/modules/catalog/application/commands/bind_attribute_to_family.py`
- Create: `src/modules/catalog/application/commands/unbind_attribute_from_family.py`
- Create: `src/modules/catalog/application/commands/update_family_attribute_binding.py`
- Create: `src/modules/catalog/application/commands/reorder_family_bindings.py`

- [ ] **Step 1: Implement `BindAttributeToFamilyHandler`** — follow old `BindAttributeToCategoryHandler` pattern. Add family effective cache invalidation (family + all descendants).

- [ ] **Step 2: Implement `UnbindAttributeFromFamilyHandler`** — follow old unbind pattern. Cascade cache invalidation.

- [ ] **Step 3: Implement `UpdateFamilyAttributeBindingHandler`** — follow old update pattern. Cascade cache invalidation.

- [ ] **Step 4: Implement `ReorderFamilyBindingsHandler`** — follow old reorder pattern. Cascade cache invalidation.

- [ ] **Step 5: Commit**

```bash
git add src/modules/catalog/application/commands/bind_attribute_to_family.py \
        src/modules/catalog/application/commands/unbind_attribute_from_family.py \
        src/modules/catalog/application/commands/update_family_attribute_binding.py \
        src/modules/catalog/application/commands/reorder_family_bindings.py
git commit -m "feat(catalog): add family binding command handlers"
```

---

### Task 13: Create Exclusion Command Handlers

**Files:**

- Create: `src/modules/catalog/application/commands/add_family_exclusion.py`
- Create: `src/modules/catalog/application/commands/remove_family_exclusion.py`

- [ ] **Step 1: Implement `AddFamilyExclusionHandler`**

Key validation logic:

1. Load family, validate exists
2. Load attribute, validate exists
3. Check not in own bindings → `FamilyExclusionConflictsWithOwnBindingError`
4. Resolve ancestor effective attributes → check attribute is inherited → `AttributeNotInheritedError`
5. Check exclusion pair doesn't exist already
6. Create exclusion, emit event, commit
7. Cascade cache invalidation (family + descendants)

- [ ] **Step 2: Implement `RemoveFamilyExclusionHandler`**

1. Load exclusion, validate exists and belongs to family
2. Delete, emit event, commit
3. Cascade cache invalidation

- [ ] **Step 3: Commit**

```bash
git add src/modules/catalog/application/commands/add_family_exclusion.py \
        src/modules/catalog/application/commands/remove_family_exclusion.py
git commit -m "feat(catalog): add family exclusion command handlers"
```

---

### Task 14: Implement Effective Attribute Resolution Query

**Files:**

- Create: `src/modules/catalog/application/queries/resolve_family_attributes.py`

- [ ] **Step 1: Create `EffectiveAttributeReadModel`** (Pydantic BaseModel)

Fields: `attribute_id`, `code`, `slug`, `name_i18n`, `description_i18n`, `data_type`, `ui_type`, `is_dictionary`, `level`, `requirement_level`, `validation_rules`, `flag_overrides`, `filter_settings`, `source_family_id`, `is_overridden`, `values` (list of `StorefrontValueReadModel`), `sort_order`.

- [ ] **Step 2: Implement `ResolveFamilyAttributesHandler`**

Algorithm:

1. Check Redis cache `family:{family_id}:effective_attrs`
2. On miss: call `family_repo.get_ancestor_chain(family_id)` → chain
3. Call `binding_repo.get_bindings_for_families(chain_ids)` + `exclusion_repo.get_exclusions_for_families(chain_ids)`
4. Merge loop (root→leaf): exclusions first, then own bindings override
5. Load attribute metadata (JOIN with attributes table) for the effective set
6. Cache result, return

- [ ] **Step 3: Add `invalidate_family_effective_cache()` helper**

Takes `family_id` + `cache`. Calls `family_repo.get_descendant_ids(family_id)`, then deletes `family:{id}:effective_attrs` for self + all descendants.

- [ ] **Step 4: Commit**

```bash
git add src/modules/catalog/application/queries/resolve_family_attributes.py
git commit -m "feat(catalog): implement effective attribute resolution with caching"
```

---

### Task 15: Implement Family List/Tree Queries

**Files:**

- Create: `src/modules/catalog/application/queries/list_attribute_families.py`

- [ ] **Step 1: Implement `ListAttributeFamiliesHandler`** — paginated list query.

- [ ] **Step 2: Implement `GetAttributeFamilyTreeHandler`** — loads all families ordered, builds tree structure (same approach as category tree).

- [ ] **Step 3: Implement `GetAttributeFamilyHandler`** — single family by ID.

- [ ] **Step 4: Commit**

```bash
git add src/modules/catalog/application/queries/list_attribute_families.py
git commit -m "feat(catalog): add family list/tree/get query handlers"
```

---

### Task 16: Rewrite Storefront Queries

**Files:**

- Modify: `src/modules/catalog/application/queries/storefront.py`

- [ ] **Step 1: Replace `_load_bindings_with_attributes()`**

New logic:

1. Load category → get `family_id`
2. If `family_id is None` → return empty list (no family = no attributes)
3. Call `ResolveFamilyAttributesHandler.handle(family_id)` to get effective attributes
4. The effective attributes already have attribute metadata loaded

- [ ] **Step 2: Update all 4 storefront handlers** to use the new resolution path.

The handler signatures stay the same (take `category_id`), but internally resolve through family.

- [ ] **Step 3: Update cache invalidation** — storefront cache keys are now also invalidated when family effective cache changes. Add cross-invalidation in the family binding/exclusion handlers.

- [ ] **Step 4: Commit**

```bash
git add src/modules/catalog/application/queries/storefront.py
git commit -m "refactor(catalog): rewrite storefront queries to resolve through AttributeFamily"
```

---

### Task 17: Modify Category Commands

**Files:**

- Modify: `src/modules/catalog/application/commands/create_category.py`
- Modify: `src/modules/catalog/application/commands/update_category.py`

- [ ] **Step 1: Add `family_id` to `CreateCategoryCommand`** and pass it through to `Category.create_root()` / `create_child()`.

- [ ] **Step 2: Add `family_id` to `UpdateCategoryCommand`** and apply in handler. When `family_id` changes → invalidate storefront cache.

- [ ] **Step 3: Modify attribute delete handler** (`delete_attribute.py`):
  - Add `IFamilyAttributeBindingRepository` as constructor dependency
  - Replace `self._attribute_repo.has_category_bindings(attribute_id)` with `self._binding_repo.has_bindings_for_attribute(attribute_id)`
  - Replace `AttributeHasCategoryBindingsError` with `AttributeHasFamilyBindingsError`

- [ ] **Step 4: Update `update_category.py`** cache invalidation for `family_id` changes:
  - When `family_id` changes, invalidate storefront cache for the category: `invalidate_storefront_cache(cache, category_id)`
  - If old `family_id` was not None, also invalidate `family:{old_family_id}:effective_attrs`
  - If new `family_id` is not None, also invalidate `family:{new_family_id}:effective_attrs`

- [ ] **Step 5: Commit**

```bash
git add src/modules/catalog/application/commands/create_category.py \
        src/modules/catalog/application/commands/update_category.py \
        src/modules/catalog/application/commands/delete_attribute.py
git commit -m "feat(catalog): add family_id to category commands, update attribute delete guard"
```

---

## Phase 4: Presentation Layer (Schemas, Routers, DI)

### Task 18: Add Family Schemas

**Files:**

- Modify: `src/modules/catalog/presentation/schemas.py`

- [ ] **Step 1: Add family request/response schemas**

```python
# --- AttributeFamily schemas ---

class AttributeFamilyCreateRequest(CamelModel):
    code: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9_]+$")
    parent_id: uuid.UUID | None = None
    name_i18n: I18nDict = Field(..., min_length=1)
    description_i18n: I18nDict | None = Field(default_factory=dict)
    sort_order: int = Field(0, ge=0)

class AttributeFamilyCreateResponse(CamelModel):
    id: uuid.UUID

class AttributeFamilyResponse(CamelModel):
    id: uuid.UUID
    parent_id: uuid.UUID | None
    code: str
    name_i18n: dict[str, str]
    description_i18n: dict[str, str]
    sort_order: int
    level: int
    created_at: datetime
    updated_at: datetime

class AttributeFamilyTreeResponse(CamelModel):
    id: uuid.UUID
    code: str
    name_i18n: dict[str, str]
    level: int
    sort_order: int
    children: list[AttributeFamilyTreeResponse]

class AttributeFamilyUpdateRequest(CamelModel):
    name_i18n: I18nDict | None = None
    description_i18n: I18nDict | None = None
    sort_order: int | None = Field(None, ge=0)
    # model_validator: at least one field

class AttributeFamilyListResponse(CamelModel):
    items: list[AttributeFamilyResponse]
    total: int
    offset: int
    limit: int

# --- FamilyAttributeBinding schemas ---
# (same structure as old BindAttributeToCategoryRequest but with familyId)

class FamilyAttributeBindingRequest(CamelModel):
    attribute_id: uuid.UUID
    sort_order: int = Field(0, ge=0)
    requirement_level: str = Field("optional", pattern=r"^(required|recommended|optional)$")
    flag_overrides: BoundedJsonDict | None = None
    filter_settings: BoundedJsonDict | None = None

class FamilyAttributeBindingResponse(CamelModel):
    id: uuid.UUID

# ... etc (effective response, exclusion request/response)
```

- [ ] **Step 2: Add `family_id` to `CategoryCreateRequest` and `CategoryUpdateRequest`**

```python
family_id: uuid.UUID | None = None
```

- [ ] **Step 3: Commit**

```bash
git add src/modules/catalog/presentation/schemas.py
git commit -m "feat(catalog): add AttributeFamily presentation schemas"
```

---

### Task 19: Create Family Router

**Files:**

- Create: `src/modules/catalog/presentation/router_attribute_families.py`

- [ ] **Step 1: Implement all endpoints** following existing router patterns (DishkaRoute, RequirePermission, FromDishka):

Family CRUD:

- `POST /` → create
- `GET /` → list (paginated)
- `GET /tree` → tree
- `GET /{family_id}` → get
- `PATCH /{family_id}` → update
- `DELETE /{family_id}` → delete

Family Bindings (nested under `/{family_id}/attributes`):

- `POST /` → bind
- `GET /` → list own bindings
- `GET /effective` → resolved effective set
- `PATCH /{binding_id}` → update
- `DELETE /{binding_id}` → unbind
- `POST /reorder` → reorder

Family Exclusions (nested under `/{family_id}/exclusions`):

- `POST /` → add exclusion
- `GET /` → list exclusions
- `DELETE /{exclusion_id}` → remove exclusion

- [ ] **Step 2: Commit**

```bash
git add src/modules/catalog/presentation/router_attribute_families.py
git commit -m "feat(catalog): add AttributeFamily REST router with all endpoints"
```

---

### Task 20: Wire Up DI and Router Registration

**Files:**

- Modify: `src/modules/catalog/presentation/dependencies.py`
- Modify: `src/bootstrap/container.py`
- Modify: `src/api/router.py`

- [ ] **Step 1: Replace `CategoryAttributeBindingProvider` with `AttributeFamilyProvider`**

New provider registers:

- `AttributeFamilyRepository` → `IAttributeFamilyRepository`
- `FamilyAttributeBindingRepository` → `IFamilyAttributeBindingRepository`
- `FamilyAttributeExclusionRepository` → `IFamilyAttributeExclusionRepository`
- All 9 command handlers + 3 query handlers

- [ ] **Step 2: Update `container.py`** — replace `CategoryAttributeBindingProvider()` with `AttributeFamilyProvider()`.

- [ ] **Step 3: Update `router.py`** — replace `category_binding_router` import with `attribute_family_router`, mount with prefix `/catalog`.

- [ ] **Step 4: Register `ResolveFamilyAttributesHandler`** in `AttributeFamilyProvider` (or `StorefrontCatalogProvider`) with explicit `provide(ResolveFamilyAttributesHandler, scope=Scope.REQUEST)`.

- [ ] **Step 5: Update `AttributeProvider`** — add `IFamilyAttributeBindingRepository` as a dependency for `DeleteAttributeHandler` so it can call `has_bindings_for_attribute()`.

- [ ] **Step 6: Verify no broken imports**

Run: `grep -rn "CategoryAttributeBindingProvider\|category_binding_router\|ICategoryAttributeBindingRepository" src/`

Should return 0 results.

- [ ] **Step 6: Commit**

```bash
git add src/modules/catalog/presentation/dependencies.py \
        src/bootstrap/container.py \
        src/api/router.py
git commit -m "feat(catalog): wire AttributeFamily DI provider and router registration"
```

---

## Phase 5: Verification

### Task 21: Smoke Test

- [ ] **Step 1: Start the application**

Run: `uv run uvicorn main:app --reload --port 8000`

Expected: Server starts without import errors.

- [ ] **Step 2: Check OpenAPI docs**

Open: `http://localhost:8000/docs`

Verify: New `/catalog/attribute-families` endpoints appear. Old `/catalog/categories/{id}/attributes` endpoints are gone.

- [ ] **Step 3: Check migration state**

Run: `uv run alembic current`

Expected: Shows latest migration as head.

- [ ] **Step 4: Commit any fixes needed**

---

### Task 22: Update Frontend Integration Docs

**Files:**

- Modify: `C:/Users/Sanjar/Desktop/loyality/frontend/main/docs/product-attributes-integration.md`

- [ ] **Step 1: Update the doc to reflect new flow**

Old: `GET /catalog/storefront/categories/{categoryId}/form-attributes` queries category bindings directly.
New: Same endpoint, but backend resolves through `category.family_id → AttributeFamily → effective attributes`.

Frontend API calls remain identical — only the backend resolution changed.

- [ ] **Step 2: Add note about AttributeFamily admin endpoints** for admin panel integration.

- [ ] **Step 3: Commit**

```bash
git add C:/Users/Sanjar/Desktop/loyality/frontend/main/docs/product-attributes-integration.md
git commit -m "docs: update frontend integration doc for AttributeFamily"
```
