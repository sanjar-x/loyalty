# Project Structure

E-commerce Loyalty Platform — async REST API на FastAPI + DDD архитектура.

---

## Стек технологий

| Слой                  | Технология                   |
| --------------------- | ---------------------------- |
| Web framework         | FastAPI + Uvicorn            |
| ORM                   | SQLAlchemy 2.x async         |
| База данных           | PostgreSQL 18 (asyncpg)      |
| Очередь задач         | TaskIQ + RabbitMQ (aio-pika) |
| DI-контейнер          | Dishka                       |
| Кэш                   | Redis 8                      |
| Хранилище файлов      | MinIO / S3 (aiobotocore)     |
| Обработка изображений | Pillow                       |
| Логирование           | Structlog                    |
| Миграции              | Alembic (async, date-based)  |
| Telegram-бот          | Aiogram 3                    |
| Хэширование паролей   | Argon2id (pwdlib) + bcrypt   |

---

## Корневая директория

```
project/
├── src/                    # Основной код приложения
├── tests/                  # Тест-сьюты
├── alembic/                # Миграции БД
├── scripts/                # Вспомогательные скрипты
├── docker-compose.yml      # Dev-окружение (PG, Redis, RabbitMQ, MinIO)
├── pyproject.toml          # Зависимости и настройки инструментов
├── alembic.ini             # Конфигурация Alembic
├── pytest.ini              # Конфигурация pytest
├── Makefile                # Команды проекта
└── main.py                 # Точка входа для веб-сервера
```

---

## Структура `src/`

```
src/
├── bootstrap/              # Инициализация приложения
├── api/                    # API-слой (роутер, мидлвари, обработчики ошибок)
├── bot/                    # Telegram-бот (Aiogram 3)
├── modules/                # Функциональные модули (DDD bounded contexts)
│   ├── catalog/            # Каталог: бренды, категории, товары, варианты, SKU, атрибуты, шаблоны, медиа
│   ├── identity/           # IAM: аутентификация (LOCAL/OIDC/Telegram), роли, права, сессии, приглашения
│   ├── user/               # Профили пользователей (Customer, StaffMember)
│   ├── geo/                # Географические справочники (страны, регионы, районы, валюты, языки)
│   ├── cart/               # Корзина и позиции, чек-аут снапшоты
│   ├── logistics/          # Отправления, события трекинга, провайдеры доставки
│   ├── supplier/           # Поставщики (cross-border / local), онбординг
│   ├── pricing/            # Переменные, формулы (AST + evaluator), контексты ценообразования, профили товаров
│   └── activity/           # Аналитика: трекинг событий (Redis), trending, co-view рекомендации
├── infrastructure/         # Кросс-модульная инфраструктура
└── shared/                 # Общий код и интерфейсы
```

> Ранее существовавший модуль `storage` был расформирован: S3-клиент переехал в `src/infrastructure/storage/factory.py`, а обработка изображений вынесена в отдельный сервис `image_backend/`.

---

## `src/bootstrap/` — Инициализация

| Файл           | Назначение                                                             |
| -------------- | ---------------------------------------------------------------------- |
| `config.py`    | `Settings` (Pydantic): БД, Redis, S3, JWT, CORS, Telegram              |
| `container.py` | Dishka IoC-контейнер, регистрация всех провайдеров                     |
| `web.py`       | Фабрика FastAPI-приложения: lifespan, middleware, роутеры              |
| `broker.py`    | TaskIQ `AioPikaBroker` для RabbitMQ                                    |
| `worker.py`    | Точка входа TaskIQ-воркера; порядок init критичен (контейнер → задачи) |
| `logger.py`    | Конфигурация Structlog (dev: цветной вывод, prod: JSON)                |
| `bot.py`       | Инициализация Telegram-бота (Aiogram)                                  |
| `scheduler.py` | Планировщик периодических задач                                        |

---

## `src/api/` — API-слой

```
api/
├── router.py               # Главный роутер — подключает все модули
├── dependencies/
│   └── auth.py             # JWT-аутентификация (HTTPBearer → user_id)
├── exceptions/
│   └── handlers.py         # Глобальные обработчики HTTP-ошибок
└── middlewares/
    └── logger.py           # Логирование access-запросов (X-Request-ID, duration)
```

---

## `src/bot/` — Telegram-бот

```
bot/
├── factory.py              # Фабрика бота (Dispatcher, роутеры)
├── utils.py                # Вспомогательные функции
├── callbacks/
│   └── base.py             # Базовый класс колбэков
├── filters/
│   └── admin.py            # Фильтр проверки администратора
├── handlers/
│   ├── common.py           # /start, /help
│   ├── nav.py              # Навигационные хэндлеры
│   ├── errors.py           # Обработка ошибок бота
│   └── registry.py         # Регистрация всех хэндлеров
├── keyboards/
│   ├── inline.py           # Inline-клавиатуры
│   └── reply.py            # Reply-клавиатуры
├── middlewares/
│   ├── logging.py          # Логирование update-ов
│   ├── throttling.py       # Rate-limiting
│   └── user_identify.py    # Идентификация пользователя
└── states/                 # FSM-состояния
```

---

## `src/modules/catalog/` — Каталог (основной модуль)

### Domain

```
domain/
├── entities/               # Пакет с одним файлом на агрегат (используется когда
│   ├── __init__.py         # сущностей > 2): brand, category, product,
│   ├── _common.py          # product_variant, sku, attribute, attribute_group,
│   ├── attribute.py        # attribute_value, attribute_template,
│   ├── ...                 # template_attribute_binding, product_attribute_value, media_asset
│   └── product.py
├── value_objects.py        # MediaType, MediaRole, BehaviorFlags, AttributeDataType,
│                           # AttributeUIType, AttributeLevel, RequirementLevel,
│                           # ProductStatus, Money
├── exceptions.py           # BrandSlugConflictError, MissingRequiredLocalesError, ...
├── events.py               # Доменные события (brand/category/product lifecycle, FSM)
├── interfaces.py           # IBrandRepository, ICategoryRepository, IProductRepository, ...
└── constants.py            # DEFAULT_CURRENCY, DEFAULT_SEARCH_WEIGHT, REQUIRED_LOCALES
```

**Brand FSM** (`MediaProcessingStatus`):

```
PENDING_UPLOAD → PROCESSING → COMPLETED
                           ↘ FAILED
PROCESSING → PENDING_UPLOAD   (revert при ошибке брокера)
```

**Product Lifecycle** (`ProductStatus`):

```
DRAFT → ENRICHING → READY_FOR_REVIEW → PUBLISHED → ARCHIVED
```

### Application

```
application/
├── commands/                              # ~50 команд: brand/category/product/variant/SKU/
│                                          # attribute/attribute_group/attribute_value/
│                                          # attribute_template (CRUD + clone) /
│                                          # template_attribute_binding (bind/update/reorder/unbind) /
│                                          # product_attribute (assign/delete/bulk) / product_media
│                                          # (add/update/delete/reorder/sync) / SKU matrix generation /
│                                          # bulk operations (attributes, brands, categories) /
│                                          # change_product_status (FSM)
├── queries/                               # ~35 запросов: get_product, list_products, search_products,
│                                          # search_suggest, breadcrumbs, get_product_completeness,
│                                          # get_storefront_product, list_storefront_products,
│                                          # get_storefront_cards_by_ids, get_similar_products,
│                                          # get_similar_product_cards, get_also_viewed,
│                                          # get_for_you_feed, compute_facets, brand/category CRUD,
│                                          # get_category_tree (Redis-кэш, TTL 5 мин),
│                                          # attribute/template/value listings,
│                                          # resolve_template_attributes, list_attribute_templates,
│                                          # list_template_bindings
└── constants.py
```

> Сервисы media-обработки и фоновые задачи (`tasks.py`) перенесены в отдельный сервис `image_backend/`. Из основного backend остался только `infrastructure/image_backend_client.py` для server-to-server вызовов на удаление.

**Поток обработки логотипа:**

1. `create_brand` — `reserve_upload_slot()` (создаёт StorageObject + presigned PUT URL)
2. Фронтенд загружает файл напрямую в S3
3. `confirm_brand_logo` — `verify_upload()` + `.kiq()` (постановка задачи)
4. `process_brand_logo_task` → `BrandLogoProcessor.process()`:
   - Скачивает raw-файл из S3 (лимит 10 MB)
   - Конвертирует в WebP 800×800 через Pillow
   - Загружает в `public/brands/{id}/logo.webp`
   - Обновляет StorageObject метаданные
   - **SELECT FOR UPDATE** → `complete_logo_processing(url=...)`

### Infrastructure

```
infrastructure/
├── models.py                  # SQLAlchemy ORM: Brand, Category, Product, ProductVariant, SKU,
│                              # Attribute, AttributeGroup, AttributeValue, AttributeTemplate,
│                              # TemplateAttributeBinding, ProductAttributeValue, MediaAsset
├── image_backend_client.py    # HTTP-клиент к image_backend (server-to-server delete)
└── repositories/
    ├── base.py                # Базовый репозиторий (shared CRUD)
    ├── brand.py               # BrandRepository (Data Mapper: ORM ↔ Domain)
    ├── category.py            # CategoryRepository
    ├── product.py             # ProductRepository (включая variants/SKUs)
    ├── attribute.py           # AttributeRepository
    ├── attribute_group.py     # AttributeGroupRepository
    ├── attribute_value.py     # AttributeValueRepository
    ├── attribute_template.py  # AttributeTemplateRepository
    ├── template_attribute_binding.py  # TemplateAttributeBindingRepository
    ├── product_attribute_value.py     # ProductAttributeValueRepository
    └── media_asset.py         # MediaAssetRepository
```

**ORM-модели:**

| Модель                     | Ключевые поля                                                              |
| -------------------------- | -------------------------------------------------------------------------- |
| `Brand`                    | name (unique), slug, logo_file_id, logo_status, logo_url                   |
| `Category`                 | parent_id, full_slug, level, sort_order                                    |
| `Product`                  | slug, brand_id, category_id, attributes (JSONB), version (optimistic lock) |
| `SKU`                      | sku_code, variant_hash (unique), price, currency_id, attributes_cache      |
| `Attribute`                | code (unique), data_type, ui_type, is_dictionary                           |
| `AttributeGroup`           | code (unique), name, sort_order                                            |
| `AttributeValue`           | attribute_id, value, sort_order                                            |
| `CategoryAttributeBinding` | category_id, attribute_id, requirement_level, sort_order                   |
| `MediaAsset`               | role, sort_order, content_type                                             |

### Presentation

```
presentation/
├── router_brands.py                    # CRUD брендов
├── router_categories.py                # CRUD категорий + иерархия
├── router_products.py                  # CRUD товаров + смена статуса
├── router_variants.py                  # CRUD вариантов товара
├── router_skus.py                      # Управление SKU
├── router_attributes.py                # CRUD атрибутов
├── router_attribute_groups.py          # CRUD групп атрибутов
├── router_attribute_values.py          # CRUD значений атрибутов
├── router_attribute_templates.py       # CRUD шаблонов атрибутов + привязки
├── router_product_attributes.py        # Назначение атрибутов товарам
├── router_media.py                     # Медиа-роутер (upload/confirm/sync)
├── router_storefront.py                # Публичная витрина (категории, бренды, фасеты)
├── router_storefront_products.py       # PDP / список товаров storefront
├── router_storefront_search.py         # Поиск + suggest
├── router_storefront_trending.py       # Тренды (Redis sorted sets)
├── router_storefront_for_you.py        # Персональная лента / co-view рекомендации
├── schemas.py                          # Pydantic-схемы запросов/ответов админки
├── schemas_storefront.py               # Pydantic-схемы публичной витрины
├── mappers.py                          # ORM → DTO мапперы
├── update_helpers.py                   # Хелперы для PATCH-запросов
└── dependencies.py                     # DI-провайдеры: BrandProvider, CategoryProvider,
                                        # AttributeProvider, AttributeTemplateProvider,
                                        # ProductProvider, MediaAssetProvider,
                                        # StorefrontCatalogProvider, ...
```

---

## `src/modules/identity/` — IAM (Identity & Access Management)

### Domain

```
domain/
├── entities.py             # Identity (агрегат), Session, LocalCredentials,
│                           # Role, Permission, LinkedAccount, StaffInvitation
├── value_objects.py        # IdentityType, AccountType, InvitationStatus,
│                           # PrimaryAuthMethod, TokenPair, HashPassword
├── interfaces.py           # IIdentityRepository, ISessionRepository,
│                           # IRoleRepository, IPermissionRepository, ...
├── exceptions.py           # IdentityDeactivatedError, InvalidCredentialsError, ...
└── events.py               # IdentityCreatedEvent, StaffInvitedEvent, ...
```

**Мульти-провайдерная аутентификация:**

| Провайдер | Механизм                                     |
| --------- | -------------------------------------------- |
| LOCAL     | Email + пароль (Argon2id / bcrypt)           |
| OIDC      | OpenID Connect (OAuth 2.0)                   |
| TELEGRAM  | Telegram Login Widget (init data validation) |

**NIST RBAC:**

- Роли с иерархическими связями
- Гранулярные права (`catalog:manage`, `profile:read`, ...)
- Привязка ролей к сессии
- Кэширование прав в Redis (TTL)

### Application

```
application/
├── commands/                              # 21 команда
│   ├── register.py                        # Регистрация (email/password)
│   ├── login.py                           # Вход (email/password → токены)
│   ├── login_telegram.py                  # Вход через Telegram
│   ├── login_oidc.py                      # Вход через OIDC-провайдер
│   ├── refresh_token.py                   # Ротация refresh-токена
│   ├── logout.py                          # Выход (одна сессия)
│   ├── logout_all.py                      # Выход со всех устройств
│   ├── change_password.py                 # Смена пароля
│   ├── create_role.py                     # Создание роли
│   ├── update_role.py                     # Обновление роли
│   ├── delete_role.py                     # Удаление роли
│   ├── set_role_permissions.py            # Назначение прав роли
│   ├── assign_role.py                     # Назначение роли пользователю
│   ├── revoke_role.py                     # Отзыв роли
│   ├── invite_staff.py                    # Приглашение сотрудника
│   ├── accept_staff_invitation.py         # Принятие приглашения
│   ├── revoke_staff_invitation.py         # Отзыв приглашения
│   ├── deactivate_identity.py             # Деактивация аккаунта (self)
│   ├── admin_deactivate_identity.py       # Деактивация аккаунта (admin)
│   └── reactivate_identity.py             # Реактивация аккаунта
├── queries/                               # 15 запросов
│   ├── get_identity_detail.py             # Детали identity
│   ├── get_identity_roles.py              # Роли identity
│   ├── get_customer_detail.py             # Детали клиента
│   ├── get_staff_detail.py                # Детали сотрудника
│   ├── get_session_permissions.py         # Права текущей сессии
│   ├── get_my_sessions.py                 # Мои активные сессии
│   ├── get_role_detail.py                 # Детали роли
│   ├── list_identities.py                 # Список identity (admin)
│   ├── list_roles.py                      # Список ролей
│   ├── list_permissions.py                # Список прав
│   ├── list_customers.py                  # Список клиентов
│   ├── list_staff.py                      # Список сотрудников
│   ├── list_staff_invitations.py          # Список приглашений
│   └── validate_invitation.py             # Валидация приглашения
└── consumers/                             # Обработчики доменных событий
```

### Infrastructure

```
infrastructure/
├── models.py               # SQLAlchemy ORM: Identity, Session, LocalCredentials,
│                           # LinkedAccount, Role, Permission, StaffInvitation
├── provider.py             # IdentityProvider (Dishka)
└── repositories/
    ├── identity_repository.py
    ├── session_repository.py
    ├── role_repository.py
    ├── permission_repository.py
    ├── linked_account_repository.py
    └── staff_invitation_repository.py
```

### Presentation

```
presentation/
├── router_auth.py          # Публичные: /auth/register, /auth/login, /auth/refresh, /auth/logout
├── router_admin.py         # Админ: управление ролями и правами
├── router_staff.py         # Админ: список сотрудников, приглашения
├── router_customers.py     # Админ: список клиентов
├── router_account.py       # Аккаунт: сессии, детали identity
├── router_invitation.py    # Принятие приглашений
├── schemas.py              # Pydantic-модели
└── dependencies.py         # Auth context, permission requirements
```

---

## `src/modules/user/` — Профили пользователей

### Domain

```
domain/
├── entities.py             # Customer, StaffMember (агрегаты)
├── interfaces.py           # ICustomerRepository, IStaffMemberRepository
├── exceptions.py           # Доменные исключения
└── services.py             # Доменные сервисы
```

**Разделение Identity ↔ User:**

- `Identity` (модуль identity) — аутентификация, сессии, роли
- `Customer` / `StaffMember` (модуль user) — PII: имя, email, телефон
- Связь 1:1 через `identity_id`

### Application

```
application/
├── commands/
│   ├── create_user.py              # Создание user-записи
│   ├── create_customer.py          # Создание профиля клиента
│   ├── create_staff_member.py      # Создание профиля сотрудника
│   ├── update_profile.py           # Обновление профиля
│   ├── anonymize_user.py           # Анонимизация (GDPR)
│   └── anonymize_customer.py       # Анонимизация клиента
├── queries/
│   ├── get_my_profile.py           # Мой профиль
│   └── get_user_by_identity.py     # Поиск по identity_id
└── consumers/
    └── identity_events.py          # Обработчик событий из Identity-модуля
```

### Infrastructure

```
infrastructure/
├── models.py               # SQLAlchemy ORM: User, Customer, StaffMember
├── provider.py             # UserProvider (Dishka)
└── repositories/
    ├── customer_repository.py
    └── staff_member_repository.py
```

### Presentation

```
presentation/
├── router.py               # /users/me — профиль текущего пользователя
└── schemas.py              # Pydantic-модели
```

---

## `src/modules/geo/` — Географические справочники

### Domain

```
domain/
├── value_objects.py        # Country, Currency, Language, Subdivision (value objects)
├── interfaces.py           # ICountryRepository, ICurrencyRepository,
│                           # ILanguageRepository, ISubdivisionRepository
└── exceptions.py           # Доменные исключения
```

**Стандарты:**

| Сущность    | Стандарт    | Описание                          |
| ----------- | ----------- | --------------------------------- |
| Country     | ISO 3166-1  | Коды стран (alpha-2/3, numeric)   |
| Subdivision | ISO 3166-2  | Регионы/области с категоризацией  |
| Currency    | ISO 4217    | Коды валют, символы, точность     |
| Language    | IETF BCP 47 | Локали (uz, ru, en, uz-Cyrl, ...) |

### Application

```
application/
└── queries/
    ├── list_countries.py       # Список стран с переводами
    ├── list_currencies.py      # Список валют с переводами
    ├── list_languages.py       # Список языков
    ├── list_subdivisions.py    # Список регионов страны
    └── read_models.py          # DTO с мультиязычными переводами
```

### Infrastructure

```
infrastructure/
├── models.py               # SQLAlchemy ORM: Country, CountryTranslation,
│                           # Currency, CurrencyTranslation,
│                           # Language, Subdivision
└── repositories/
    ├── country.py
    ├── currency.py
    ├── language.py
    └── subdivision.py
```

### Presentation

```
presentation/
├── router.py               # Публичные read-only эндпоинты: /geo/*
└── dependencies.py         # GeoProvider (Dishka)
```

---

## `src/modules/cart/` — Корзина

Агрегат `Cart` с FSM `ACTIVE → FROZEN → ORDERED | MERGED` и дочерней сущностью `CartItem`. Поддерживает гостевые корзины через `anonymous_token` и слияние при логине.

```
cart/
├── domain/
│   ├── entities.py             # Cart (AggregateRoot), CartItem
│   ├── value_objects.py        # CartStatus, SkuSnapshot, CheckoutSnapshot
│   ├── events.py               # CartCreated/ItemAdded/Removed/Updated/Frozen/Merged/Ordered
│   ├── interfaces.py           # ICartRepository, ICartResolver
│   └── exceptions.py
├── application/
│   ├── commands/               # add_item, remove_item, update_quantity, clear,
│   │                           # freeze_for_checkout, unfreeze, merge_carts
│   ├── queries/                # get_cart, get_cart_summary
│   ├── cart_resolver.py        # CartResolver: identity_id или anonymous_token → Cart
│   └── constants.py            # MAX_CART_ITEMS=50, MAX_QTY_PER_ITEM=99, CHECKOUT_TTL=15min
├── infrastructure/
│   ├── models.py               # Cart, CartItem ORM
│   ├── provider.py             # CartProvider (Dishka)
│   ├── repository.py
│   └── adapters/
│       └── catalog_adapter.py  # Anti-corruption: SKU валидация через прямой JOIN на catalog/supplier
└── presentation/
    ├── router_customer.py      # /cart endpoints
    └── schemas.py
```

---

## `src/modules/logistics/` — Логистика

Агрегат `Shipment` с локальным FSM (DRAFT → BOOKING_PENDING → BOOKED → CANCEL_PENDING → CANCELLED/FAILED) и append-only `TrackingEvent`. Carrier lifecycle отслеживается отдельно от локального.

```
logistics/
├── domain/
│   ├── entities.py             # Shipment (AggregateRoot)
│   ├── value_objects.py        # ShipmentStatus, TrackingStatus, TrackingEvent,
│   │                           # Address, Parcel, ContactInfo, DeliveryQuote, Money,
│   │                           # ProviderCode, DeliveryType, EstimatedDelivery, CashOnDelivery
│   ├── events.py               # ShipmentCreated/BookingRequested/Booked/BookingFailed/
│   │                           # CancellationRequested/Cancelled/CancellationFailed/TrackingUpdated
│   ├── interfaces.py           # IShipmentRepository, ICarrierProvider, IQuoteService
│   └── exceptions.py
├── application/
│   ├── commands/               # create_shipment_from_quote, book_shipment, cancel_shipment,
│   │                           # append_tracking_event
│   ├── queries/                # get_shipment, list_shipments, get_quotes
│   ├── consumers/              # Обработчики событий заказа
│   └── dto.py                  # DeliveryQuoteRequest/Response, TrackingResponse
├── infrastructure/
│   ├── models.py               # Shipment, TrackingEvent ORM
│   ├── provider.py             # LogisticsInfraProvider, CommandProvider, QueryProvider
│   ├── repository.py
│   └── carriers/               # Конкретные провайдеры (CDEK, Russian Post, Yandex Delivery)
└── presentation/
    ├── router.py               # Внутренние API
    ├── router_webhooks.py      # Carrier webhooks
    └── schemas.py
```

---

## `src/modules/supplier/` — Поставщики

```
supplier/
├── domain/
│   ├── entities.py             # Supplier (тип CROSS_BORDER/LOCAL — immutable после create)
│   ├── value_objects.py        # SupplierType
│   ├── events.py               # SupplierCreated/Updated/Activated/Deactivated
│   ├── interfaces.py           # ISupplierRepository
│   ├── exceptions.py
│   └── constants.py
├── application/
│   ├── commands/               # create_supplier, update_supplier, activate, deactivate
│   └── queries/                # get_supplier, list_suppliers
├── infrastructure/
│   ├── models.py               # Supplier ORM (с ISO 3166-1/2 кодами)
│   └── repositories/
├── management/                 # Admin CLI bootstrap
└── presentation/
    ├── router.py
    ├── dependencies.py         # SupplierProvider (Dishka)
    └── schemas.py
```

---

## `src/modules/pricing/` — Ценообразование

Формульный движок ценообразования с AST, версионируемыми формулами и контекстами. См. ADR-004.

```
pricing/
├── domain/
│   ├── entities.py             # ProductPricingProfile (AggregateRoot)
│   ├── formula.py              # FormulaVersion (FSM: draft → published → archived)
│   │                           # с AST-валидацией (depth ≤ 64, JSON ≤ 4096 chars)
│   ├── formula_evaluator.py    # Pure-domain Decimal evaluator (op: +/-/*//,
│   │                           # fn: min/max/round/ceil/floor/abs/if)
│   ├── pricing_context.py      # PricingContext (с currency, rounding mode, active formula)
│   ├── variable.py             # Variable (scope: global/supplier/category/range/product_input,
│   │                           # data_type: decimal/integer/percent — immutable)
│   ├── variable_resolver.py    # Резолвинг переменных по scope-цепочке
│   ├── category_pricing_settings.py
│   ├── supplier_pricing_settings.py
│   ├── supplier_type_context_mapping.py
│   ├── value_objects.py        # ProfileStatus, FormulaStatus, VariableScope, RoundingMode
│   ├── events.py
│   ├── interfaces.py
│   └── exceptions.py
├── application/
│   ├── commands/               # create_variable, create_context, freeze/unfreeze_context,
│   │                           # set_context_global_value, upsert_formula_draft,
│   │                           # publish_formula_draft, discard_formula_draft, rollback_formula,
│   │                           # upsert_product_pricing_profile, upsert_supplier_pricing_settings,
│   │                           # upsert_category_pricing_settings,
│   │                           # upsert_supplier_type_context_mapping
│   └── queries/                # variables, contexts, formulas, preview_price,
│                               # get_product_pricing_profile, required_variables
├── infrastructure/
│   ├── models.py               # PricingContext, Variable, FormulaVersion,
│   │                           # ProductPricingProfile, SupplierPricingSettings,
│   │                           # CategoryPricingSettings, SupplierTypeContextMapping ORM
│   ├── provider.py
│   └── repositories/
└── presentation/
    ├── router.py                          # Profiles
    ├── router_variable.py
    ├── router_context.py
    ├── router_formula.py
    ├── router_preview.py                  # Превью расчёта цены
    ├── router_category_pricing.py
    ├── router_supplier_pricing.py
    ├── router_supplier_type_mapping.py
    └── schemas.py
```

---

## `src/modules/activity/` — Аналитика и трекинг

Lightweight трекер активности (не агрегат): Redis hot path → flush в partitioned PG таблицу. Считает trending, popular search, co-view scores для рекомендаций.

```
activity/
├── domain/
│   ├── entities.py             # UserActivityEvent (frozen attrs, не AggregateRoot)
│   ├── value_objects.py        # ActivityEventType (PRODUCT_VIEWED, PRODUCT_LIST_VIEWED,
│   │                           # SEARCH_PERFORMED)
│   └── interfaces.py           # IActivityTracker, IActivityFlusher, ICoViewReader
├── application/
│   └── queries/                # Чтение Redis sorted sets и co_view_scores
├── infrastructure/
│   ├── models.py               # UserActivityEvent (partitioned), ProductCoViewScore ORM
│   ├── redis_tracker.py        # Pipeline: lpush + zincrby (trending daily/weekly/category,
│   │                           # popular_queries, zero_results) с soft-cap LTRIM
│   ├── redis_query_service.py  # Чтение Redis-агрегатов
│   ├── history_reader.py       # Чтение истории из PG
│   ├── co_view_reader.py       # product_co_view_scores (FK CASCADE на products)
│   ├── repository.py
│   ├── tasks.py                # flush_activity_events (Redis → PG batch insert)
│   └── provider.py
└── presentation/
    ├── router_admin.py         # Admin-эндпоинты для аналитики
    └── schemas.py
```

---

## `src/infrastructure/` — Кросс-модульная инфраструктура

```
infrastructure/
├── database/
│   ├── base.py             # SQLAlchemy DeclarativeBase + naming conventions
│   ├── session.py          # AsyncSession factory
│   ├── uow.py              # UnitOfWork: транзакции + сбор доменных событий → Outbox
│   ├── registry.py         # Реестр моделей для Alembic
│   ├── provider.py         # Dishka-провайдер БД (engine, sessionmaker, UoW)
│   └── models/
│       ├── outbox.py       # OutboxMessage (Transactional Outbox)
│       └── failed_task.py  # FailedTask (Dead Letter Queue)
├── cache/
│   ├── redis.py            # RedisService (set/get/delete, TTL)
│   └── provider.py         # Dishka-провайдер кэша
├── security/
│   ├── jwt.py              # JwtTokenProvider (HS256, access + refresh)
│   ├── password.py         # Argon2PasswordHasher (+ bcrypt fallback)
│   ├── authorization.py    # PermissionResolver (Redis cache + recursive CTE)
│   ├── telegram.py         # Валидация Telegram init data
│   └── provider.py         # Dishka-провайдер безопасности
├── logging/
│   ├── adapter.py          # StructlogAdapter (ILogger)
│   ├── provider.py         # Dishka-провайдер логирования
│   ├── taskiq_middleware.py # Логирование TaskIQ-задач
│   └── dlq_middleware.py   # Dead Letter Queue middleware
├── outbox/
│   ├── relay.py            # Outbox Relay: FOR UPDATE SKIP LOCKED → handler dispatch
│   └── tasks.py            # Фоновая задача polling outbox
└── storage/
    └── factory.py          # S3-клиент (aiobotocore, ephemeral connections)
```

**Connection Pool:**

| Параметр      | Значение       |
| ------------- | -------------- |
| pool_size     | 15             |
| max_overflow  | 10             |
| pool_recycle  | 3600s          |
| pool_pre_ping | True           |
| isolation     | READ COMMITTED |

---

## `src/shared/` — Общий код

```
shared/
├── exceptions.py           # AppException → NotFoundError (404), BadRequestError (400),
│                           # UnauthorizedError (401), ForbiddenError (403),
│                           # ConflictError (409), ValidationError (400),
│                           # UnprocessableEntityError (422), ServiceUnavailableError (503)
├── context.py              # Request context (correlation ID via ContextVar)
├── schemas.py              # Общие Pydantic-модели
└── interfaces/
    ├── entities.py         # IBase, DomainEvent, AggregateRoot mixin
    ├── uow.py              # IUnitOfWork (Protocol: commit/rollback/flush/register_aggregate)
    ├── auth.py             # AuthContext (identity_id, session_id)
    ├── security.py         # ITokenProvider, IPasswordHasher, IPermissionResolver,
    │                       # IOIDCProvider, OIDCUserInfo
    ├── cache.py            # ICacheService (set/get/delete + TTL)
    ├── logger.py           # ILogger (bind/debug/info/warning/error/critical/exception)
    ├── blob_storage.py     # IBlobStorage (download/upload_stream, presigned URLs, CRUD)
    ├── storage.py          # IStorageFacade + PresignedUploadData
    └── config.py           # IStorageConfig (S3_BUCKET_NAME, S3_PUBLIC_BASE_URL)
```

---

## `tests/` — Тест-сьюты

```
tests/
├── conftest.py             # Общие фикстуры (testcontainers: PG, Redis, MinIO, RabbitMQ)
├── unit/                   # Юнит-тесты (domain entities, FSM, pure logic)
│   ├── conftest.py
│   ├── activity/           # Тесты Redis-трекера и read-моделей
│   ├── cart/               # Cart aggregate + CartItem FSM
│   ├── modules/
│   │   ├── catalog/        # domain entities, FSM, AST для атрибутов, slug, i18n
│   │   ├── identity/       # Identity, Session, Role, Invitation
│   │   ├── logistics/      # Shipment FSM, TrackingEvent дедуп
│   │   ├── pricing/        # Variable, FormulaVersion, AST validator + evaluator
│   │   ├── supplier/       # Supplier (immutable type guard)
│   │   └── user/           # Customer/StaffMember анонимизация
│   ├── infrastructure/
│   │   ├── logging/
│   │   ├── outbox/         # test_relay, test_tasks
│   │   └── security/       # test_telegram_validator, JWT, Argon2
│   └── shared/             # IUnitOfWork, exception envelope
├── integration/            # Интеграционные тесты (реальные контейнеры)
│   ├── conftest.py
│   ├── bootstrap/          # test_broker, test_worker_init
│   └── modules/
│       ├── activity/       # Redis trackers + flush в PG
│       ├── cart/           # cart endpoints + catalog adapter
│       ├── catalog/        # commands, repositories, storefront queries, search
│       ├── identity/       # login/register/refresh, RBAC
│       ├── pricing/        # формула publish/rollback, preview-расчёт
│       └── supplier/
├── e2e/                    # HTTP E2E тесты через AsyncClient
│   ├── conftest.py         # FastAPI + DI override
│   └── api/v1/
│       ├── test_auth.py            # Регистрация/логин
│       ├── test_auth_telegram.py   # Telegram Mini App
│       ├── test_brands.py          # CRUD брендов
│       ├── test_categories.py      # CRUD категорий
│       ├── test_users.py           # Профиль пользователя
│       ├── catalog/                # Products, variants, SKUs, attributes, storefront
│       ├── cart/                   # Cart endpoints
│       └── pricing/                # Variables, contexts, formulas, preview
├── architecture/           # Тесты архитектурных границ (pytest-archon)
│   └── test_boundaries.py  # Import-linting для всех 9 модулей
├── load/                   # Нагрузочные тесты (Locust)
│   ├── locustfile.py
│   └── scenarios/          # auth_flow, browse_catalog, mixed_workload
├── factories/              # Factory-методы для тестовых данных
│   ├── builders.py                 # Fluent-билдеры (общие)
│   ├── attribute_builder.py
│   ├── attribute_group_builder.py
│   ├── attribute_template_builder.py
│   ├── brand_builder.py
│   ├── cart_builder.py
│   ├── media_asset_builder.py
│   ├── product_builder.py
│   ├── sku_builder.py
│   ├── variant_builder.py
│   ├── catalog_factories.py        # ORM factory functions
│   ├── catalog_mothers.py          # Object Mother паттерн
│   ├── identity_mothers.py
│   ├── orm_factories.py
│   ├── schema_factories.py
│   ├── sku_mothers.py
│   ├── storage_factories.py
│   └── strategies/                 # Hypothesis-стратегии
└── fakes/                  # Mock-реализации
    ├── blob_storage.py             # InMemoryBlobStorage
    └── oidc_provider.py            # StubOIDCProvider
```

---

## `alembic/` — Миграции

```
alembic/
├── env.py                  # Async runner, подключается к Settings
├── script.py.mako          # Шаблон миграции
└── versions/
    └── 2026/03/
        ├── 13_..._init.py                          # Начальная схема (каталог)
        ├── 15_..._add_outbox_messages.py            # Transactional Outbox
        ├── 15_..._add_correlation_id_to_outbox.py   # Трассировка запросов
        ├── 16_..._create_iam_tables.py              # IAM: identities, sessions, roles, permissions
        ├── 16_..._seed_iam_roles_and_permissions.py # Начальные роли и права
        ├── 19_..._add_identity_deactivation_fields.py
        ├── 19_..._users_staff_separation.py         # Customer / StaffMember разделение
        ├── 20_..._add_telegram_credentials.py
        ├── 20_..._iam_multi_provider.py             # LinkedAccount для OAuth
        ├── 20_..._drop_telegram_credentials.py
        ├── 21_..._create_countries_table.py         # Geo: страны
        ├── 21_..._create_languages_table.py         # Geo: языки
        ├── 21_..._create_country_translations_table.py
        ├── 21_..._seed_languages_and_countries.py
        ├── 22_..._create_currencies_tables.py       # Geo: валюты
        ├── 22_..._seed_currencies.py
        ├── 22_..._refactor_countries_table.py
        ├── 22_..._add_missing_uz_cyrl_translations.py
        ├── 22_..._add_sku_currency_fk.py            # SKU → Currency FK
        └── 22_..._add_updated_at_to_geo_tables.py
```

Особенности:

- Дата-ориентированная организация версий (`YYYY/MM/`)
- Async-режим (`run_async_migrations`)
- Сравнение типов и server defaults включено
- Ruff-форматирование при генерации

---

## Docker Compose (dev)

| Сервис     | Image                     | Порт         |
| ---------- | ------------------------- | ------------ |
| PostgreSQL | postgres:18-alpine        | 5432         |
| Redis      | redis:8.4-alpine          | 6379         |
| RabbitMQ   | rabbitmq:4.2.4-management | 5672 / 15672 |
| MinIO      | minio/minio               | 9000 / 9001  |

---

## Ключевые архитектурные паттерны

| Паттерн                      | Где применяется                                                        |
| ---------------------------- | ---------------------------------------------------------------------- |
| **DDD / Bounded Context**    | 5 модулей: catalog, identity, user, geo, storage — независимые области |
| **CQRS**                     | commands/ и queries/ в каждом модуле — разделение записи и чтения      |
| **Repository + Data Mapper** | `BrandRepository`: ORM ↔ Domain, без утечки ORM в домен                |
| **Unit of Work**             | `IUnitOfWork` — транзакции через async context manager                 |
| **Transactional Outbox**     | Доменные события → `outbox_messages` → relay → consumers               |
| **Facade**                   | `StorageFacade` — единая точка входа для файлового хранилища           |
| **FSM (конечный автомат)**   | `MediaProcessingStatus` (лого), `ProductStatus` (жизненный цикл)       |
| **Claim Check**              | Presigned S3 URL + StorageFile registry (файл минует API)              |
| **Pessimistic Locking**      | `SELECT FOR UPDATE` в `get_for_update()` при финальной записи          |
| **Cache-Aside**              | Дерево категорий (Redis TTL=300s), права сессии (Redis + CTE fallback) |
| **NIST RBAC**                | Role → Permission с иерархией, кэширование в Redis                     |
| **Soft Link**                | Catalog ↔ Storage через `logo_file_id`, не FK                          |
| **Dependency Injection**     | Dishka: APP/REQUEST scope, провайдеры для всех слоёв                   |
| **Dead Letter Queue**        | `FailedTask` — персистентное хранение упавших задач                    |
| **Event-Driven Integration** | Identity → User через доменные события (outbox → consumer)             |
| **Retry**                    | `max_retries=3, retry_on_error=True` на TaskIQ-задачах                 |
