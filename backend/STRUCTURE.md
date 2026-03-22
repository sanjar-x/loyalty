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
│   ├── catalog/            # Каталог: бренды, категории, товары, атрибуты
│   ├── identity/           # IAM: аутентификация, роли, права, сессии
│   ├── user/               # Профили пользователей (Customer, StaffMember)
│   ├── geo/                # Географические справочники (страны, валюты, языки)
│   └── storage/            # Управление файлами (S3)
├── infrastructure/         # Кросс-модульная инфраструктура
└── shared/                 # Общий код и интерфейсы
```

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
├── entities.py             # Brand, Category, Product, SKU, Attribute, AttributeGroup,
│                           # AttributeValue, CategoryAttributeBinding (агрегаты)
├── value_objects.py        # MediaProcessingStatus (FSM), ProductStatus, AttributeDataType,
│                           # Money, RequirementLevel
├── exceptions.py           # BrandSlugConflictError, InvalidLogoStateException, ...
├── events.py               # Доменные события (logo processing, product lifecycle)
└── interfaces.py           # IBrandRepository, ICategoryRepository, IProductRepository, ...
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
├── commands/                          # 31 команда
│   ├── create_brand.py                # Создание бренда + резервация слота загрузки
│   ├── update_brand.py                # Обновление бренда
│   ├── delete_brand.py                # Удаление бренда
│   ├── confirm_brand_logo.py          # Подтверждение загрузки → постановка задачи
│   ├── create_category.py             # Создание категории + инвалидация кэша дерева
│   ├── update_category.py             # Обновление категории
│   ├── delete_category.py             # Удаление категории
│   ├── create_product.py              # Создание товара
│   ├── update_product.py              # Обновление товара
│   ├── delete_product.py              # Удаление товара
│   ├── change_product_status.py       # Смена статуса товара (FSM)
│   ├── add_sku.py                     # Добавление варианта SKU
│   ├── update_sku.py                  # Обновление SKU
│   ├── delete_sku.py                  # Удаление SKU
│   ├── create_attribute.py            # Создание атрибута
│   ├── update_attribute.py            # Обновление атрибута
│   ├── delete_attribute.py            # Удаление атрибута
│   ├── create_attribute_group.py      # Создание группы атрибутов
│   ├── update_attribute_group.py      # Обновление группы
│   ├── delete_attribute_group.py      # Удаление группы
│   ├── add_attribute_value.py         # Добавление значения атрибута
│   ├── update_attribute_value.py      # Обновление значения
│   ├── delete_attribute_value.py      # Удаление значения
│   ├── reorder_attribute_values.py    # Сортировка значений
│   ├── bind_attribute_to_category.py  # Привязка атрибута к категории
│   ├── unbind_attribute_from_category.py
│   ├── update_category_attribute_binding.py
│   ├── reorder_category_bindings.py   # Сортировка привязок
│   ├── bulk_update_requirement_levels.py
│   ├── assign_product_attribute.py    # Назначение атрибута товару
│   └── remove_product_attribute.py    # Удаление атрибута у товара
├── queries/                           # 17 запросов
│   ├── get_product.py                 # Получение товара
│   ├── list_products.py               # Список товаров
│   ├── list_product_attributes.py     # Атрибуты товара
│   ├── list_skus.py                   # SKU-варианты товара
│   ├── get_brand.py                   # Получение бренда
│   ├── list_brands.py                 # Список брендов
│   ├── get_category.py                # Получение категории
│   ├── list_categories.py             # Список категорий
│   ├── get_category_tree.py           # Дерево категорий (Redis-кэш, TTL 5 мин)
│   ├── list_category_bindings.py      # Привязки атрибутов к категории
│   ├── get_attribute.py               # Получение атрибута
│   ├── list_attributes.py             # Список атрибутов
│   ├── get_attribute_group.py         # Получение группы
│   ├── list_attribute_groups.py       # Список групп
│   ├── list_attribute_values.py       # Значения атрибута
│   ├── storefront.py                  # Витрина (публичный каталог/поиск)
│   └── read_models.py                 # DTO/read-модели
├── services/
│   └── media_processor.py            # BrandLogoProcessor: скачать → Pillow → WebP → S3
├── tasks.py                           # process_brand_logo_task (max_retries=3)
└── constants.py
```

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
├── models.py               # SQLAlchemy ORM: Brand, Category, Product, SKU,
│                           # Attribute, AttributeGroup, AttributeValue,
│                           # CategoryAttributeBinding, MediaAsset
├── queries.py              # SQL query-строители
└── repositories/
    ├── base.py             # Базовый репозиторий (shared CRUD)
    ├── brand.py            # BrandRepository (Data Mapper: ORM ↔ Domain)
    ├── category.py         # CategoryRepository
    ├── product.py          # ProductRepository
    ├── attribute.py        # AttributeRepository
    ├── attribute_group.py  # AttributeGroupRepository
    ├── attribute_value.py  # AttributeValueRepository
    ├── category_attribute_binding.py  # CategoryAttributeBindingRepository
    └── product_attribute_value.py     # ProductAttributeValueRepository
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
├── router_brands.py              # CRUD брендов
├── router_categories.py          # CRUD категорий + иерархия
├── router_products.py            # CRUD товаров + смена статуса
├── router_skus.py                # Управление SKU-вариантами
├── router_attributes.py          # CRUD атрибутов
├── router_attribute_groups.py    # CRUD групп атрибутов
├── router_attribute_values.py    # CRUD значений атрибутов
├── router_category_bindings.py   # Привязка атрибутов к категориям
├── router_product_attributes.py  # Назначение атрибутов товарам
├── router_storefront.py          # Публичная витрина (поиск, фильтрация)
├── schemas.py                    # Pydantic-схемы запросов/ответов
└── dependencies.py               # DI-провайдеры: BrandProvider, CategoryProvider,
                                  # AttributeProvider, ProductProvider, ...
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
- Гранулярные права (`catalog:manage`, `users:read`, ...)
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
    ├── user_repository.py
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

## `src/modules/storage/` — Хранилище файлов

```
storage/
├── domain/
│   ├── entities.py             # StorageFile (S3 object metadata)
│   ├── interfaces.py           # IStorageRepository (Protocol)
│   └── exceptions.py           # Доменные исключения
├── application/
│   ├── consumers/
│   │   └── brand_events.py     # Обработчик событий бренда (logo upload)
│   ├── commands/               # (зарезервировано)
│   └── queries/                # (зарезервировано)
├── infrastructure/
│   ├── models.py               # StorageFile (UUID7, bucket, object_key, versioning)
│   ├── repository.py           # StorageRepository
│   └── service.py              # S3-сервис
└── presentation/
    ├── facade.py               # StorageFacade — публичный API для других модулей
    ├── router.py               # HTTP-эндпоинты (заглушка)
    ├── schemas.py              # Pydantic-модели
    ├── dependencies.py         # StorageProvider (Dishka)
    └── tasks.py                # Фоновые задачи
```

**StorageFacade** (интерфейс для других модулей):

| Метод                        | Назначение                                            |
| ---------------------------- | ----------------------------------------------------- |
| `reserve_upload_slot()`      | Создать StorageFile в БД + вернуть presigned PUT URL  |
| `verify_upload(file_id)`     | Проверить наличие файла в S3 по внутреннему ID        |
| `update_object_metadata()`   | Обновить object_key/size/content_type после обработки |
| `register_processed_media()` | Зарегистрировать новый обработанный файл              |
| `verify_module_upload()`     | Проверить файл по S3-ключу напрямую                   |

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
│   ├── modules/catalog/
│   │   ├── domain/         # test_entities, test_attribute, test_category_attribute_binding, ...
│   │   └── application/
│   │       ├── commands/   # test_create_product, test_add_sku, test_change_product_status, ...
│   │       └── queries/    # test_get_product, test_list_products, test_storefront_helpers, ...
│   └── infrastructure/
│       ├── logging/
│       ├── outbox/         # test_relay, test_tasks
│       └── security/       # test_telegram_validator
├── integration/            # Интеграционные тесты (реальные контейнеры)
│   ├── conftest.py
│   ├── bootstrap/          # test_broker, test_worker_init
│   └── modules/
│       ├── catalog/
│       │   ├── application/commands/  # test_create_brand, test_confirm_brand_logo
│       │   ├── application/           # test_workers (TaskIQ end-to-end)
│       │   └── infrastructure/repositories/  # test_brand, test_category, ...
│       ├── identity/
│       │   ├── application/commands/  # test_login, test_register
│       │   ├── application/queries/   # test_get_identity_roles, test_list_roles, ...
│       │   └── infrastructure/repositories/  # test_identity_repo, test_session_repo, ...
│       └── user/
│           ├── application/commands/  # test_create_user
│           ├── application/queries/   # test_get_my_profile, test_get_user_by_identity
│           └── infrastructure/repositories/  # test_user_repo
├── e2e/                    # HTTP E2E тесты через AsyncClient
│   ├── conftest.py         # FastAPI + DI override
│   └── api/v1/
│       ├── test_auth.py          # Регистрация/логин
│       ├── test_brands.py        # CRUD брендов
│       ├── test_categories.py    # CRUD категорий
│       └── test_users.py         # Профиль пользователя
├── architecture/           # Тесты архитектурных границ (pytest-archon)
│   └── test_boundaries.py  # Import-linting для bounded contexts
├── load/                   # Нагрузочные тесты (Locust)
│   ├── locustfile.py
│   └── scenarios/
│       ├── auth_flow.py
│       ├── browse_catalog.py
│       └── mixed_workload.py
├── factories/              # Factory-методы для тестовых данных
│   ├── builders.py         # Fluent-билдеры
│   ├── catalog_mothers.py  # Brand, Category, Product, SKU, Attribute
│   ├── identity_mothers.py # Identity, Role, Permission, Session
│   ├── storage_mothers.py  # StorageFile
│   └── user_mothers.py     # User, Customer
└── fakes/                  # Mock-реализации
    ├── blob_storage.py     # InMemoryBlobStorage
    └── oidc_provider.py    # StubOIDCProvider
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
