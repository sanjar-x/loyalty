Deep Code Review: Модуль catalog

Консолидированный отчёт 7 параллельных Opus 4.6 агентов

---

MAJOR — Архитектура (6)

ВСЕ 18 query handlers импортируют ORM-модели и AsyncSession напрямую из infrastructure. Read-side интерфейсы

(IBrandReadRepository, etc.) определены в domain/interfaces.py:504-695 но НЕ реализованы и НЕ используются

MediaAsset хранит media_type: str и role: str вместо domain-enum'ов MediaType/MediaRole — теряется type safety

Delete handlers (DeleteBrandHandler, DeleteCategoryHandler) обходят domain-методы validate_deletable() — дублируя guard-логику процедурно

DeleteBrandHandler не emit'ит domain event при удалении бренда (все остальные delete-handlers emit'ят)

domain/interfaces.py:477-501 импортирует read-модели из application/queries/ — инверсия зависимостей domain→application

IProductRepository — 8 abstract-методов в одном интерфейсе (CRUD + slugs + locking + SKU checks)

---

MAJOR — Дублирование кода (6)

Enum'ы MediaType, MediaRole, SupplierType domain/value*objects.py + 3 enum'а × 2 копии infrastructure/models.py
at_least_one_field validator presentation/schemas.py 9 копий одного и того же
PaginatedListResponse шаблон schemas.py + read_models.py 22 класса с items/total/offset/limit
Update handler boilerplate application/commands/update*\*.py 6 handlers (fetch→guard→update→persist)
SKU price validation (compare_at_price vs domain/entities.py 2 идентичных блока в **attrs_post_init** и price) update()
MediaAssetRepository CRUD infrastructure/repositories/media_asset.py Полностью дублирует BaseRepository

---

MAJOR — Performance (6)

router_products.py:194-205 Double-fetch: product update → сразу re-query того же продукта (2× query overhead)
router_products.py:243-248 То же для change_product_status — двойная загрузка графа
router_skus.py:139-145 SKU update загружает ВСЕ SKU варианта (limit=None) чтобы найти один
router_skus.py:168-172 SKU delete загружает все SKU для IDOR-проверки вместо EXISTS
repositories/media_asset.py:131-140 list_by_product без пагинации — используется только для if not media_assets
queries/list_attributes.py:140-142 JSONB CAST(...AS Text) ILIKE обходит GIN-индекс — seq scan

---

MAJOR — Именование (4)

ui*type (domain/ORM) vs display_type (storefront) — одно и то же понятие 8+ файлов
value_group (domain) vs group_code (ORM) — ручной маппинг │ entities.py, models.py, repos
delete (command) vs remove (domain method/event) — для variant/SKU commands/, events.py
sku_code_exists — нарушает паттерн check*\*\_exists interfaces.py:348

---

MAJOR — Security (2)

│ # │ Проблема │ OWASP │┤
│ 30 │ tags: list[str] без ограничений по количеству и длине строк — DoS через раздувание БД │ A04 │
├─────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────┤
│ 31 │ Bulk operations (ReorderAttributeValuesRequest.items, etc.) без max_length — неограниченные batch-операции │ A04 │

---

MINOR issues (суммарно ~25)

Security:

- AttributeUpdateRequest.ui_type/level — строки вместо Literal (в отличие от create-схемы)
- sort_order без ge=0 в 6 схемах
- sku_code без pattern ограничения
- LogoMetadataRequest.size без ge=0
- Нет idempotency-key на POST endpoints
- content_type regex слишком permissive

Performance:

- StorefrontFormAttributesHandler — единственный storefront handler без кеширования
- invalidate_storefront_cache не чистит form-кеш
- lazy="raise" не установлен на relationships — риск N+1
- Count + items = 2 запроса на каждый paginated endpoint

Architecture:

- CategoryAttributeBinding — де-факто aggregate, но не AggregateRoot
- Presentation dependencies.py импортирует infrastructure напрямую
- \_provided_fields: frozenset — hack вместо sentinel-паттерна
- Inconsistent query handler signatures (UUID vs Query dataclass)

Naming:

- pav_id / \_pav_repo аббревиатуры
- exists() vs check\_\*\_exists() в 2 repos
- ICategoryBindingReadRepository без "Attribute"
- ProductAttributeReadModel re-declares inherited fields
- Cross-module: catalog=ABC, storage=Protocol

Quality:

- **setattr** guard дублируется (Brand, Category)
- FSM transition guard дублируется (Brand, MediaAsset)
- Money→MoneySchema конвертация 3× в mappers.py
- Storefront cache boilerplate 3× в storefront.py

---

Positive Findings

Агенты также отметили сильные стороны модуля:

- SQL Injection: защищён — все запросы через SQLAlchemy ORM, LIKE экранирует wildcards
- Authorization: каждый endpoint использует RequirePermission
- HMAC: router_internal.py использует hmac.compare_digest() — timing-safe
- Mass Assignment: Pydantic schemas + domain \_UPDATABLE_FIELDS whitelist
- JSON bomb protection: BoundedJsonDict (10KB, depth 4)
- Domain FSM: Status transitions через \_ALLOWED_TRANSITIONS
- Optimistic locking: version field на Products и SKUs
- Module boundaries: нет cross-module violations (только shared kernel)

---

Top 5 действий по приоритету

┌─────┬───────────────────────────────────────────────────────────────────────────────┬─────────────────────────────────────────┐
│ # │ Действие │ Impact │
├─────┼───────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
│ 1 │ Fix CRITICAL bugs (#1, #2) — Product.create() и missing events │ Блокеры — ничего не работает без них │
├─────┼───────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
│ 2 │ Fix IDOR (#6) — добавить variant_id в UpdateSKUCommand │ Security vulnerability │
├─────┼───────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
│ 3 │ Fix cache invalidation (#4) — использовать invalidate_storefront_cache() │ Stale data на storefront │
├─────┼───────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
│ 4 │ Eliminate double-fetch (#20, #21) — возвращать read model из write path │ 2× снижение query load │
├─────┼───────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
│ 5 │ Deduplicate enums (#14) — удалить копии из models.py, импортировать из domain │ 5 минут работы, убирает divergence risk │
└─────┴───────────────────────────────────────────────────────────────────────────────┴─────────────────────────────────────────┘

★ Insight ─────────────────────────────────────

- CQRS tech debt: Все 18 query handlers напрямую работают с ORM — это самое масштабное архитектурное нарушение. Read-side интерфейсы уже спроектированы в
  domain, но не имеют реализаций. Это единственный рефакторинг, который разом закроет и coupling, и testability.
- Double-fetch antipattern: Паттерн "write → commit → re-read for response" встречается в 3+ endpoints. В CQRS это нормально при event sourcing, но здесь
  тот же ORM — данные уже загружены, перечитывать не нужно.
- Tuple property trap: @property возвращающий tuple() — правильный DDD-паттерн для immutability коллекций, но .append() на нём — ловушка. Attrs + alias
  требуют дисциплины при работе с private \_variants.
  ─────────────────────────────────────────────────
