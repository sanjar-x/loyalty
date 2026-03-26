# Fix: Deep Code Review Findings

> **Источник:** `docs/reviews/deep-code-review-eav.md` — 52 findings (2 P0, 11 P1, 28 P2, 11 P3)
> **Verdict:** NOT READY for production
> **Цель:** Исправить P0 + P1 за 1 спринт. P2 — следующий спринт. P3 — tech debt backlog.
> **Правило:** Каждый fix = отдельный коммит. P0 фиксить первыми. Не мешать fixes с рефакторингом.

---

## ⛔ Перед началом: прочитай review

```bash
cat backend/docs/reviews/deep-code-review-eav.md
```

Каждый finding содержит: файл:строка, код, проблема, сценарий, предложенный fix. **Используй предложенный fix как отправную точку**, но верифицируй его по реальному коду — review мог содержать неточности в номерах строк.

---

## Sprint 1: P0 Blockers (день 1)

### Fix #1: Infrastructure import leak в 3 command handlers [P0]

**Файлы:**
- `commands/update_product.py:29`
- `commands/update_brand.py:19`
- `commands/delete_product_media.py:14`

**Проблема:** Прямой import `ImageBackendClient` (concrete class) в application layer.

**Что сделать:**

1. Создать protocol/interface в domain:
```python
# domain/interfaces.py — добавить:
class IImageBackendClient(Protocol):
    async def delete(self, storage_object_id: uuid.UUID) -> None: ...
```

2. В 3 handler-ах заменить import:
```python
# БЫЛО:
from src.modules.catalog.infrastructure.image_backend_client import ImageBackendClient
# СТАЛО:
from src.modules.catalog.domain.interfaces import IImageBackendClient
```

3. В `__init__` handler-ов: `image_backend: IImageBackendClient` (вместо `ImageBackendClient`)

4. DI provider: `provide(ImageBackendClient, provides=IImageBackendClient)`

**Верификация:**
```bash
grep -rn "from src.modules.catalog.infrastructure.image_backend" backend/src/modules/catalog/application/
# Ожидание: 0 результатов
```

---

### Fix #2: Missing UoW context в DeleteProductMediaHandler [P0]

**Файл:** `commands/delete_product_media.py:56-68`

**Проблема:** `commit()` вызывается без `async with self._uow:`. Нет транзакционных границ.

**Что сделать:**
```python
async def handle(self, command: DeleteProductMediaCommand) -> None:
    async with self._uow:  # ← ДОБАВИТЬ
        media = await self._media_repo.get(command.media_id)
        if media is None:
            raise MediaAssetNotFoundError(media_id=command.media_id)
        # ... validation ...
        self._uow.register_aggregate(media)  # если нужен event
        await self._media_repo.delete(command.media_id)
        await self._uow.commit()

    # ImageBackend cleanup ПОСЛЕ commit:
    if media.storage_object_id:
        await self._image_backend.delete(media.storage_object_id)
```

---

## Sprint 1: P1 Critical (дни 1-3)

### Fix #3: ImageBackend delete BEFORE commit [P1]

**Файл:** `commands/update_product.py:211-216`

**Проблема:** Файл удаляется из storage ДО commit. Rollback → broken pointer навсегда.

**Что сделать:**
```python
# Собрать ID для удаления, НЕ удалять сразу:
storage_ids_to_delete: list[uuid.UUID] = []
for item in to_delete:
    mid = uuid.UUID(item["id"])
    await self._media_repo.delete(mid)
    sid = item.get("storage_object_id")
    if sid:
        storage_ids_to_delete.append(uuid.UUID(sid))

# ... остальная логика ...
await self._uow.commit()

# ПОСЛЕ commit — безопасно удалять файлы:
for sid in storage_ids_to_delete:
    await self._image_backend.delete(sid)
```

---

### Fix #4: has_product_references ignores sku_attribute_values [P1]

**Файл:** `repositories/attribute_value.py:104-113`

**Проблема:** Проверяет только `product_attribute_values`, игнорирует `sku_attribute_values`. FK RESTRICT → 500 IntegrityError.

**Что сделать:**
```python
async def has_product_references(self, value_id: uuid.UUID) -> bool:
    # Check product-level
    pav_exists = select(
        select(OrmProductAttributeValue.id)
        .where(OrmProductAttributeValue.attribute_value_id == value_id)
        .limit(1).exists()
    )
    # Check variant/SKU-level
    sav_exists = select(
        select(OrmSKUAttributeValueLink.id)
        .where(OrmSKUAttributeValueLink.attribute_value_id == value_id)
        .limit(1).exists()
    )
    r1 = await self._session.execute(pav_exists)
    r2 = await self._session.execute(sav_exists)
    return bool(r1.scalar()) or bool(r2.scalar())
```

**Добавить import:** `from src.modules.catalog.infrastructure.models import SKUAttributeValueLink as OrmSKUAttributeValueLink`

---

### Fix #5: SKU.update() partial mutation [P1]

**Файл:** `domain/entities.py:1218-1246`

**Проблема:** Поля мутируются ДО валидации. ValueError → corrupt entity state.

**Что сделать:** Validate-then-mutate:
```python
def update(self, **kwargs):
    # 1. Compute new values WITHOUT mutating
    new_price = kwargs.get("price", self.price)
    new_compare = kwargs.get("compare_at_price", self.compare_at_price)

    # 2. Validate
    if new_price is None and new_compare is not None:
        raise ValueError("compare_at_price cannot be set when price is None")

    # 3. Mutate ONLY after validation passes
    if "sku_code" in kwargs:
        self.sku_code = kwargs["sku_code"]
    if "price" in kwargs:
        self.price = kwargs["price"]
    # ...
```

**Аналогично:** Проверить `ProductVariant.update()` (#51) — тот же паттерн.

---

### Fix #6: Category.update() leaves stale effective_template_id [P1]

**Файл:** `domain/entities.py:367-370`

**Что сделать:**
```python
if template_id is not ...:
    self.template_id = template_id
    if template_id is not None:
        self.effective_template_id = template_id
    else:
        # Сбрасываем — caller (handler) должен re-inherit от parent
        self.effective_template_id = None
```

---

### Fix #7: Inactive values leaked to storefront [P1]

**Файл:** `queries/resolve_template_attributes.py:210-222`

**Что сделать:**
```python
values = [
    EffectiveValueReadModel(id=v.id, code=v.code, ...)
    for v in sorted(orm_attr.values, key=lambda x: x.sort_order)
    if v.is_active  # ← ДОБАВИТЬ
]
```

**Верификация:** Деактивировать value → GET /storefront/filters → value отсутствует.

---

### Fix #8 + #11: DoS — SKU matrix unbounded [P1]

**Файлы:**
- `commands/generate_sku_matrix.py:143`
- `schemas.py:867,873`

**Что сделать:**

1. **Schema limits:**
```python
value_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=50)
attribute_selections: list[AttributeSelectionSchema] = Field(..., min_length=1, max_length=10)
```

2. **Handler limit:**
```python
MAX_SKU_COMBINATIONS = 1000

combinations = self._build_combinations(command.attribute_selections)
if len(combinations) > MAX_SKU_COMBINATIONS:
    raise UnprocessableEntityError(
        message=f"Too many SKU combinations: {len(combinations)}. Maximum is {MAX_SKU_COMBINATIONS}.",
        error_code="SKU_MATRIX_TOO_LARGE",
        details={"combinations": len(combinations), "max": MAX_SKU_COMBINATIONS},
    )
```

---

### Fix #9: Unfiltered _provided_fields [P1]

**Файлы:**
- `commands/update_attribute.py:94-96`
- `commands/update_attribute_value.py:107-108` (аналогично)

**Что сделать:**
```python
# update_attribute.py:
_SAFE_FIELDS = Attribute._UPDATABLE_FIELDS  # переиспользовать из entity

update_kwargs = {
    name: getattr(command, name)
    for name in command._provided_fields
    if name in _SAFE_FIELDS  # ← ДОБАВИТЬ фильтрацию
}
```

---

### Fix #12: TOCTOU — IntegrityError → 500 вместо 409 [P1]

**Файлы:** Все create handlers (6+): `create_product.py`, `create_brand.py`, `create_category.py`, `create_attribute.py`, `add_attribute_value.py`, `clone_attribute_template.py`

**Что сделать:** Обернуть `commit()` в IntegrityError catch:
```python
from sqlalchemy.exc import IntegrityError

try:
    await self._uow.commit()
except IntegrityError as e:
    error_str = str(e).lower()
    if "uix_products_slug" in error_str or "unique" in error_str:
        raise ProductSlugConflictError(slug=command.slug) from e
    raise  # re-raise unknown integrity errors
```

**Паттерн:** Создать shared helper `handle_unique_violation(e, field, error_class)`.

---

### Fix #13: Template check outside UoW [P1]

**Файл:** `commands/create_category.py:111-114`

**Что сделать:** Переместить проверку внутрь `async with self._uow:`:
```python
async with self._uow:
    # Проверка template ВНУТРИ транзакции:
    if command.template_id is not None:
        template = await self._template_repo.get(command.template_id)
        if template is None:
            raise AttributeTemplateNotFoundError(...)

    # ... остальная логика создания категории
```

---

## Sprint 2: P2 Fixes (дни 4-8)

Сгруппированы по типу для эффективности:

### Группа A: Validation gaps (fixes #23, #24, #31, #33, #34, #38)

```
#23 Brand.name — add non-empty validation in create()/update()
#24 Category name_i18n — add non-empty validation in create_root()/create_child()
#31 BindingUpdateRequest — add at_least_one_field validator
#33 tags — add max_length=50, max item length=100
#34 Reorder items — add max_length=500
#38 media: list[dict] — create MediaItemSchema Pydantic model
```

### Группа B: Immutability guards (fixes #25, #26)

```
#25 AttributeGroup.code — add to guarded fields or __setattr__ guard
#26 Attribute code/slug — add __setattr__ guard (match Brand/Category pattern)
```

### Группа C: Concurrency (fixes #15, #16)

```
#15 SKU version — set only on is_create, not on update path
#16 FOR UPDATE — use subqueryload or manual FOR UPDATE on SKU/variant selects
```

### Группа D: Data model (fixes #14, #22, #27, #39)

```
#14 Category CASCADE vs RESTRICT — change ORM cascade to "save-update, merge"
#22 update() None handling — use Ellipsis sentinel (match Brand/Category)
#27 ProductVariant price/currency conflict — derive currency from price always
#39 requirement_level server_default — align case with Python enum
```

### Группа E: Response completeness (fixes #28, #29, #30)

```
#28 CategoryReadModel — add template_id, effective_template_id
#29 ProductResponse attributes — map attribute_value_code, attribute_value_name_i18n
#30 BindingUpdateResponse — reload with JOIN after commit
```

### Группа F: Security (fixes #17, #32)

```
#17 LIKE f-string — use func.concat(param, '/%') for parameterization
#32 Cache-Control: public on /form-attributes — change to "private, max-age=300"
```

### Группа G: Performance (fixes #18, #20, #21, #35, #37, #41)

```
#18 httpx.AsyncClient — create once in __init__, reuse
#20 Batch intra-duplicates — add existing_assignments.add() inside loop
#21 SKU code collision — retry loop with max 3 attempts
#35 SKU ownership check — use direct PK lookup, not full list
#37 Media update N+1 — batch-load media, update in memory
#41 get_all_ordered — add LIMIT or remove method (already flagged dead)
```

### Группа H: DDD compliance (fixes #10, #36, #40)

```
#10 Cross-module import — create anti-corruption layer or shared kernel VO
#36 Post-commit query — move inside UoW or re-open session for cache invalidation
#40 validate_i18n_completeness — call from entity factories, not only handlers
```

---

## Sprint 3: P3 Tech Debt (ongoing)

| # | Fix | Effort |
|---|---|---|
| #42 | MediaAsset: use enums not strings | 30 мин |
| #43 | MAX_CATEGORY_DEPTH=3 → document actual depth rules | 15 мин |
| #44 | Product.create() dict reference copy — use `dict(name_i18n)` | 5 мин |
| #45 | Money(0) — add business rule: min price > 0 for published SKU | 30 мин |
| #46 | delete_by_product N+1 — use `DELETE WHERE product_id = :id` bulk | 30 мин |
| #47 | Add created_at/updated_at to AttributeValue/PAV | Migration |
| #48 | Dead code: build_update_product_command — delete | 5 мин |
| #49 | BrandCreateRequest.logo_url — add URL format + max 1024 | 10 мин |
| #50 | AttributeValue clear search_aliases — handle None vs [] | 15 мин |
| #51 | ProductVariant.update() — validate-then-mutate (= #5 pattern) | 30 мин |
| #52 | CatalogEvent __init_subclass__ — add `Final` or test | 15 мин |

---

## Sprint 4: Test Coverage (3-5 дней)

**Текущее:** 1.7% handler coverage (1 из 58).

| Priority | Test Area | Tests to Write | Effort |
|---|---|---|---|
| P0 | CreateProduct happy path + slug conflict | 3 | 0.5 дня |
| P0 | UpdateProduct optimistic locking | 3 | 0.5 дня |
| P0 | ChangeProductStatus transitions (all valid + invalid) | 8 | 1 день |
| P0 | Delete guards (brand, category) | 4 | 0.5 дня |
| P1 | GenerateSKUMatrix (happy + collision + DoS limit) | 5 | 0.5 дня |
| P1 | BulkAssign (family validation + duplicates + intra-batch) | 5 | 0.5 дня |
| P1 | Storefront cache invalidation (bind → cache cleared) | 4 | 0.5 дня |
| P1 | UpdateCategory slug cascade | 3 | 0.5 дня |

**Target:** 35 tests, coverage → ~60% handlers.

---

## Верификация после каждого Sprint

```bash
# Lint
ruff check backend/src/

# Tests
pytest backend/tests/ -x --timeout=120

# Grep: no infrastructure imports in application
grep -rn "from src.modules.catalog.infrastructure" backend/src/modules/catalog/application/ | grep -v "__pycache__"
# Ожидание: 0 (после fix #1, #10)

# Grep: all UoW handlers have `async with self._uow`
grep -rn "await self._uow.commit()" backend/src/modules/catalog/application/commands/ | grep -v "async with"
# Ожидание: 0 (после fix #2)
```

---

## Сводка

| Sprint | Scope | Fixes | Effort |
|---|---|---|---|
| **Sprint 1** | P0 + P1 | #1-9, #11-13 | 3 дня |
| **Sprint 2** | P2 (8 групп) | #14-41 | 5 дней |
| **Sprint 3** | P3 tech debt | #42-52 | 1 день |
| **Sprint 4** | Tests | 35 new tests | 3-5 дней |
| **Итого** | **52 fixes + 35 tests** | | **~12-14 дней** |

Сохрани результат выполнения в `backend/docs/reviews/deep-review-fixes-report.md`
