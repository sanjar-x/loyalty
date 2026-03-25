# Supplier Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract supplier management from catalog into a standalone DDD module with CRUD endpoints, activation/deactivation, cross-module validation, marketplace seeding, and source_url surfacing on products.

**Architecture:** New `src/modules/supplier/` module following the same layered DDD + CQRS pattern as catalog/identity. Supplier entity is an attrs `AggregateRoot` with `SupplierType` value object (moved from catalog). The catalog module accesses supplier data through an `ISupplierQueryService` interface — no direct imports of supplier internals. Existing `suppliers` DB table is reused (same physical table name), with `is_active` and `version` columns added via migration.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL, Dishka DI, attrs dataclasses, Pydantic v2

**PRD:** `prd.md` (project root)

---

## File Structure

### New files (supplier module)

```
src/modules/supplier/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── entities.py          # Supplier aggregate root (attrs)
│   ├── value_objects.py     # SupplierType enum (moved from catalog)
│   ├── exceptions.py        # SupplierNotFoundError, SupplierInactiveError, etc.
│   ├── interfaces.py        # ISupplierRepository, ISupplierQueryService
│   ├── events.py            # SupplierCreatedEvent, SupplierDeactivatedEvent, etc.
│   └── constants.py         # MARKETPLACE_SUPPLIERS seed data
├── application/
│   ├── __init__.py
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── create_supplier.py
│   │   ├── update_supplier.py
│   │   ├── deactivate_supplier.py
│   │   └── activate_supplier.py
│   └── queries/
│       ├── __init__.py
│       ├── read_models.py       # SupplierReadModel, SupplierListReadModel
│       ├── get_supplier.py
│       └── list_suppliers.py
├── infrastructure/
│   ├── __init__.py
│   ├── models.py            # Supplier ORM (moved from catalog)
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── supplier.py      # SupplierRepository (Data Mapper)
│   └── query_service.py     # SupplierQueryService (implements ISupplierQueryService)
└── presentation/
    ├── __init__.py
    ├── router.py             # FastAPI router (/suppliers)
    ├── schemas.py            # Pydantic request/response DTOs
    └── dependencies.py       # Dishka providers
```

### Modified files

```
src/modules/catalog/domain/value_objects.py       — remove SupplierType enum
src/modules/catalog/domain/entities.py            — import SupplierType from supplier module
src/modules/catalog/infrastructure/models.py      — remove Supplier ORM class, update imports
src/modules/catalog/presentation/schemas.py       — add source_url to ProductCreateRequest/Response
src/modules/catalog/application/commands/create_product.py — add supplier validation, source_url
src/infrastructure/database/registry.py           — update Supplier import path
src/api/router.py                                 — add supplier_router
src/bootstrap/container.py                        — add SupplierProvider
tests/conftest.py                                 — add SupplierProvider to test container
```

---

## Task Order

Dependencies require this execution order:

1. **Task 1** — Supplier domain layer (entities, value objects, exceptions, interfaces, events, constants)
2. **Task 2** — Move SupplierType from catalog to supplier module + update catalog imports (must happen before infrastructure layer to avoid duplicate SQLAlchemy enum registration)
3. **Task 3** — Supplier infrastructure layer (ORM model, repository, query service)
4. **Task 4** — Supplier application layer — commands (create, update, deactivate, activate)
5. **Task 5** — Supplier application layer — queries (get, list, read models)
6. **Task 6** — Supplier presentation layer (router, schemas, DI provider)
7. **Task 7** — Wire module into bootstrap (container, router, registry)
8. **Task 8** — Cross-module supplier validation (ISupplierQueryService in catalog)
9. **Task 9** — Source URL on product (domain, command, schema)
10. **Task 10** — Alembic migration (is_active, version columns, marketplace seed)
11. **Task 11** — Integration tests
12. **Task 12** — Final verification

---

### Task 1: Supplier domain layer

**Files:**

- Create: `src/modules/supplier/__init__.py`
- Create: `src/modules/supplier/domain/__init__.py`
- Create: `src/modules/supplier/domain/value_objects.py`
- Create: `src/modules/supplier/domain/entities.py`
- Create: `src/modules/supplier/domain/exceptions.py`
- Create: `src/modules/supplier/domain/interfaces.py`
- Create: `src/modules/supplier/domain/events.py`
- Create: `src/modules/supplier/domain/constants.py`
- Test: `tests/unit/modules/supplier/__init__.py`
- Test: `tests/unit/modules/supplier/domain/__init__.py`
- Test: `tests/unit/modules/supplier/domain/test_entities.py`

- [ ] **Step 1: Create module directory structure**

Create all `__init__.py` files for the supplier module and test directories:

```python
# src/modules/supplier/__init__.py
# (empty)
```

```python
# src/modules/supplier/domain/__init__.py
# (empty)
```

Same for `application/__init__.py`, `application/commands/__init__.py`, `application/queries/__init__.py`, `infrastructure/__init__.py`, `infrastructure/repositories/__init__.py`, `presentation/__init__.py`, and test mirrors.

- [ ] **Step 2: Create SupplierType value object**

```python
# src/modules/supplier/domain/value_objects.py
"""Supplier domain value objects."""

import enum


class SupplierType(enum.StrEnum):
    """Classification of supplier by geography and logistics model.

    CROSS_BORDER: Chinese marketplace suppliers (Poizon, Taobao, etc.)
    LOCAL: Russian regional suppliers
    """

    CROSS_BORDER = "cross_border"
    LOCAL = "local"
```

- [ ] **Step 3: Create domain events**

```python
# src/modules/supplier/domain/events.py
"""Supplier domain events for the Transactional Outbox."""

from dataclasses import dataclass

from src.shared.interfaces.entities import DomainEvent


@dataclass
class SupplierCreatedEvent(DomainEvent):
    aggregate_type: str = "Supplier"
    event_type: str = "supplier.created"
    supplier_name: str = ""
    supplier_type: str = ""


@dataclass
class SupplierUpdatedEvent(DomainEvent):
    aggregate_type: str = "Supplier"
    event_type: str = "supplier.updated"


@dataclass
class SupplierDeactivatedEvent(DomainEvent):
    aggregate_type: str = "Supplier"
    event_type: str = "supplier.deactivated"


@dataclass
class SupplierActivatedEvent(DomainEvent):
    aggregate_type: str = "Supplier"
    event_type: str = "supplier.activated"
```

- [ ] **Step 4: Create domain exceptions**

```python
# src/modules/supplier/domain/exceptions.py
"""Supplier domain exceptions."""

import uuid

from src.shared.exceptions import ConflictError, NotFoundError, UnprocessableEntityError


class SupplierNotFoundError(NotFoundError):
    def __init__(self, supplier_id: uuid.UUID | str):
        super().__init__(
            message=f"Supplier with ID {supplier_id} not found.",
            error_code="SUPPLIER_NOT_FOUND",
            details={"supplier_id": str(supplier_id)},
        )


class SupplierInactiveError(UnprocessableEntityError):
    def __init__(self, supplier_id: uuid.UUID | str):
        super().__init__(
            message=f"Supplier {supplier_id} is inactive and cannot be assigned to new products.",
            error_code="SUPPLIER_INACTIVE",
            details={"supplier_id": str(supplier_id)},
        )


class SupplierAlreadyActiveError(ConflictError):
    def __init__(self, supplier_id: uuid.UUID | str):
        super().__init__(
            message=f"Supplier {supplier_id} is already active.",
            error_code="SUPPLIER_ALREADY_ACTIVE",
            details={"supplier_id": str(supplier_id)},
        )


class SupplierAlreadyInactiveError(ConflictError):
    def __init__(self, supplier_id: uuid.UUID | str):
        super().__init__(
            message=f"Supplier {supplier_id} is already inactive.",
            error_code="SUPPLIER_ALREADY_INACTIVE",
            details={"supplier_id": str(supplier_id)},
        )


class SourceUrlRequiredError(UnprocessableEntityError):
    def __init__(self):
        super().__init__(
            message="source_url is required for cross-border suppliers.",
            error_code="SOURCE_URL_REQUIRED",
        )
```

- [ ] **Step 5: Create repository and query service interfaces**

```python
# src/modules/supplier/domain/interfaces.py
"""Supplier repository port interfaces."""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.modules.supplier.domain.entities import Supplier
from src.modules.supplier.domain.value_objects import SupplierType


class ISupplierRepository(ABC):
    """Write-side repository for the Supplier aggregate."""

    @abstractmethod
    async def add(self, entity: Supplier) -> Supplier: ...

    @abstractmethod
    async def get(self, entity_id: uuid.UUID) -> Supplier | None: ...

    @abstractmethod
    async def update(self, entity: Supplier) -> Supplier: ...


@dataclass(frozen=True)
class SupplierInfo:
    """Lightweight DTO returned by the cross-module query service."""

    id: uuid.UUID
    name: str
    type: SupplierType
    is_active: bool


class ISupplierQueryService(ABC):
    """Read-only interface for cross-module supplier lookups.

    The catalog module depends on this interface to validate supplier
    references without importing supplier internals.
    """

    @abstractmethod
    async def get_supplier_info(self, supplier_id: uuid.UUID) -> SupplierInfo | None: ...

    @abstractmethod
    async def assert_supplier_active(self, supplier_id: uuid.UUID) -> SupplierInfo: ...
```

- [ ] **Step 6: Create Supplier entity**

```python
# src/modules/supplier/domain/entities.py
"""Supplier aggregate root."""

import uuid
from datetime import UTC, datetime
from typing import Any, ClassVar

from attr import dataclass, field

from src.modules.supplier.domain.events import (
    SupplierActivatedEvent,
    SupplierCreatedEvent,
    SupplierDeactivatedEvent,
    SupplierUpdatedEvent,
)
from src.modules.supplier.domain.exceptions import (
    SupplierAlreadyActiveError,
    SupplierAlreadyInactiveError,
)
from src.modules.supplier.domain.value_objects import SupplierType
from src.shared.interfaces.entities import AggregateRoot


def _generate_id() -> uuid.UUID:
    return uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4()


_SUPPLIER_GUARDED_FIELDS: frozenset[str] = frozenset({"type"})


@dataclass
class Supplier(AggregateRoot):
    """Supplier aggregate root.

    Represents a product source — either a Chinese marketplace or a local
    regional supplier. Type is immutable after creation.

    Attributes:
        id: Unique supplier identifier (UUIDv7).
        name: Display name (max 255 chars).
        type: CROSS_BORDER or LOCAL (immutable).
        region: Geographic region (max 100 chars).
        is_active: Whether new products can reference this supplier.
        version: Optimistic locking counter.
    """

    id: uuid.UUID
    name: str
    type: SupplierType
    region: str
    is_active: bool = True
    version: int = 1
    created_at: datetime = field(factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(factory=lambda: datetime.now(UTC))

    _UPDATABLE_FIELDS: ClassVar[frozenset[str]] = frozenset({"name", "region"})

    def __setattr__(self, name: str, value: object) -> None:
        if name in _SUPPLIER_GUARDED_FIELDS and getattr(
            self, "_Supplier__initialized", False
        ):
            raise AttributeError(
                f"Cannot set '{name}' directly on Supplier. Type is immutable after creation."
            )
        super().__setattr__(name, value)

    def __attrs_post_init__(self) -> None:
        super().__attrs_post_init__()
        object.__setattr__(self, "_Supplier__initialized", True)

    @classmethod
    def create(
        cls,
        *,
        name: str,
        supplier_type: SupplierType,
        region: str,
        supplier_id: uuid.UUID | None = None,
        is_active: bool = True,
    ) -> "Supplier":
        if not name or not name.strip():
            raise ValueError("Supplier name is required.")
        if not region or not region.strip():
            raise ValueError("Supplier region is required.")

        supplier = cls(
            id=supplier_id or _generate_id(),
            name=name.strip(),
            type=supplier_type,
            region=region.strip(),
            is_active=is_active,
        )
        supplier.add_domain_event(
            SupplierCreatedEvent(
                aggregate_id=str(supplier.id),
                supplier_name=supplier.name,
                supplier_type=supplier.type.value,
            )
        )
        return supplier

    def update(self, **kwargs: Any) -> None:
        unknown = kwargs.keys() - self._UPDATABLE_FIELDS
        if unknown:
            raise TypeError(
                f"update() got unexpected keyword argument(s): {', '.join(sorted(unknown))}"
            )

        if "name" in kwargs:
            name = kwargs["name"]
            if not name or not name.strip():
                raise ValueError("Supplier name is required.")
            self.name = name.strip()

        if "region" in kwargs:
            region = kwargs["region"]
            if not region or not region.strip():
                raise ValueError("Supplier region is required.")
            self.region = region.strip()

        self.updated_at = datetime.now(UTC)
        self.add_domain_event(SupplierUpdatedEvent(aggregate_id=str(self.id)))

    def deactivate(self) -> None:
        if not self.is_active:
            raise SupplierAlreadyInactiveError(self.id)
        self.is_active = False
        self.updated_at = datetime.now(UTC)
        self.add_domain_event(SupplierDeactivatedEvent(aggregate_id=str(self.id)))

    def activate(self) -> None:
        if self.is_active:
            raise SupplierAlreadyActiveError(self.id)
        self.is_active = True
        self.updated_at = datetime.now(UTC)
        self.add_domain_event(SupplierActivatedEvent(aggregate_id=str(self.id)))
```

- [ ] **Step 7: Create marketplace seed constants**

```python
# src/modules/supplier/domain/constants.py
"""Marketplace supplier seed data.

Fixed UUIDv7 identifiers for the four known Chinese marketplace suppliers.
These are deterministic across all environments.
"""

import uuid

from src.modules.supplier.domain.value_objects import SupplierType

# Fixed UUIDv7 identifiers — generated once, used everywhere
POIZON_ID = uuid.UUID("019550a0-0001-7000-8000-000000000001")
TAOBAO_ID = uuid.UUID("019550a0-0002-7000-8000-000000000002")
PINDUODUO_ID = uuid.UUID("019550a0-0003-7000-8000-000000000003")
ALI_1688_ID = uuid.UUID("019550a0-0004-7000-8000-000000000004")

MARKETPLACE_SUPPLIERS: list[dict] = [
    {
        "id": POIZON_ID,
        "name": "Poizon",
        "type": SupplierType.CROSS_BORDER,
        "region": "China",
    },
    {
        "id": TAOBAO_ID,
        "name": "Taobao",
        "type": SupplierType.CROSS_BORDER,
        "region": "China",
    },
    {
        "id": PINDUODUO_ID,
        "name": "Pinduoduo",
        "type": SupplierType.CROSS_BORDER,
        "region": "China",
    },
    {
        "id": ALI_1688_ID,
        "name": "1688",
        "type": SupplierType.CROSS_BORDER,
        "region": "China",
    },
]
```

- [ ] **Step 8: Write unit tests for Supplier entity**

```python
# tests/unit/modules/supplier/domain/test_entities.py
"""Unit tests for Supplier domain entity."""

import uuid

import pytest

from src.modules.supplier.domain.entities import Supplier
from src.modules.supplier.domain.exceptions import (
    SupplierAlreadyActiveError,
    SupplierAlreadyInactiveError,
)
from src.modules.supplier.domain.value_objects import SupplierType


class TestSupplierCreate:
    def test_create_local_supplier(self):
        supplier = Supplier.create(
            name="Moscow Supplier",
            supplier_type=SupplierType.LOCAL,
            region="Moscow",
        )
        assert supplier.name == "Moscow Supplier"
        assert supplier.type == SupplierType.LOCAL
        assert supplier.region == "Moscow"
        assert supplier.is_active is True
        assert supplier.version == 1
        assert len(supplier.domain_events) == 1
        assert supplier.domain_events[0].event_type == "supplier.created"

    def test_create_cross_border_supplier(self):
        supplier = Supplier.create(
            name="Poizon",
            supplier_type=SupplierType.CROSS_BORDER,
            region="China",
        )
        assert supplier.type == SupplierType.CROSS_BORDER

    def test_create_with_fixed_id(self):
        fixed_id = uuid.uuid4()
        supplier = Supplier.create(
            name="Test", supplier_type=SupplierType.LOCAL, region="SPB",
            supplier_id=fixed_id,
        )
        assert supplier.id == fixed_id

    def test_create_empty_name_raises(self):
        with pytest.raises(ValueError, match="name is required"):
            Supplier.create(name="", supplier_type=SupplierType.LOCAL, region="Moscow")

    def test_create_empty_region_raises(self):
        with pytest.raises(ValueError, match="region is required"):
            Supplier.create(name="Test", supplier_type=SupplierType.LOCAL, region="")

    def test_create_strips_whitespace(self):
        supplier = Supplier.create(
            name="  Spaced  ", supplier_type=SupplierType.LOCAL, region="  Moscow  ",
        )
        assert supplier.name == "Spaced"
        assert supplier.region == "Moscow"


class TestSupplierUpdate:
    def test_update_name(self):
        supplier = Supplier.create(
            name="Old Name", supplier_type=SupplierType.LOCAL, region="Moscow",
        )
        supplier.clear_domain_events()
        supplier.update(name="New Name")
        assert supplier.name == "New Name"
        assert len(supplier.domain_events) == 1
        assert supplier.domain_events[0].event_type == "supplier.updated"

    def test_update_region(self):
        supplier = Supplier.create(
            name="Test", supplier_type=SupplierType.LOCAL, region="Moscow",
        )
        supplier.update(region="SPB")
        assert supplier.region == "SPB"

    def test_update_unknown_field_raises(self):
        supplier = Supplier.create(
            name="Test", supplier_type=SupplierType.LOCAL, region="Moscow",
        )
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            supplier.update(type=SupplierType.CROSS_BORDER)


class TestSupplierTypeImmutability:
    def test_type_cannot_be_changed_after_creation(self):
        supplier = Supplier.create(
            name="Test", supplier_type=SupplierType.LOCAL, region="Moscow",
        )
        with pytest.raises(AttributeError, match="immutable"):
            supplier.type = SupplierType.CROSS_BORDER


class TestSupplierActivation:
    def test_deactivate(self):
        supplier = Supplier.create(
            name="Test", supplier_type=SupplierType.LOCAL, region="Moscow",
        )
        supplier.clear_domain_events()
        supplier.deactivate()
        assert supplier.is_active is False
        assert supplier.domain_events[0].event_type == "supplier.deactivated"

    def test_deactivate_already_inactive_raises(self):
        supplier = Supplier.create(
            name="Test", supplier_type=SupplierType.LOCAL, region="Moscow",
        )
        supplier.deactivate()
        with pytest.raises(SupplierAlreadyInactiveError):
            supplier.deactivate()

    def test_activate(self):
        supplier = Supplier.create(
            name="Test", supplier_type=SupplierType.LOCAL, region="Moscow",
        )
        supplier.deactivate()
        supplier.clear_domain_events()
        supplier.activate()
        assert supplier.is_active is True
        assert supplier.domain_events[0].event_type == "supplier.activated"

    def test_activate_already_active_raises(self):
        supplier = Supplier.create(
            name="Test", supplier_type=SupplierType.LOCAL, region="Moscow",
        )
        with pytest.raises(SupplierAlreadyActiveError):
            supplier.activate()
```

- [ ] **Step 9: Run unit tests to verify they pass**

Run: `pytest tests/unit/modules/supplier/domain/test_entities.py -v`
Expected: All tests PASS

- [ ] **Step 10: Commit**

```bash
git add src/modules/supplier/domain/ src/modules/supplier/__init__.py tests/unit/modules/supplier/
git commit -m "feat(supplier): add domain layer — entity, value objects, exceptions, interfaces, events, constants"
```

---

### Task 2: Move SupplierType from catalog to supplier module

**Files:**

- Modify: `src/modules/catalog/domain/value_objects.py` — remove SupplierType, add re-export
- Modify: `src/modules/catalog/infrastructure/models.py` — remove Supplier ORM class, update SupplierType import, update Product.supplier relationship to string reference
- Modify: `src/modules/catalog/domain/entities.py` — update import if SupplierType is used
- Grep all files importing catalog's SupplierType and update

- [ ] **Step 1: Update catalog value_objects.py**

In `src/modules/catalog/domain/value_objects.py`, remove the `SupplierType` class definition and replace with a re-export:

```python
# Remove SupplierType class definition.
# Add re-export for backward compatibility:
from src.modules.supplier.domain.value_objects import SupplierType  # noqa: F401
```

- [ ] **Step 2: Remove Supplier ORM from catalog models**

In `src/modules/catalog/infrastructure/models.py`:

- Remove the entire `class Supplier(Base):` block (lines ~444-472)
- Update the `SupplierType` import to come from the supplier module:

```python
# Change:
from src.modules.catalog.domain.value_objects import SupplierType
# To:
from src.modules.supplier.domain.value_objects import SupplierType
```

- **Important:** Update the Product model's `supplier` relationship to reference the new ORM model path. Change:

```python
supplier: Mapped[Supplier] = relationship("Supplier", back_populates="products")
```

To a fully qualified string reference (avoids import cycle):

```python
supplier: Mapped["Supplier"] = relationship(
    "src.modules.supplier.infrastructure.models.Supplier",
    back_populates="products",
    foreign_keys="[Product.supplier_id]",
)
```

- Also remove the `Supplier` import from catalog's models.py since the class no longer lives there.

- [ ] **Step 3: Update all other files importing SupplierType from catalog**

Run grep to find all imports and update them. Most files can use the re-export from `catalog.domain.value_objects`, but for clarity new code should import from `supplier.domain.value_objects`.

- [ ] **Step 4: Verify no import cycles**

Run: `python -c "from src.modules.supplier.infrastructure.models import Supplier; print('OK')"`
Run: `python -c "from src.modules.catalog.infrastructure.models import Product; print('OK')"`

- [ ] **Step 5: Commit**

```bash
git add src/modules/catalog/ src/modules/supplier/
git commit -m "refactor(supplier): move SupplierType and Supplier ORM from catalog to supplier module"
```

---

### Task 3: Supplier infrastructure layer (ORM model, repository)

**Files:**

- Create: `src/modules/supplier/infrastructure/__init__.py`
- Create: `src/modules/supplier/infrastructure/models.py`
- Create: `src/modules/supplier/infrastructure/repositories/__init__.py`
- Create: `src/modules/supplier/infrastructure/repositories/supplier.py`
- Create: `src/modules/supplier/infrastructure/query_service.py`
- Test: `tests/integration/modules/supplier/__init__.py`
- Test: `tests/integration/modules/supplier/infrastructure/__init__.py`
- Test: `tests/integration/modules/supplier/infrastructure/repositories/__init__.py`
- Test: `tests/integration/modules/supplier/infrastructure/repositories/test_supplier.py`

- [ ] **Step 1: Create Supplier ORM model**

This is the new home for the Supplier ORM class. It mirrors the existing one in catalog but adds `is_active` and `version`:

```python
# src/modules/supplier/infrastructure/models.py
"""Supplier ORM model (Data Mapper pattern)."""

import uuid
from datetime import datetime
from typing import Any, ClassVar

from sqlalchemy import Boolean, Enum, Integer, String, func, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base
from src.modules.supplier.domain.value_objects import SupplierType


class Supplier(Base):
    """ORM model for the suppliers table.

    Adds is_active and version columns to support lifecycle management
    and optimistic locking.
    """

    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[SupplierType] = mapped_column(
        Enum(SupplierType, name="supplier_type_enum", create_type=False)
    )
    region: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
    version: Mapped[int] = mapped_column(
        Integer, server_default=text("1"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Keep the back-reference to Product for ORM relationship integrity.
    # Product ORM model references this via ForeignKey("suppliers.id").
    products: Mapped[list] = relationship(
        "src.modules.catalog.infrastructure.models.Product",
        back_populates="supplier",
    )

    __mapper_args__: ClassVar[dict[str, Any]] = {
        "version_id_col": version,
    }
```

> **Note:** The `products` relationship uses a string import path to avoid circular imports between modules. The `create_type=False` on the Enum prevents SQLAlchemy from trying to re-create the existing `supplier_type_enum` PostgreSQL type.

- [ ] **Step 2: Create SupplierRepository**

```python
# src/modules/supplier/infrastructure/repositories/supplier.py
"""Supplier repository — Data Mapper implementation."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.supplier.domain.entities import Supplier as DomainSupplier
from src.modules.supplier.domain.interfaces import ISupplierRepository
from src.modules.supplier.infrastructure.models import Supplier as OrmSupplier


class SupplierRepository(ISupplierRepository):
    """Data Mapper repository for the Supplier aggregate."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_domain(self, orm: OrmSupplier) -> DomainSupplier:
        return DomainSupplier(
            id=orm.id,
            name=orm.name,
            type=orm.type,
            region=orm.region or "",
            is_active=orm.is_active,
            version=orm.version,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    def _to_orm(self, entity: DomainSupplier, orm: OrmSupplier | None = None) -> OrmSupplier:
        if orm is None:
            orm = OrmSupplier()
        orm.id = entity.id
        orm.name = entity.name
        orm.type = entity.type
        orm.region = entity.region
        orm.is_active = entity.is_active
        return orm

    async def add(self, entity: DomainSupplier) -> DomainSupplier:
        orm = self._to_orm(entity)
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def get(self, entity_id: uuid.UUID) -> DomainSupplier | None:
        orm = await self._session.get(OrmSupplier, entity_id)
        if orm:
            return self._to_domain(orm)
        return None

    async def update(self, entity: DomainSupplier) -> DomainSupplier:
        orm = await self._session.get(OrmSupplier, entity.id)
        if not orm:
            raise ValueError(f"Supplier with id {entity.id} not found in database")
        orm = self._to_orm(entity, orm)
        await self._session.flush()
        return self._to_domain(orm)
```

```python
# src/modules/supplier/infrastructure/repositories/__init__.py
from src.modules.supplier.infrastructure.repositories.supplier import SupplierRepository

__all__ = ["SupplierRepository"]
```

- [ ] **Step 3: Create SupplierQueryService**

```python
# src/modules/supplier/infrastructure/query_service.py
"""Cross-module supplier query service implementation."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.supplier.domain.exceptions import (
    SupplierInactiveError,
    SupplierNotFoundError,
)
from src.modules.supplier.domain.interfaces import ISupplierQueryService, SupplierInfo
from src.modules.supplier.infrastructure.models import Supplier as OrmSupplier


class SupplierQueryService(ISupplierQueryService):
    """Read-only supplier lookups for cross-module validation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_supplier_info(self, supplier_id: uuid.UUID) -> SupplierInfo | None:
        stmt = select(OrmSupplier).where(OrmSupplier.id == supplier_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return SupplierInfo(
            id=orm.id, name=orm.name, type=orm.type, is_active=orm.is_active
        )

    async def assert_supplier_active(self, supplier_id: uuid.UUID) -> SupplierInfo:
        info = await self.get_supplier_info(supplier_id)
        if info is None:
            raise SupplierNotFoundError(supplier_id)
        if not info.is_active:
            raise SupplierInactiveError(supplier_id)
        return info
```

- [ ] **Step 4: Write integration test for repository**

```python
# tests/integration/modules/supplier/infrastructure/repositories/test_supplier.py
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.supplier.domain.entities import Supplier
from src.modules.supplier.domain.value_objects import SupplierType
from src.modules.supplier.infrastructure.repositories.supplier import SupplierRepository


async def test_supplier_repository_add_and_get(db_session: AsyncSession):
    repo = SupplierRepository(session=db_session)
    supplier = Supplier.create(
        name="Test Supplier", supplier_type=SupplierType.LOCAL, region="Moscow",
    )

    added = await repo.add(supplier)
    fetched = await repo.get(supplier.id)

    assert added.id == supplier.id
    assert fetched is not None
    assert fetched.name == "Test Supplier"
    assert fetched.type == SupplierType.LOCAL
    assert fetched.region == "Moscow"
    assert fetched.is_active is True


async def test_supplier_repository_update(db_session: AsyncSession):
    repo = SupplierRepository(session=db_session)
    supplier = Supplier.create(
        name="Old Name", supplier_type=SupplierType.LOCAL, region="Moscow",
    )
    await repo.add(supplier)

    supplier.update(name="New Name")
    updated = await repo.update(supplier)

    assert updated.name == "New Name"


async def test_supplier_repository_deactivate(db_session: AsyncSession):
    repo = SupplierRepository(session=db_session)
    supplier = Supplier.create(
        name="Active Supplier", supplier_type=SupplierType.CROSS_BORDER, region="China",
    )
    await repo.add(supplier)

    supplier.deactivate()
    updated = await repo.update(supplier)

    assert updated.is_active is False
```

- [ ] **Step 5: Commit**

```bash
git add src/modules/supplier/infrastructure/ tests/integration/modules/supplier/
git commit -m "feat(supplier): add infrastructure layer — ORM model, repository, query service"
```

---

### Task 4: Supplier application layer — commands

**Files:**

- Create: `src/modules/supplier/application/__init__.py`
- Create: `src/modules/supplier/application/commands/__init__.py`
- Create: `src/modules/supplier/application/commands/create_supplier.py`
- Create: `src/modules/supplier/application/commands/update_supplier.py`
- Create: `src/modules/supplier/application/commands/deactivate_supplier.py`
- Create: `src/modules/supplier/application/commands/activate_supplier.py`

- [ ] **Step 1: Create CreateSupplierCommand and handler**

```python
# src/modules/supplier/application/commands/create_supplier.py
"""Command handler: create a new supplier."""

import uuid
from dataclasses import dataclass

from src.modules.supplier.domain.entities import Supplier
from src.modules.supplier.domain.interfaces import ISupplierRepository
from src.modules.supplier.domain.value_objects import SupplierType
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CreateSupplierCommand:
    name: str
    type: SupplierType
    region: str


@dataclass(frozen=True)
class CreateSupplierResult:
    supplier_id: uuid.UUID


class CreateSupplierHandler:
    def __init__(
        self,
        supplier_repo: ISupplierRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._supplier_repo = supplier_repo
        self._uow = uow
        self._logger = logger.bind(handler="CreateSupplierHandler")

    async def handle(self, command: CreateSupplierCommand) -> CreateSupplierResult:
        async with self._uow:
            supplier = Supplier.create(
                name=command.name,
                supplier_type=command.type,
                region=command.region,
            )
            await self._supplier_repo.add(supplier)
            self._uow.register_aggregate(supplier)
            await self._uow.commit()

        return CreateSupplierResult(supplier_id=supplier.id)
```

- [ ] **Step 2: Create UpdateSupplierCommand and handler**

```python
# src/modules/supplier/application/commands/update_supplier.py
"""Command handler: update an existing supplier's name and/or region."""

import uuid
from dataclasses import dataclass

from src.modules.supplier.domain.exceptions import SupplierNotFoundError
from src.modules.supplier.domain.interfaces import ISupplierRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateSupplierCommand:
    supplier_id: uuid.UUID
    name: str | None = None
    region: str | None = None


class UpdateSupplierHandler:
    def __init__(
        self,
        supplier_repo: ISupplierRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._supplier_repo = supplier_repo
        self._uow = uow
        self._logger = logger.bind(handler="UpdateSupplierHandler")

    async def handle(self, command: UpdateSupplierCommand) -> None:
        async with self._uow:
            supplier = await self._supplier_repo.get(command.supplier_id)
            if supplier is None:
                raise SupplierNotFoundError(command.supplier_id)

            kwargs = {}
            if command.name is not None:
                kwargs["name"] = command.name
            if command.region is not None:
                kwargs["region"] = command.region

            if kwargs:
                supplier.update(**kwargs)
                await self._supplier_repo.update(supplier)
                self._uow.register_aggregate(supplier)

            await self._uow.commit()
```

- [ ] **Step 3: Create DeactivateSupplierCommand and handler**

```python
# src/modules/supplier/application/commands/deactivate_supplier.py
"""Command handler: deactivate a supplier."""

import uuid
from dataclasses import dataclass

from src.modules.supplier.domain.exceptions import SupplierNotFoundError
from src.modules.supplier.domain.interfaces import ISupplierRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DeactivateSupplierCommand:
    supplier_id: uuid.UUID


class DeactivateSupplierHandler:
    def __init__(
        self,
        supplier_repo: ISupplierRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._supplier_repo = supplier_repo
        self._uow = uow
        self._logger = logger.bind(handler="DeactivateSupplierHandler")

    async def handle(self, command: DeactivateSupplierCommand) -> None:
        async with self._uow:
            supplier = await self._supplier_repo.get(command.supplier_id)
            if supplier is None:
                raise SupplierNotFoundError(command.supplier_id)

            supplier.deactivate()
            await self._supplier_repo.update(supplier)
            self._uow.register_aggregate(supplier)
            await self._uow.commit()
```

- [ ] **Step 4: Create ActivateSupplierCommand and handler**

```python
# src/modules/supplier/application/commands/activate_supplier.py
"""Command handler: reactivate a supplier."""

import uuid
from dataclasses import dataclass

from src.modules.supplier.domain.exceptions import SupplierNotFoundError
from src.modules.supplier.domain.interfaces import ISupplierRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class ActivateSupplierCommand:
    supplier_id: uuid.UUID


class ActivateSupplierHandler:
    def __init__(
        self,
        supplier_repo: ISupplierRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._supplier_repo = supplier_repo
        self._uow = uow
        self._logger = logger.bind(handler="ActivateSupplierHandler")

    async def handle(self, command: ActivateSupplierCommand) -> None:
        async with self._uow:
            supplier = await self._supplier_repo.get(command.supplier_id)
            if supplier is None:
                raise SupplierNotFoundError(command.supplier_id)

            supplier.activate()
            await self._supplier_repo.update(supplier)
            self._uow.register_aggregate(supplier)
            await self._uow.commit()
```

- [ ] **Step 5: Commit**

```bash
git add src/modules/supplier/application/commands/
git commit -m "feat(supplier): add command handlers — create, update, deactivate, activate"
```

---

### Task 5: Supplier application layer — queries and read models

**Files:**

- Create: `src/modules/supplier/application/queries/__init__.py`
- Create: `src/modules/supplier/application/queries/read_models.py`
- Create: `src/modules/supplier/application/queries/get_supplier.py`
- Create: `src/modules/supplier/application/queries/list_suppliers.py`

- [ ] **Step 1: Create read models**

```python
# src/modules/supplier/application/queries/read_models.py
"""Read models (DTOs) for Supplier query handlers."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedReadModel(BaseModel, Generic[T]):
    items: list[T]
    total: int
    offset: int
    limit: int


class SupplierReadModel(BaseModel):
    id: uuid.UUID
    name: str
    type: str
    region: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


SupplierListReadModel = PaginatedReadModel[SupplierReadModel]
```

- [ ] **Step 2: Create GetSupplierHandler**

```python
# src/modules/supplier/application/queries/get_supplier.py
"""Query handler: retrieve a single supplier by ID."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.supplier.application.queries.read_models import SupplierReadModel
from src.modules.supplier.domain.exceptions import SupplierNotFoundError
from src.modules.supplier.infrastructure.models import Supplier as OrmSupplier
from src.shared.interfaces.logger import ILogger


def supplier_orm_to_read_model(orm: OrmSupplier) -> SupplierReadModel:
    return SupplierReadModel(
        id=orm.id,
        name=orm.name,
        type=orm.type.value,
        region=orm.region or "",
        is_active=orm.is_active,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class GetSupplierHandler:
    def __init__(self, session: AsyncSession, logger: ILogger):
        self._session = session
        self._logger = logger.bind(handler="GetSupplierHandler")

    async def handle(self, supplier_id: uuid.UUID) -> SupplierReadModel:
        stmt = select(OrmSupplier).where(OrmSupplier.id == supplier_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            raise SupplierNotFoundError(supplier_id)

        return supplier_orm_to_read_model(orm)
```

- [ ] **Step 3: Create ListSuppliersHandler**

```python
# src/modules/supplier/application/queries/list_suppliers.py
"""Query handler: paginated supplier listing."""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.supplier.application.queries.get_supplier import (
    supplier_orm_to_read_model,
)
from src.modules.supplier.application.queries.read_models import SupplierListReadModel
from src.modules.supplier.infrastructure.models import Supplier as OrmSupplier
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class ListSuppliersQuery:
    offset: int = 0
    limit: int = 50


class ListSuppliersHandler:
    def __init__(self, session: AsyncSession, logger: ILogger):
        self._session = session
        self._logger = logger.bind(handler="ListSuppliersHandler")

    async def handle(self, query: ListSuppliersQuery) -> SupplierListReadModel:
        count_result = await self._session.execute(
            select(func.count()).select_from(OrmSupplier)
        )
        total = count_result.scalar_one()

        stmt = (
            select(OrmSupplier)
            .order_by(OrmSupplier.name)
            .limit(query.limit)
            .offset(query.offset)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        items = [supplier_orm_to_read_model(orm) for orm in rows]
        return SupplierListReadModel(
            items=items, total=total, offset=query.offset, limit=query.limit,
        )
```

- [ ] **Step 4: Commit**

```bash
git add src/modules/supplier/application/queries/
git commit -m "feat(supplier): add query handlers — get, list with read models"
```

---

### Task 6: Supplier presentation layer (router, schemas, DI)

**Files:**

- Create: `src/modules/supplier/presentation/__init__.py`
- Create: `src/modules/supplier/presentation/schemas.py`
- Create: `src/modules/supplier/presentation/router.py`
- Create: `src/modules/supplier/presentation/dependencies.py`

- [ ] **Step 1: Create Pydantic schemas**

```python
# src/modules/supplier/presentation/schemas.py
"""Pydantic request/response schemas for the Supplier API."""

import uuid
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import Field

from src.shared.schemas import CamelModel

S = TypeVar("S")


class PaginatedResponse(CamelModel, Generic[S]):
    items: list[S]
    total: int
    offset: int
    limit: int


class SupplierCreateRequest(CamelModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., pattern=r"^(cross_border|local)$")
    region: str = Field(..., min_length=1, max_length=100)


class SupplierCreateResponse(CamelModel):
    id: uuid.UUID


class SupplierUpdateRequest(CamelModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    region: str | None = Field(None, min_length=1, max_length=100)


class SupplierResponse(CamelModel):
    id: uuid.UUID
    name: str
    type: str
    region: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SupplierListResponse(PaginatedResponse[SupplierResponse]):
    pass
```

- [ ] **Step 2: Create FastAPI router**

```python
# src/modules/supplier/presentation/router.py
"""FastAPI router for Supplier CRUD and lifecycle endpoints."""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, status

from src.modules.supplier.application.commands.activate_supplier import (
    ActivateSupplierCommand,
    ActivateSupplierHandler,
)
from src.modules.supplier.application.commands.create_supplier import (
    CreateSupplierCommand,
    CreateSupplierHandler,
)
from src.modules.supplier.application.commands.deactivate_supplier import (
    DeactivateSupplierCommand,
    DeactivateSupplierHandler,
)
from src.modules.supplier.application.commands.update_supplier import (
    UpdateSupplierCommand,
    UpdateSupplierHandler,
)
from src.modules.supplier.application.queries.get_supplier import GetSupplierHandler
from src.modules.supplier.application.queries.list_suppliers import (
    ListSuppliersHandler,
    ListSuppliersQuery,
)
from src.modules.supplier.domain.value_objects import SupplierType
from src.modules.supplier.presentation.schemas import (
    SupplierCreateRequest,
    SupplierCreateResponse,
    SupplierListResponse,
    SupplierResponse,
    SupplierUpdateRequest,
)
from src.modules.identity.presentation.dependencies import RequirePermission

supplier_router = APIRouter(
    prefix="/suppliers",
    tags=["Suppliers"],
    route_class=DishkaRoute,
)


@supplier_router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=SupplierCreateResponse,
    summary="Create a new supplier",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def create_supplier(
    request: SupplierCreateRequest,
    handler: FromDishka[CreateSupplierHandler],
) -> SupplierCreateResponse:
    command = CreateSupplierCommand(
        name=request.name,
        type=SupplierType(request.type),
        region=request.region,
    )
    result = await handler.handle(command)
    return SupplierCreateResponse(id=result.supplier_id)


@supplier_router.get(
    path="",
    response_model=SupplierListResponse,
    summary="List all suppliers",
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def list_suppliers(
    handler: FromDishka[ListSuppliersHandler],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> SupplierListResponse:
    query = ListSuppliersQuery(offset=offset, limit=limit)
    result = await handler.handle(query)
    return SupplierListResponse(
        items=[
            SupplierResponse(
                id=s.id, name=s.name, type=s.type, region=s.region,
                is_active=s.is_active, created_at=s.created_at, updated_at=s.updated_at,
            )
            for s in result.items
        ],
        total=result.total,
        offset=result.offset,
        limit=result.limit,
    )


@supplier_router.get(
    path="/{supplier_id}",
    response_model=SupplierResponse,
    summary="Get supplier by ID",
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def get_supplier(
    supplier_id: uuid.UUID,
    handler: FromDishka[GetSupplierHandler],
) -> SupplierResponse:
    result = await handler.handle(supplier_id)
    return SupplierResponse(
        id=result.id, name=result.name, type=result.type, region=result.region,
        is_active=result.is_active, created_at=result.created_at, updated_at=result.updated_at,
    )


@supplier_router.put(
    path="/{supplier_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Update supplier name/region",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def update_supplier(
    supplier_id: uuid.UUID,
    request: SupplierUpdateRequest,
    handler: FromDishka[UpdateSupplierHandler],
) -> None:
    command = UpdateSupplierCommand(
        supplier_id=supplier_id,
        name=request.name,
        region=request.region,
    )
    await handler.handle(command)


@supplier_router.patch(
    path="/{supplier_id}/deactivate",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a supplier",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def deactivate_supplier(
    supplier_id: uuid.UUID,
    handler: FromDishka[DeactivateSupplierHandler],
) -> None:
    await handler.handle(DeactivateSupplierCommand(supplier_id=supplier_id))


@supplier_router.patch(
    path="/{supplier_id}/activate",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reactivate a supplier",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def activate_supplier(
    supplier_id: uuid.UUID,
    handler: FromDishka[ActivateSupplierHandler],
) -> None:
    await handler.handle(ActivateSupplierCommand(supplier_id=supplier_id))
```

- [ ] **Step 3: Create Dishka DI provider**

```python
# src/modules/supplier/presentation/dependencies.py
"""Dishka IoC providers for the Supplier bounded context."""

from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource

from src.modules.supplier.application.commands.activate_supplier import (
    ActivateSupplierHandler,
)
from src.modules.supplier.application.commands.create_supplier import (
    CreateSupplierHandler,
)
from src.modules.supplier.application.commands.deactivate_supplier import (
    DeactivateSupplierHandler,
)
from src.modules.supplier.application.commands.update_supplier import (
    UpdateSupplierHandler,
)
from src.modules.supplier.application.queries.get_supplier import GetSupplierHandler
from src.modules.supplier.application.queries.list_suppliers import ListSuppliersHandler
from src.modules.supplier.domain.interfaces import (
    ISupplierQueryService,
    ISupplierRepository,
)
from src.modules.supplier.infrastructure.query_service import SupplierQueryService
from src.modules.supplier.infrastructure.repositories.supplier import SupplierRepository


class SupplierProvider(Provider):
    """DI provider for supplier-related repositories and handlers."""

    # Repository
    supplier_repo: CompositeDependencySource = provide(
        SupplierRepository, scope=Scope.REQUEST, provides=ISupplierRepository
    )

    # Cross-module query service
    supplier_query_service: CompositeDependencySource = provide(
        SupplierQueryService, scope=Scope.REQUEST, provides=ISupplierQueryService
    )

    # Command handlers
    create_supplier_handler: CompositeDependencySource = provide(
        CreateSupplierHandler, scope=Scope.REQUEST
    )
    update_supplier_handler: CompositeDependencySource = provide(
        UpdateSupplierHandler, scope=Scope.REQUEST
    )
    deactivate_supplier_handler: CompositeDependencySource = provide(
        DeactivateSupplierHandler, scope=Scope.REQUEST
    )
    activate_supplier_handler: CompositeDependencySource = provide(
        ActivateSupplierHandler, scope=Scope.REQUEST
    )

    # Query handlers
    get_supplier_handler: CompositeDependencySource = provide(
        GetSupplierHandler, scope=Scope.REQUEST
    )
    list_suppliers_handler: CompositeDependencySource = provide(
        ListSuppliersHandler, scope=Scope.REQUEST
    )
```

- [ ] **Step 4: Commit**

```bash
git add src/modules/supplier/presentation/
git commit -m "feat(supplier): add presentation layer — router, schemas, DI provider"
```

---

### Task 7: Wire module into bootstrap (container, router, registry)

**Files:**

- Modify: `src/bootstrap/container.py`
- Modify: `src/api/router.py`
- Modify: `src/infrastructure/database/registry.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Add SupplierProvider to container**

In `src/bootstrap/container.py`, add the import and provider:

```python
# Add import
from src.modules.supplier.presentation.dependencies import SupplierProvider

# Add to make_async_container call (after ProductProvider)
SupplierProvider(),
```

- [ ] **Step 2: Add supplier_router to API router**

In `src/api/router.py`, add:

```python
# Add import
from src.modules.supplier.presentation.router import supplier_router

# Mount with no additional prefix — the router already has prefix="/suppliers"
# Final path: /api/v1/suppliers (same pattern as identity/geo routers)
router.include_router(supplier_router)
```

- [ ] **Step 3: Update ORM registry**

In `src/infrastructure/database/registry.py`, change the Supplier import from catalog to supplier module:

```python
# Remove from the catalog imports block:
#     Supplier,

# Add new import:
from src.modules.supplier.infrastructure.models import Supplier
```

Keep `"Supplier"` in `__all__`.

- [ ] **Step 4: Add SupplierProvider to test container**

In `tests/conftest.py`, add the SupplierProvider to the `app_container` fixture:

```python
from src.modules.supplier.presentation.dependencies import SupplierProvider

# In the make_async_container call, add:
SupplierProvider(),
```

- [ ] **Step 5: Commit**

```bash
git add src/bootstrap/container.py src/api/router.py src/infrastructure/database/registry.py tests/conftest.py
git commit -m "feat(supplier): wire module into bootstrap — container, router, registry, test container"
```

---

### Task 8: Cross-module supplier validation in catalog

**Files:**

- Modify: `src/modules/catalog/application/commands/create_product.py`

- [ ] **Step 1: Add ISupplierQueryService to CreateProductHandler**

In `src/modules/catalog/application/commands/create_product.py`:

1. Add import:

```python
from src.modules.supplier.domain.interfaces import ISupplierQueryService
```

2. Add `supplier_query_service` to constructor:

```python
def __init__(
    self,
    product_repo: IProductRepository,
    brand_repo: IBrandRepository,
    category_repo: ICategoryRepository,
    supplier_query_service: ISupplierQueryService,
    uow: IUnitOfWork,
    logger: ILogger,
) -> None:
    # ... existing assignments ...
    self._supplier_query_service = supplier_query_service
```

3. Add supplier validation in `handle()`, after category validation and before `Product.create()`:

```python
# Validate supplier exists and is active
if command.supplier_id is not None:
    await self._supplier_query_service.assert_supplier_active(command.supplier_id)
```

- [ ] **Step 2: Verify existing product creation tests still pass**

Run: `pytest tests/integration/modules/catalog/ -v -k product`
Expected: Existing tests PASS (supplier_id is still optional)

- [ ] **Step 3: Commit**

```bash
git add src/modules/catalog/application/commands/create_product.py
git commit -m "feat(catalog): validate supplier active status during product creation"
```

---

### Task 9: Surface source_url on Product

**Files:**

- Modify: `src/modules/catalog/domain/entities.py` — add `source_url` to Product entity
- Modify: `src/modules/catalog/application/commands/create_product.py` — add `source_url` to command
- Modify: `src/modules/catalog/presentation/schemas.py` — add `source_url` to request/response
- Modify: `src/modules/catalog/application/queries/read_models.py` — add `source_url` to ProductReadModel

- [ ] **Step 1: Add source_url to Product domain entity**

In `src/modules/catalog/domain/entities.py`, in the `Product` class, add the field after `supplier_id`:

```python
source_url: str | None = None
```

Add `"source_url"` to `_UPDATABLE_FIELDS` if such a set exists, or add it to the `create()` factory:

```python
@classmethod
def create(
    cls,
    *,
    slug: str,
    title_i18n: dict[str, str],
    brand_id: uuid.UUID,
    primary_category_id: uuid.UUID,
    description_i18n: dict[str, str] | None = None,
    supplier_id: uuid.UUID | None = None,
    source_url: str | None = None,
    country_of_origin: str | None = None,
    tags: list[str] | None = None,
    product_id: uuid.UUID | None = None,
) -> Product:
```

Pass `source_url=source_url` through to the constructor.

- [ ] **Step 2: Add source_url to CreateProductCommand**

In `src/modules/catalog/application/commands/create_product.py`, add to the command:

```python
source_url: str | None = None
```

Pass it through to `Product.create()`:

```python
source_url=command.source_url,
```

Add top-level imports at the file header:

```python
from src.modules.supplier.domain.interfaces import ISupplierQueryService, SupplierInfo
from src.modules.supplier.domain.value_objects import SupplierType
from src.modules.supplier.domain.exceptions import SourceUrlRequiredError
```

Add cross-border validation after the supplier check:

```python
if command.supplier_id is not None:
    supplier_info = await self._supplier_query_service.assert_supplier_active(command.supplier_id)

    # Cross-border suppliers require source_url
    if supplier_info.type == SupplierType.CROSS_BORDER and not command.source_url:
        raise SourceUrlRequiredError()
```

- [ ] **Step 3: Add source_url to presentation schemas**

In `src/modules/catalog/presentation/schemas.py`, add to `ProductCreateRequest`:

```python
source_url: str | None = Field(None, max_length=1024)
```

Add to `ProductResponse` (or wherever product details are returned):

```python
source_url: str | None = None
```

- [ ] **Step 4: Add source_url to ProductReadModel**

In `src/modules/catalog/application/queries/read_models.py`, add to `ProductReadModel`:

```python
source_url: str | None = None
```

Update any ORM-to-read-model mapping functions to include `source_url=orm.source_url`.

- [ ] **Step 5: Commit**

```bash
git add src/modules/catalog/
git commit -m "feat(catalog): surface source_url on Product — domain, command, schema, read model"
```

---

### Task 10: Alembic migration

**Files:**

- Create: `alembic/versions/xxxx_add_supplier_is_active_version_and_seed.py`

- [ ] **Step 1: Generate migration**

Run: `alembic revision --autogenerate -m "add supplier is_active, version columns and seed marketplaces"`

This should detect:

- `is_active` column added to `suppliers` table
- `version` column added to `suppliers` table

- [ ] **Step 2: Add marketplace seed data to migration**

Edit the generated migration's `upgrade()` to add marketplace seeding after the column additions:

```python
from src.modules.supplier.domain.constants import MARKETPLACE_SUPPLIERS

def upgrade() -> None:
    # Auto-generated column additions
    op.add_column("suppliers", sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False))
    op.add_column("suppliers", sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False))

    # Seed marketplace suppliers (idempotent — uses ON CONFLICT DO NOTHING)
    for s in MARKETPLACE_SUPPLIERS:
        op.execute(
            sa.text(
                "INSERT INTO suppliers (id, name, type, region, is_active, version) "
                "VALUES (:id, :name, :type, :region, true, 1) "
                "ON CONFLICT (id) DO NOTHING"
            ).bindparams(
                id=str(s["id"]),
                name=s["name"],
                type=s["type"].value,
                region=s["region"],
            )
        )
```

- [ ] **Step 3: Verify migration runs**

Run: `alembic upgrade head`
Expected: Migration applies without errors.

- [ ] **Step 4: Verify migration is idempotent**

Run: `alembic downgrade -1 && alembic upgrade head`
Expected: Clean up and re-apply without errors.

- [ ] **Step 5: Commit**

```bash
git add alembic/
git commit -m "feat(supplier): add migration — is_active, version columns, marketplace seed"
```

---

### Task 11: Integration tests

**Files:**

- Create: `tests/integration/modules/supplier/test_supplier_crud.py`
- Create: `tests/integration/modules/supplier/test_supplier_lifecycle.py`
- Create: `tests/integration/modules/supplier/test_cross_module.py`

- [ ] **Step 1: Write CRUD integration tests**

```python
# tests/integration/modules/supplier/test_supplier_crud.py
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.supplier.domain.entities import Supplier
from src.modules.supplier.domain.value_objects import SupplierType
from src.modules.supplier.infrastructure.repositories.supplier import SupplierRepository
from src.modules.supplier.infrastructure.query_service import SupplierQueryService


async def test_create_local_supplier(db_session: AsyncSession):
    repo = SupplierRepository(session=db_session)
    supplier = Supplier.create(
        name="Moscow Store", supplier_type=SupplierType.LOCAL, region="Moscow",
    )
    result = await repo.add(supplier)
    assert result.id == supplier.id
    assert result.is_active is True


async def test_create_cross_border_supplier(db_session: AsyncSession):
    repo = SupplierRepository(session=db_session)
    supplier = Supplier.create(
        name="Poizon", supplier_type=SupplierType.CROSS_BORDER, region="China",
    )
    result = await repo.add(supplier)
    assert result.type == SupplierType.CROSS_BORDER


async def test_update_supplier_name(db_session: AsyncSession):
    repo = SupplierRepository(session=db_session)
    supplier = Supplier.create(
        name="Old Name", supplier_type=SupplierType.LOCAL, region="Moscow",
    )
    await repo.add(supplier)
    supplier.update(name="New Name")
    updated = await repo.update(supplier)
    assert updated.name == "New Name"


async def test_query_service_get_info(db_session: AsyncSession):
    repo = SupplierRepository(session=db_session)
    query_svc = SupplierQueryService(session=db_session)
    supplier = Supplier.create(
        name="Test", supplier_type=SupplierType.LOCAL, region="Moscow",
    )
    await repo.add(supplier)

    info = await query_svc.get_supplier_info(supplier.id)
    assert info is not None
    assert info.name == "Test"
    assert info.is_active is True
```

- [ ] **Step 2: Write lifecycle tests**

```python
# tests/integration/modules/supplier/test_supplier_lifecycle.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.supplier.domain.entities import Supplier
from src.modules.supplier.domain.exceptions import (
    SupplierInactiveError,
    SupplierNotFoundError,
)
from src.modules.supplier.domain.value_objects import SupplierType
from src.modules.supplier.infrastructure.query_service import SupplierQueryService
from src.modules.supplier.infrastructure.repositories.supplier import SupplierRepository


async def test_deactivate_supplier(db_session: AsyncSession):
    repo = SupplierRepository(session=db_session)
    supplier = Supplier.create(
        name="To Deactivate", supplier_type=SupplierType.LOCAL, region="Moscow",
    )
    await repo.add(supplier)
    supplier.deactivate()
    updated = await repo.update(supplier)
    assert updated.is_active is False


async def test_assert_active_raises_for_inactive(db_session: AsyncSession):
    repo = SupplierRepository(session=db_session)
    query_svc = SupplierQueryService(session=db_session)
    supplier = Supplier.create(
        name="Inactive", supplier_type=SupplierType.LOCAL, region="Moscow",
    )
    await repo.add(supplier)
    supplier.deactivate()
    await repo.update(supplier)

    with pytest.raises(SupplierInactiveError):
        await query_svc.assert_supplier_active(supplier.id)


async def test_assert_active_raises_for_nonexistent(db_session: AsyncSession):
    import uuid
    query_svc = SupplierQueryService(session=db_session)

    with pytest.raises(SupplierNotFoundError):
        await query_svc.assert_supplier_active(uuid.uuid4())
```

- [ ] **Step 3: Run all tests**

Run: `pytest tests/ -v --tb=short`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/integration/modules/supplier/
git commit -m "test(supplier): add integration tests — CRUD, lifecycle, cross-module query service"
```

---

### Task 12: Final verification

- [ ] **Step 1: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Verify import integrity**

Run: `python -c "from src.bootstrap.web import create_app; print('App factory OK')"`
Expected: No import errors

- [ ] **Step 3: Verify endpoints are registered**

Start the app (if possible) or check OpenAPI schema generation:

```bash
python -c "
from src.bootstrap.web import create_app
app = create_app()
routes = [r.path for r in app.routes]
assert '/api/v1/suppliers' in str(routes) or any('/suppliers' in str(r.path) for r in app.routes)
print('Supplier routes registered')
"
```

- [ ] **Step 4: Review checklist**

Verify against PRD acceptance criteria:

- [ ] POST /api/v1/suppliers creates a supplier with UUIDv7, is_active=true
- [ ] GET /api/v1/suppliers returns paginated list
- [ ] GET /api/v1/suppliers/{id} returns supplier detail
- [ ] PUT /api/v1/suppliers/{id} updates name/region
- [ ] PATCH /api/v1/suppliers/{id}/deactivate sets is_active=false
- [ ] PATCH /api/v1/suppliers/{id}/activate sets is_active=true
- [ ] Deactivated supplier blocks new product assignment
- [ ] Type is immutable after creation
- [ ] source_url required for CROSS_BORDER supplier products
- [ ] Four marketplace suppliers seeded with fixed UUIDs
- [ ] All responses use camelCase field names
- [ ] Supplier module has zero references to catalog internals
