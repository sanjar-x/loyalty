# Architecture Plan -- MT-20: Add Product router (CRUD + status)

> **Pipeline run:** 20260318-121109
> **Micro-task:** MT-20
> **Layer:** Presentation
> **Module:** catalog
> **FR Reference:** FR-001, FR-002, FR-005
> **Depends on:** MT-7, MT-8, MT-9, MT-10, MT-15, MT-19

---

## Research findings

Skipped -- FastAPI APIRouter patterns are well-established in this codebase (`router_attributes.py`, `router_attribute_values.py`). No new library APIs involved. The `DishkaRoute`, `FromDishka`, `Depends(RequirePermission(...))` patterns are already used throughout.

---

## Design decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| HTTP method for update | `PUT` (full update) | MT-20 acceptance criteria says "PUT /products/{product_id}", matching the spec |
| Status change endpoint | `PATCH /products/{product_id}/status` | Separate from PUT update per CQRS -- status transition is its own command |
| Delete response | 204 No Content, return `None` | Follows existing `delete_attribute` pattern |
| Create response | 201 Created | Follows existing `create_attribute` pattern |
| ProductStatus conversion | `ProductStatus(request.status)` in router | Converts string to domain enum at boundary, same as `AttributeDataType(request.data_type)` pattern |
| Sentinel handling for update | Pass `...` sentinel fields through to command | `UpdateProductCommand` uses its own `_SENTINEL`; router maps Pydantic `...` to command sentinel |
| Permission codename | `catalog:manage` | Same permission used by all catalog write endpoints |
| Get product returns ProductResponse | Map `ProductReadModel` to `ProductResponse` with nested SKUs/attributes | Full detail endpoint |
| Router variable name | `product_router` | Follows `attribute_router`, `brand_router` naming convention |

---

## File plan

### `src/modules/catalog/presentation/router_products.py` -- CREATE

**Purpose:** FastAPI router for product CRUD operations and status transitions. Delegates all business logic to application-layer command/query handlers via Dishka DI.

**Layer:** Presentation

#### Router definition:

```python
product_router = APIRouter(
    prefix="/products",
    tags=["Products"],
    route_class=DishkaRoute,
)
```

#### Endpoints:

**1. `POST ""` -- create product**
- Status code: `201`
- Response model: `ProductCreateResponse`
- Dependencies: `[Depends(RequirePermission(codename="catalog:manage"))]`
- Parameters: `request: ProductCreateRequest`, `handler: FromDishka[CreateProductHandler]`
- Body: Build `CreateProductCommand` from request fields, call `handler.handle(command)`, return `ProductCreateResponse(id=result.product_id, message="Product created")`

**2. `GET ""` -- list products**
- Status code: `200`
- Response model: `ProductListResponse`
- No permission dependency (read endpoint)
- Query parameters:
  - `offset: int = Query(default=0, ge=0)`
  - `limit: int = Query(default=50, ge=1, le=200)`
  - `status: str | None = Query(default=None)`
  - `brand_id: uuid.UUID | None = Query(default=None)`
- Parameters: `handler: FromDishka[ListProductsHandler]`
- Body: Build `ListProductsQuery(offset=offset, limit=limit, status=status, brand_id=brand_id)`, call `handler.handle(query)`, map result items to `ProductListItemResponse`, return `ProductListResponse`

**3. `GET "/{product_id}"` -- get product detail**
- Status code: `200`
- Response model: `ProductResponse`
- No permission dependency (read endpoint)
- Path parameter: `product_id: uuid.UUID`
- Parameters: `handler: FromDishka[GetProductHandler]`
- Body: Call `handler.handle(product_id)`, map `ProductReadModel` to `ProductResponse` using `_to_product_response()` helper

**4. `PUT "/{product_id}"` -- update product**
- Status code: `200`
- Response model: `ProductResponse`
- Dependencies: `[Depends(RequirePermission(codename="catalog:manage"))]`
- Path parameter: `product_id: uuid.UUID`
- Parameters: `request: ProductUpdateRequest`, `handler: FromDishka[UpdateProductHandler]`, `get_handler: FromDishka[GetProductHandler]`
- Body:
  1. Build `UpdateProductCommand` from request fields. For sentinel fields (`supplier_id`, `country_of_origin`): if `request.supplier_id is not ...` pass it through, otherwise omit from kwargs. Use the `_SENTINEL` from `update_product` module.
  2. Call `handler.handle(command)` to get `UpdateProductResult`
  3. Call `get_handler.handle(result.id)` to fetch full read model
  4. Return `_to_product_response(read_model)`

**5. `DELETE "/{product_id}"` -- soft-delete**
- Status code: `204`
- No response model
- Dependencies: `[Depends(RequirePermission(codename="catalog:manage"))]`
- Path parameter: `product_id: uuid.UUID`
- Parameters: `handler: FromDishka[DeleteProductHandler]`
- Body: Build `DeleteProductCommand(product_id=product_id)`, call `handler.handle(command)`, return `None`

**6. `PATCH "/{product_id}/status"` -- change status**
- Status code: `200`
- No response model (returns `None`, but keep 200 for consistency; OR return `ProductResponse` after re-fetching)
- Dependencies: `[Depends(RequirePermission(codename="catalog:manage"))]`
- Path parameter: `product_id: uuid.UUID`
- Parameters: `request: ProductStatusChangeRequest`, `handler: FromDishka[ChangeProductStatusHandler]`, `get_handler: FromDishka[GetProductHandler]`
- Body:
  1. Convert `request.status` to `ProductStatus` enum: `ProductStatus(request.status)`
  2. Build `ChangeProductStatusCommand(product_id=product_id, new_status=new_status)`
  3. Call `handler.handle(command)`
  4. Fetch updated product: `read_model = await get_handler.handle(product_id)`
  5. Return `_to_product_response(read_model)`
- Response model: `ProductResponse`

#### Helper functions:

**`_to_sku_response(sku: SKUReadModel) -> SKUResponse`** -- Maps a single SKU read model to a SKU response schema.

```python
def _to_sku_response(sku: SKUReadModel) -> SKUResponse:
    compare_at: MoneySchema | None = None
    if sku.compare_at_price is not None:
        compare_at = MoneySchema(
            amount=sku.compare_at_price.amount,
            currency=sku.compare_at_price.currency,
        )
    return SKUResponse(
        id=sku.id,
        product_id=sku.product_id,
        sku_code=sku.sku_code,
        variant_hash=sku.variant_hash,
        price=MoneySchema(amount=sku.price.amount, currency=sku.price.currency),
        compare_at_price=compare_at,
        is_active=sku.is_active,
        version=sku.version,
        deleted_at=sku.deleted_at,
        created_at=sku.created_at,
        updated_at=sku.updated_at,
        variant_attributes=[
            VariantAttributePairSchema(
                attribute_id=va.attribute_id,
                attribute_value_id=va.attribute_value_id,
            )
            for va in sku.variant_attributes
        ],
    )
```

**`_to_product_response(model: ProductReadModel) -> ProductResponse`** -- Maps a full product read model to a product response schema with nested SKUs and attributes.

```python
def _to_product_response(model: ProductReadModel) -> ProductResponse:
    return ProductResponse(
        id=model.id,
        slug=model.slug,
        title_i18n=model.title_i18n,
        description_i18n=model.description_i18n,
        status=model.status,
        brand_id=model.brand_id,
        primary_category_id=model.primary_category_id,
        supplier_id=model.supplier_id,
        country_of_origin=model.country_of_origin,
        tags=model.tags,
        version=model.version,
        deleted_at=model.deleted_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
        published_at=model.published_at,
        min_price=model.min_price,
        max_price=model.max_price,
        skus=[_to_sku_response(s) for s in model.skus],
        attributes=[
            ProductAttributeResponse(
                id=a.id,
                product_id=a.product_id,
                attribute_id=a.attribute_id,
                attribute_value_id=a.attribute_value_id,
            )
            for a in model.attributes
        ],
    )
```

#### Imports (COMPLETE list):

```python
import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, status

from src.modules.catalog.application.commands.change_product_status import (
    ChangeProductStatusCommand,
    ChangeProductStatusHandler,
)
from src.modules.catalog.application.commands.create_product import (
    CreateProductCommand,
    CreateProductHandler,
    CreateProductResult,
)
from src.modules.catalog.application.commands.delete_product import (
    DeleteProductCommand,
    DeleteProductHandler,
)
from src.modules.catalog.application.commands.update_product import (
    UpdateProductCommand,
    UpdateProductHandler,
    UpdateProductResult,
    _SENTINEL,
)
from src.modules.catalog.application.queries.get_product import GetProductHandler
from src.modules.catalog.application.queries.list_products import (
    ListProductsHandler,
    ListProductsQuery,
)
from src.modules.catalog.application.queries.read_models import (
    ProductReadModel,
    SKUReadModel,
)
from src.modules.catalog.domain.value_objects import ProductStatus
from src.modules.catalog.presentation.schemas import (
    MoneySchema,
    ProductAttributeResponse,
    ProductCreateRequest,
    ProductCreateResponse,
    ProductListItemResponse,
    ProductListResponse,
    ProductResponse,
    ProductStatusChangeRequest,
    ProductUpdateRequest,
    SKUResponse,
    VariantAttributePairSchema,
)
from src.modules.identity.presentation.dependencies import RequirePermission
```

#### Critical implementation detail -- sentinel mapping for UpdateProductCommand:

The `UpdateProductCommand` uses a module-level `_SENTINEL` object for nullable fields. The router must import `_SENTINEL` from `src.modules.catalog.application.commands.update_product` and use it as the default when the Pydantic schema field is `...` (Ellipsis).

```python
# In the update_product endpoint:
update_kwargs: dict[str, object] = {"product_id": product_id}

if request.title_i18n is not None:
    update_kwargs["title_i18n"] = request.title_i18n
if request.slug is not None:
    update_kwargs["slug"] = request.slug
if request.description_i18n is not None:
    update_kwargs["description_i18n"] = request.description_i18n
if request.brand_id is not None:
    update_kwargs["brand_id"] = request.brand_id
if request.primary_category_id is not None:
    update_kwargs["primary_category_id"] = request.primary_category_id
if request.tags is not None:
    update_kwargs["tags"] = request.tags
if request.version is not None:
    update_kwargs["version"] = request.version

# Sentinel fields: Pydantic uses ... (Ellipsis) as "not provided"
# Map Pydantic Ellipsis -> command _SENTINEL, explicit None -> None
if request.supplier_id is not ...:
    update_kwargs["supplier_id"] = request.supplier_id
else:
    update_kwargs["supplier_id"] = _SENTINEL

if request.country_of_origin is not ...:
    update_kwargs["country_of_origin"] = request.country_of_origin
else:
    update_kwargs["country_of_origin"] = _SENTINEL

command = UpdateProductCommand(**update_kwargs)
```

#### Module docstring:

```python
"""
FastAPI router for Product CRUD and status transition endpoints.

All mutating endpoints require the ``catalog:manage`` permission.
Delegates to application-layer command/query handlers via Dishka DI.
"""
```

---

## Dependency registration

No DI changes required for this micro-task. MT-23 handles all ProductProvider DI registration and router mounting in `api/router.py`.

## Migration plan

No database changes required for this micro-task.

## Integration points

No cross-module integration in this micro-task. The router only imports from:
- `catalog.application.commands.*` (same module)
- `catalog.application.queries.*` (same module)
- `catalog.domain.value_objects` (same module)
- `catalog.presentation.schemas` (same module)
- `identity.presentation.dependencies` (for `RequirePermission` -- already used by all catalog routers)

## Risks & edge cases

| Risk | Impact | Mitigation |
|------|--------|------------|
| `_SENTINEL` is a private module-level object | Importing `_SENTINEL` from another module is technically accessing a private symbol | This is intentional; the update_product module defines it as a shared sentinel. The leading underscore is a naming convention, not an access restriction. If mypy flags it, add a `# noqa` comment or rename to `SENTINEL` in a follow-up. |
| `ProductStatus(request.status)` raises `ValueError` on invalid status string | FastAPI will return 500 unless caught | FastAPI's default exception handling will convert `ValueError` to 422. If the codebase has a global exception handler for `ValueError`, it will be caught there. No additional handling needed in the router. |
| List endpoint without auth | Public read access | Consistent with existing `list_attributes`, `list_brands` endpoints which also have no permission dependency |

## Acceptance verification

```bash
uv run pytest tests/unit/ tests/architecture/ -v
uv run ruff check .
uv run mypy .
```

**Specific checks:**
- [ ] POST /products creates product and returns 201 with `ProductCreateResponse`
- [ ] GET /products returns paginated list with `ProductListResponse`, supports `offset`, `limit`, `status`, `brand_id` query params
- [ ] GET /products/{product_id} returns full `ProductResponse` with nested SKUs and attributes
- [ ] PUT /products/{product_id} updates product and returns `ProductResponse`
- [ ] DELETE /products/{product_id} soft-deletes and returns 204
- [ ] PATCH /products/{product_id}/status changes status and returns `ProductResponse`
- [ ] All routes use `DishkaRoute` + `FromDishka` for handler injection
- [ ] Write endpoints have `Depends(RequirePermission(codename="catalog:manage"))`
- [ ] Domain layer has zero framework imports
- [ ] No cross-module imports (identity dependency import is presentation-to-presentation, allowed)
- [ ] `product_router` is exported as a module-level variable for MT-23 to mount
