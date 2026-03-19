# Architecture Plan -- MT-22: Add Product attribute router

> **Pipeline run:** 20260318-121109
> **Micro-task:** MT-22
> **Layer:** Presentation
> **Module:** catalog
> **FR Reference:** FR-003
> **Depends on:** MT-14, MT-15, MT-19

---

## Research findings

Skipped -- the codebase already has 7 routers following the exact same FastAPI + DishkaRoute + FromDishka pattern. No new library APIs are involved. The existing `router_attributes.py` and `router_attribute_values.py` serve as precise templates.

---

## Design decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Router prefix | `/products/{product_id}/attributes` | MT spec requires nesting under product; matches REST resource hierarchy |
| DishkaRoute vs @inject | `DishkaRoute` (route_class) | All existing routers use `route_class=DishkaRoute`, not `@inject` decorator |
| Response for POST | 201 with `ProductAttributeAssignResponse` | Matches existing pattern (e.g., `AttributeValueCreateResponse` returns ID) |
| Response for GET list | 200 with `list[ProductAttributeResponse]` | Simple list (no pagination needed -- a product has a bounded number of attributes) |
| Response for DELETE | 204 No Content, return None | Matches existing `delete_attribute` pattern |
| Permission guard | `catalog:manage` | All mutating catalog endpoints use this permission |
| GET requires auth? | No permission guard (read-only) | Follows existing pattern -- list/get endpoints have no permission dependency |

---

## File plan

### `src/modules/catalog/presentation/router_product_attributes.py` -- CREATE

**Purpose:** FastAPI router for product-level attribute assignment CRUD (assign, list, remove).
**Layer:** Presentation

#### Router instance:

**`product_attribute_router`** (new)
- Type: `APIRouter`
- prefix: `"/products/{product_id}/attributes"`
- tags: `["Product Attributes"]`
- route_class: `DishkaRoute`

#### Route functions:

**`assign_product_attribute`** (new)
- Decorator: `@product_attribute_router.post(path="", status_code=status.HTTP_201_CREATED, response_model=ProductAttributeAssignResponse, summary="Assign an attribute value to a product", dependencies=[Depends(RequirePermission(codename="catalog:manage"))])`
- Signature: `async def assign_product_attribute(product_id: uuid.UUID, request: ProductAttributeAssignRequest, handler: FromDishka[AssignProductAttributeHandler]) -> ProductAttributeAssignResponse`
- Body:
  1. Build `AssignProductAttributeCommand(product_id=product_id, attribute_id=request.attribute_id, attribute_value_id=request.attribute_value_id)`
  2. Call `result = await handler.handle(command)`
  3. Return `ProductAttributeAssignResponse(id=result.pav_id, message="Attribute assigned to product")`

**`list_product_attributes`** (new)
- Decorator: `@product_attribute_router.get(path="", status_code=status.HTTP_200_OK, response_model=list[ProductAttributeResponse], summary="List attribute assignments for a product")`
- Signature: `async def list_product_attributes(product_id: uuid.UUID, handler: FromDishka[ListProductAttributesHandler]) -> list[ProductAttributeResponse]`
- Body:
  1. Build `ListProductAttributesQuery(product_id=product_id)`
  2. Call `items = await handler.handle(query)`
  3. Return `[ProductAttributeResponse(id=item.id, product_id=item.product_id, attribute_id=item.attribute_id, attribute_value_id=item.attribute_value_id) for item in items]`

**`remove_product_attribute`** (new)
- Decorator: `@product_attribute_router.delete(path="/{attribute_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove an attribute assignment from a product", dependencies=[Depends(RequirePermission(codename="catalog:manage"))])`
- Signature: `async def remove_product_attribute(product_id: uuid.UUID, attribute_id: uuid.UUID, handler: FromDishka[RemoveProductAttributeHandler]) -> None`
- Body:
  1. Build `RemoveProductAttributeCommand(product_id=product_id, attribute_id=attribute_id)`
  2. Call `await handler.handle(command)`
  3. Return None (204 implicit)

#### Imports:

```python
"""
FastAPI router for Product attribute assignment endpoints.

Nested under ``/catalog/products/{product_id}/attributes``.
All mutating endpoints require the ``catalog:manage`` permission.
Delegates to application-layer command/query handlers via Dishka DI.
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, status

from src.modules.catalog.application.commands.assign_product_attribute import (
    AssignProductAttributeCommand,
    AssignProductAttributeHandler,
    AssignProductAttributeResult,
)
from src.modules.catalog.application.commands.remove_product_attribute import (
    RemoveProductAttributeCommand,
    RemoveProductAttributeHandler,
)
from src.modules.catalog.application.queries.list_product_attributes import (
    ListProductAttributesHandler,
    ListProductAttributesQuery,
)
from src.modules.catalog.application.queries.read_models import (
    ProductAttributeValueReadModel,
)
from src.modules.catalog.presentation.schemas import (
    ProductAttributeAssignRequest,
    ProductAttributeAssignResponse,
    ProductAttributeResponse,
)
from src.modules.identity.presentation.dependencies import RequirePermission
```

#### Structural sketch (pseudo-code only):

```python
product_attribute_router = APIRouter(
    prefix="/products/{product_id}/attributes",
    tags=["Product Attributes"],
    route_class=DishkaRoute,
)


@product_attribute_router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=ProductAttributeAssignResponse,
    summary="Assign an attribute value to a product",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def assign_product_attribute(
    product_id: uuid.UUID,
    request: ProductAttributeAssignRequest,
    handler: FromDishka[AssignProductAttributeHandler],
) -> ProductAttributeAssignResponse:
    command = AssignProductAttributeCommand(
        product_id=product_id,
        attribute_id=request.attribute_id,
        attribute_value_id=request.attribute_value_id,
    )
    result: AssignProductAttributeResult = await handler.handle(command)
    return ProductAttributeAssignResponse(id=result.pav_id, message="Attribute assigned to product")


@product_attribute_router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=list[ProductAttributeResponse],
    summary="List attribute assignments for a product",
)
async def list_product_attributes(
    product_id: uuid.UUID,
    handler: FromDishka[ListProductAttributesHandler],
) -> list[ProductAttributeResponse]:
    query = ListProductAttributesQuery(product_id=product_id)
    items: list[ProductAttributeValueReadModel] = await handler.handle(query)
    return [
        ProductAttributeResponse(
            id=item.id,
            product_id=item.product_id,
            attribute_id=item.attribute_id,
            attribute_value_id=item.attribute_value_id,
        )
        for item in items
    ]


@product_attribute_router.delete(
    path="/{attribute_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an attribute assignment from a product",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def remove_product_attribute(
    product_id: uuid.UUID,
    attribute_id: uuid.UUID,
    handler: FromDishka[RemoveProductAttributeHandler],
) -> None:
    command = RemoveProductAttributeCommand(
        product_id=product_id,
        attribute_id=attribute_id,
    )
    await handler.handle(command)
```

---

## Dependency registration

No DI changes required for this micro-task. Handler and repository DI registration is handled in MT-23 (ProductProvider).

## Migration plan

No database changes required for this micro-task.

## Integration points

No cross-module integration in this micro-task. The router only imports from:
- `src.modules.catalog.application` (same module, application layer -- allowed by Presentation -> Application rule)
- `src.modules.catalog.presentation.schemas` (same module, same layer)
- `src.modules.identity.presentation.dependencies` (only `RequirePermission` -- this is a shared auth dependency, same pattern used by all other catalog routers)

## Risks & edge cases

| Risk | Impact | Mitigation |
|------|--------|------------|
| `AssignProductAttributeResult` uses `pav_id` not `id` | Schema mismatch if backend maps wrong field | Plan explicitly maps `result.pav_id` to response `id` field |
| Router not mounted until MT-23 | Router exists but is unreachable until DI + router wiring | Expected -- MT-23 handles mounting in `router.py` and DI registration |
| `ListProductAttributesHandler` currently returns empty list | GET endpoint always returns `[]` until MT-16 ORM model is wired | Known stub behavior documented in the handler; no action needed here |

## Acceptance verification

How senior-backend should verify this MT is correctly implemented:

```bash
uv run ruff check .
uv run ruff format .
uv run mypy .
uv run pytest tests/unit/ tests/architecture/ -v
```

**Specific checks:**

- [ ] POST /products/{product_id}/attributes route exists with status 201
- [ ] GET /products/{product_id}/attributes route exists with status 200
- [ ] DELETE /products/{product_id}/attributes/{attribute_id} route exists with status 204
- [ ] All routes use `DishkaRoute` (via `route_class` on router, NOT `@inject` decorator)
- [ ] `FromDishka` used for handler injection in function signatures
- [ ] POST and DELETE have `RequirePermission(codename="catalog:manage")` dependency
- [ ] GET has no permission guard (read-only)
- [ ] Router variable is named `product_attribute_router`
- [ ] Module docstring present with Google-style documentation
- [ ] No domain layer imports (no entities, no value objects used directly)
- [ ] Pydantic schemas used only for request/response (presentation layer)
- [ ] Linter/type-checker passes
- [ ] All existing tests pass
