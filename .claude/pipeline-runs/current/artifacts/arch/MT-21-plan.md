# Architecture Plan -- MT-21: Add SKU router

> **Pipeline run:** 20260318-121109
> **Micro-task:** MT-21
> **Layer:** Presentation
> **Module:** catalog
> **FR Reference:** FR-001, FR-004, FR-006
> **Depends on:** MT-11, MT-12, MT-13, MT-15, MT-19

---

## Research findings

Skipped -- existing codebase has multiple router examples (`router_attributes.py`, `router_attribute_values.py`) using the exact same DishkaRoute + FromDishka + RequirePermission pattern. No new library APIs involved.

---

## Design decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Router prefix | `/products/{product_id}/skus` | MT spec requires nested routes under products |
| HTTP method for update | PUT (not PATCH) | MT spec explicitly says "PUT /products/{product_id}/skus/{sku_id}" |
| Response for create | 201 with `SKUCreateResponse` | Matches existing pattern (e.g., `AttributeCreateResponse`) |
| Response for delete | 204 No Content | MT spec requires soft-delete returns 204 |
| Response for list | 200 with `list[SKUResponse]` | Returns flat list (no pagination) -- `ListSKUsHandler` returns `list[SKUReadModel]`, not paginated |
| Response for update | 200 with `SKUResponse` | After update, fetch updated data via `ListSKUsHandler` and find the SKU |
| Permission guard | `catalog:manage` on all mutating endpoints | Matches existing attribute/brand router pattern; GET is public |
| Sentinel handling for compare_at_price | Check `request.compare_at_price_amount is not ...` | `SKUUpdateRequest` uses `...` sentinel for nullable field, must propagate correctly to `UpdateSKUCommand._SENTINEL` |

---

## File plan

### `src/modules/catalog/presentation/router_skus.py` -- CREATE

**Purpose:** FastAPI router for SKU (variant) CRUD endpoints nested under `/products/{product_id}/skus`.
**Layer:** Presentation

#### Functions:

**`create_sku`** (new) -- POST endpoint
- Path: `""` (empty, prefix handles `/products/{product_id}/skus`)
- Status code: 201
- Response model: `SKUCreateResponse`
- Dependencies: `RequirePermission(codename="catalog:manage")`
- Parameters:
  - `product_id: uuid.UUID` (path)
  - `request: SKUCreateRequest` (body)
  - `handler: FromDishka[AddSKUHandler]`
- Logic:
  1. Build `AddSKUCommand` from request fields:
     - `product_id=product_id`
     - `sku_code=request.sku_code`
     - `price_amount=request.price_amount`
     - `price_currency=request.price_currency`
     - `compare_at_price_amount=request.compare_at_price_amount`
     - `is_active=request.is_active`
     - `variant_attributes=[(pair.attribute_id, pair.attribute_value_id) for pair in request.variant_attributes]`
  2. Call `await handler.handle(command)`
  3. Return `SKUCreateResponse(id=result.sku_id, message="SKU created")`

**`list_skus`** (new) -- GET endpoint
- Path: `""`
- Status code: 200
- Response model: `list[SKUResponse]`
- Parameters:
  - `product_id: uuid.UUID` (path)
  - `handler: FromDishka[ListSKUsHandler]`
- Logic:
  1. Build `ListSKUsQuery(product_id=product_id)`
  2. Call `await handler.handle(query)`
  3. Map each `SKUReadModel` to `SKUResponse` using helper function `_to_sku_response`
  4. Return the list

**`update_sku`** (new) -- PUT endpoint
- Path: `"/{sku_id}"`
- Status code: 200
- Response model: `SKUResponse`
- Dependencies: `RequirePermission(codename="catalog:manage")`
- Parameters:
  - `product_id: uuid.UUID` (path)
  - `sku_id: uuid.UUID` (path)
  - `request: SKUUpdateRequest` (body)
  - `update_handler: FromDishka[UpdateSKUHandler]`
  - `list_handler: FromDishka[ListSKUsHandler]`
- Logic:
  1. Build `UpdateSKUCommand`:
     - `product_id=product_id`
     - `sku_id=sku_id`
     - `sku_code=request.sku_code`
     - `price_amount=request.price_amount`
     - `price_currency=request.price_currency`
     - For `compare_at_price_amount`: if `request.compare_at_price_amount is not ...` then pass the value (could be `None` or `int`), else pass `_SENTINEL` from the update_sku module
     - `is_active=request.is_active`
     - `variant_attributes=[(p.attribute_id, p.attribute_value_id) for p in request.variant_attributes] if request.variant_attributes is not None else None`
     - `version=request.version`
  2. Call `await update_handler.handle(command)`
  3. Fetch updated SKUs via `await list_handler.handle(ListSKUsQuery(product_id=product_id))`
  4. Find the updated SKU in the list by `result.id`
  5. Return `_to_sku_response(sku_read_model)`

**`delete_sku`** (new) -- DELETE endpoint
- Path: `"/{sku_id}"`
- Status code: 204
- Response model: None
- Dependencies: `RequirePermission(codename="catalog:manage")`
- Parameters:
  - `product_id: uuid.UUID` (path)
  - `sku_id: uuid.UUID` (path)
  - `handler: FromDishka[DeleteSKUHandler]`
- Logic:
  1. Build `DeleteSKUCommand(product_id=product_id, sku_id=sku_id)`
  2. Call `await handler.handle(command)`
  3. Return `None`

**`_to_sku_response`** (new) -- private helper function
- Signature: `def _to_sku_response(model: SKUReadModel) -> SKUResponse`
- Logic: Maps `SKUReadModel` fields to `SKUResponse` fields:
  - `id=model.id`
  - `product_id=model.product_id`
  - `sku_code=model.sku_code`
  - `variant_hash=model.variant_hash`
  - `price=MoneySchema(amount=model.price.amount, currency=model.price.currency)`
  - `compare_at_price=MoneySchema(amount=model.compare_at_price.amount, currency=model.compare_at_price.currency) if model.compare_at_price is not None else None`
  - `is_active=model.is_active`
  - `version=model.version`
  - `deleted_at=model.deleted_at`
  - `created_at=model.created_at`
  - `updated_at=model.updated_at`
  - `variant_attributes=[VariantAttributePairSchema(attribute_id=va.attribute_id, attribute_value_id=va.attribute_value_id) for va in model.variant_attributes]`

#### Router instantiation:

```python
sku_router = APIRouter(
    prefix="/products/{product_id}/skus",
    tags=["SKUs"],
    route_class=DishkaRoute,
)
```

#### Imports:

```python
"""
FastAPI router for SKU (variant) CRUD endpoints.

All mutating endpoints require the ``catalog:manage`` permission.
Delegates to application-layer command/query handlers via Dishka DI.
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, status

from src.modules.catalog.application.commands.add_sku import (
    AddSKUCommand,
    AddSKUHandler,
    AddSKUResult,
)
from src.modules.catalog.application.commands.delete_sku import (
    DeleteSKUCommand,
    DeleteSKUHandler,
)
from src.modules.catalog.application.commands.update_sku import (
    UpdateSKUCommand,
    UpdateSKUHandler,
    UpdateSKUResult,
    _SENTINEL,
)
from src.modules.catalog.application.queries.list_skus import (
    ListSKUsHandler,
    ListSKUsQuery,
)
from src.modules.catalog.application.queries.read_models import SKUReadModel
from src.modules.catalog.presentation.schemas import (
    MoneySchema,
    SKUCreateRequest,
    SKUCreateResponse,
    SKUResponse,
    SKUUpdateRequest,
    VariantAttributePairSchema,
)
from src.modules.identity.presentation.dependencies import RequirePermission
```

#### Structural sketch (pseudo-code only):

```python
sku_router = APIRouter(
    prefix="/products/{product_id}/skus",
    tags=["SKUs"],
    route_class=DishkaRoute,
)


@sku_router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=SKUCreateResponse,
    summary="Add a SKU variant to a product",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def create_sku(
    product_id: uuid.UUID,
    request: SKUCreateRequest,
    handler: FromDishka[AddSKUHandler],
) -> SKUCreateResponse:
    # build AddSKUCommand, call handler.handle, return SKUCreateResponse
    ...


@sku_router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=list[SKUResponse],
    summary="List SKU variants for a product",
)
async def list_skus(
    product_id: uuid.UUID,
    handler: FromDishka[ListSKUsHandler],
) -> list[SKUResponse]:
    # build ListSKUsQuery, call handler.handle, map to SKUResponse list
    ...


@sku_router.put(
    path="/{sku_id}",
    status_code=status.HTTP_200_OK,
    response_model=SKUResponse,
    summary="Update a SKU variant",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def update_sku(
    product_id: uuid.UUID,
    sku_id: uuid.UUID,
    request: SKUUpdateRequest,
    update_handler: FromDishka[UpdateSKUHandler],
    list_handler: FromDishka[ListSKUsHandler],
) -> SKUResponse:
    # build UpdateSKUCommand, call update_handler.handle
    # then fetch via list_handler and find by result.id
    ...


@sku_router.delete(
    path="/{sku_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a SKU variant",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def delete_sku(
    product_id: uuid.UUID,
    sku_id: uuid.UUID,
    handler: FromDishka[DeleteSKUHandler],
) -> None:
    # build DeleteSKUCommand, call handler.handle
    ...


def _to_sku_response(model: SKUReadModel) -> SKUResponse:
    # map all fields from read model to response schema
    ...
```

---

## Dependency registration

No DI changes required for this micro-task. The `AddSKUHandler`, `UpdateSKUHandler`, `DeleteSKUHandler`, and `ListSKUsHandler` registrations are handled in MT-23 (DI wiring). The router export (`sku_router`) will be mounted in `src/api/router.py` also in MT-23.

**IMPORTANT for MT-23 (not this MT):** The `sku_router` must be mounted in `src/api/router.py` as:
```python
from src.modules.catalog.presentation.router_skus import sku_router
router.include_router(sku_router, prefix="/catalog")
```
This produces the final path: `/api/v1/catalog/products/{product_id}/skus`.

---

## Migration plan

No database changes required for this micro-task.

---

## Integration points

No cross-module integration in this micro-task. The router only calls catalog-internal handlers.

---

## Risks & edge cases

| Risk | Impact | Mitigation |
|------|--------|------------|
| Importing `_SENTINEL` from `update_sku` module -- underscore-prefixed name | Ruff may warn about importing private names | This is intentional; the sentinel must match the exact object used in `UpdateSKUHandler`. Add `# noqa: PLC2701` if ruff complains, OR alternative: check `request.compare_at_price_amount is not ...` (the Pydantic `...` sentinel) and conditionally pass `_SENTINEL` or the actual value. The safer approach is to check against `...` (Ellipsis) since that is what Pydantic uses as the default in `SKUUpdateRequest`. If `request.compare_at_price_amount is ...` then do NOT pass `compare_at_price_amount` kwarg at all (use `**kwargs` dict pattern). If it is not `...`, pass the actual value (None or int). This avoids importing `_SENTINEL`. **Use this approach.** |
| `ListSKUsHandler` returns deleted SKUs too | After update, finding SKU by ID in the list may fail if handler filters | Check `list_skus.py` -- it does NOT filter by `deleted_at`. No issue. |
| `SKUReadModel` missing `created_at`/`updated_at` | Response mapping would fail | Verified: `SKUReadModel` has `created_at` and `updated_at` fields. No issue. |

**Revised sentinel handling for update_sku endpoint (CRITICAL):**

Do NOT import `_SENTINEL` from `update_sku` module. Instead, build the `UpdateSKUCommand` using a kwargs dict:

```python
# In update_sku endpoint:
cmd_kwargs: dict[str, object] = {
    "product_id": product_id,
    "sku_id": sku_id,
    "sku_code": request.sku_code,
    "price_amount": request.price_amount,
    "price_currency": request.price_currency,
    "is_active": request.is_active,
    "version": request.version,
}

# Only pass compare_at_price_amount if the client actually sent a value
# (distinguishing "not sent" from "explicitly null")
if request.compare_at_price_amount is not ...:
    cmd_kwargs["compare_at_price_amount"] = request.compare_at_price_amount

# Only pass variant_attributes if provided
if request.variant_attributes is not None:
    cmd_kwargs["variant_attributes"] = [
        (p.attribute_id, p.attribute_value_id) for p in request.variant_attributes
    ]

command = UpdateSKUCommand(**cmd_kwargs)  # type: ignore[arg-type]
```

This way `UpdateSKUCommand.compare_at_price_amount` defaults to `_SENTINEL` when not passed, which is the correct behavior.

**Updated imports (remove `_SENTINEL` import):**

```python
from src.modules.catalog.application.commands.update_sku import (
    UpdateSKUCommand,
    UpdateSKUHandler,
    UpdateSKUResult,
)
```

---

## Acceptance verification

How senior-backend should verify this MT is correctly implemented:

```bash
uv run ruff check .
uv run ruff format .
uv run mypy .
uv run pytest tests/unit/ tests/architecture/ -v
```

**Specific checks:**

- [ ] POST `/products/{product_id}/skus` returns 201 with `SKUCreateResponse`
- [ ] GET `/products/{product_id}/skus` returns 200 with `list[SKUResponse]`
- [ ] PUT `/products/{product_id}/skus/{sku_id}` returns 200 with `SKUResponse`
- [ ] DELETE `/products/{product_id}/skus/{sku_id}` returns 204
- [ ] All routes use `DishkaRoute` + `FromDishka` for handler injection
- [ ] Mutating endpoints (POST, PUT, DELETE) require `catalog:manage` permission
- [ ] GET endpoint has no permission dependency (public read)
- [ ] `_to_sku_response` helper correctly maps all fields including nested `MoneySchema` and `variant_attributes`
- [ ] No import of `_SENTINEL` -- sentinel handling uses Pydantic `...` (Ellipsis) check pattern
- [ ] Domain layer has zero framework imports (this file is presentation-only)
- [ ] Pydantic only in presentation layer (confirmed -- schemas.py)
- [ ] `uv run pytest tests/unit/ tests/architecture/ -v` passes
- [ ] Linter/type-checker passes
