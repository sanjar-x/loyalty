# Project Structure

E-commerce Catalog Service — async REST API на FastAPI + DDD архитектура.

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
├── modules/                # Функциональные модули (DDD bounded contexts)
│   ├── catalog/            # Каталог: бренды, категории, товары
│   ├── storage/            # Управление файлами
│   └── order/              # Заказы (заглушка)
├── infrastructure/         # Кросс-модульная инфраструктура
└── shared/                 # Общий код и интерфейсы
```

---

## `src/bootstrap/` — Инициализация

| Файл           | Назначение                                                             |
| -------------- | ---------------------------------------------------------------------- |
| `config.py`    | `Settings` (Pydantic): БД, Redis, S3, JWT, CORS                        |
| `container.py` | Dishka IoC-контейнер, регистрация всех провайдеров                     |
| `web.py`       | Фабрика FastAPI-приложения: lifespan, middleware, роутеры              |
| `broker.py`    | TaskIQ `AioPikaBroker` для RabbitMQ                                    |
| `worker.py`    | Точка входа TaskIQ-воркера; порядок init критичен (контейнер → задачи) |
| `logger.py`    | Конфигурация Structlog                                                 |

---

## `src/api/` — API-слой

```
api/
├── router.py               # Главный роутер — подключает все модули
├── exceptions/
│   └── handlers.py         # Глобальные обработчики HTTP-ошибок
└── middlewares/
    └── logger.py           # Логирование access-запросов
```

---

## `src/modules/catalog/` — Каталог (основной модуль)

### Domain

```
domain/
├── entities.py             # Brand, Category (агрегаты)
├── value_objects.py        # MediaProcessingStatus (FSM enum)
├── exceptions.py           # BrandSlugConflictError, InvalidLogoStateException, ...
└── interfaces.py           # IBrandRepository, ICategoryRepository, IProductRepository
```

**Brand FSM** (`MediaProcessingStatus`):

```
PENDING_UPLOAD → PROCESSING → COMPLETED
                           ↘ FAILED
PROCESSING → PENDING_UPLOAD   (revert при ошибке брокера)
```

Методы Brand: `create()`, `init_logo_upload()`, `confirm_logo_upload()`,
`complete_logo_processing()`, `fail_logo_processing()`, `revert_logo_upload()`

### Application

```
application/
├── commands/
│   ├── create_brand.py         # Создание бренда + резервация слота загрузки
│   ├── confirm_brand_logo.py   # Подтверждение загрузки → постановка задачи в брокер
│   └── create_category.py      # Создание категории + инвалидация кэша дерева
├── queries/
│   └── get_category_tree.py    # Дерево категорий (Redis-кэш, TTL 5 мин)
├── services/
│   └── media_processor.py      # BrandLogoProcessor: скачать → Pillow → WebP → S3
└── tasks.py                    # process_brand_logo_task (max_retries=3)
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
├── models.py               # SQLAlchemy ORM: Brand, Category, Product, SKU, Attribute, ...
├── queries.py              # Query-строители
└── repositories/
    ├── brand.py            # BrandRepository (Data Mapper: ORM ↔ Domain)
    ├── category.py         # CategoryRepository
    ├── product.py          # ProductRepository
    └── attribute.py        # AttributeRepository
```

**ORM-модели:**

| Модель       | Ключевые поля                                                              |
| ------------ | -------------------------------------------------------------------------- |
| `Brand`      | name (unique), slug, logo_file_id, logo_status, logo_url                   |
| `Category`   | parent_id, full_slug, level, sort_order                                    |
| `Product`    | slug, brand_id, category_id, attributes (JSONB), version (optimistic lock) |
| `SKU`        | sku_code, variant_hash (unique), price, attributes_cache                   |
| `Attribute`  | code (unique), data_type, ui_type, is_dictionary                           |
| `MediaAsset` | role, sort_order, content_type                                             |

### Presentation

```
presentation/
├── router.py               # HTTP-эндпоинты каталога
├── schemas.py              # Pydantic-схемы запросов/ответов
└── dependencies.py         # DI-провайдеры для каталога
```

---

## `src/modules/storage/` — Хранилище файлов

```
storage/
├── domain/
│   └── interfaces.py           # IStorageRepository (Protocol)
├── infrastructure/
│   ├── models.py               # StorageObject (UUID7, bucket, object_key, versioning)
│   ├── repository.py           # StorageObjectRepository
│   └── service.py
└── presentation/
    ├── facade.py               # StorageFacade — публичный API для других модулей
    ├── router.py
    ├── schemas.py
    ├── dependencies.py
    └── tasks.py
```

**StorageFacade** (интерфейс для других модулей):

| Метод                        | Назначение                                             |
| ---------------------------- | ------------------------------------------------------ |
| `reserve_upload_slot()`      | Создать StorageObject в БД + вернуть presigned PUT URL |
| `verify_upload(file_id)`     | Проверить наличие файла в S3 по внутреннему ID         |
| `update_object_metadata()`   | Обновить object_key/size/content_type после обработки  |
| `register_processed_media()` | Зарегистрировать новый обработанный файл               |
| `verify_module_upload()`     | Проверить файл по S3-ключу напрямую                    |

---

## `src/modules/order/` — Заказы (заглушка)

Структура создана, логика не реализована.

---

## `src/infrastructure/` — Кросс-модульная инфраструктура

```
infrastructure/
├── database/
│   ├── base.py             # SQLAlchemy DeclarativeBase
│   ├── session.py          # AsyncSession factory
│   ├── uow.py              # UnitOfWork реализация
│   ├── registry.py         # Реестр моделей для Alembic
│   └── provider.py         # Dishka-провайдер БД
├── cache/
│   ├── redis.py            # RedisService (set/get/delete, TTL)
│   └── provider.py         # Dishka-провайдер кэша
├── security/
│   ├── jwt.py              # JWT-токены
│   ├── password.py         # Bcrypt хэширование
│   ├── permissions.py      # Проверка прав
│   └── provider.py
└── storage/
    └── factory.py          # S3-клиент (aiobotocore)
```

---

## `src/shared/` — Общий код

```
shared/
├── exceptions.py           # ValidationError, NotFoundError, ConflictError
├── context.py              # Request context (correlation ID)
└── interfaces/
    ├── uow.py              # IUnitOfWork (Protocol: commit/rollback/flush)
    ├── blob_storage.py     # IBlobStorage (download_stream, upload_stream, presigned URLs)
    ├── storage.py          # IStorageFacade + PresignedUploadData
    ├── cache.py            # ICacheService (set/get/delete + TTL)
    ├── entities.py         # Базовые интерфейсы сущностей
    └── security.py         # Интерфейсы безопасности
```

---

## `tests/` — Тест-сьюты

```
tests/
├── conftest.py             # Общие фикстуры (testcontainers: PG, Redis, MinIO, RabbitMQ)
├── unit/                   # Юнит-тесты (domain entities, FSM, pure logic)
├── integration/            # Интеграционные тесты (реальные контейнеры)
│   └── modules/catalog/application/
│       └── test_workers.py # Тест TaskIQ-задачи end-to-end
├── e2e/                    # HTTP E2E тесты через AsyncClient
│   └── conftest.py         # FastAPI + DI override
├── architecture/           # Тесты архитектурных границ (import-linter / pytest-archon)
├── factories/              # Factory-методы для тестовых данных
└── load/                   # Нагрузочные тесты (Locust)
```

---

## `alembic/` — Миграции

```
alembic/
├── env.py                  # Async runner, подключается к Settings
├── script.py.mako          # Шаблон миграции
└── versions/
    └── 2026/03/
        └── 13_1402_04_9108a4a20a82_init.py   # Начальная схема (13 таблиц)
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

| Паттерн                      | Где применяется                                                    |
| ---------------------------- | ------------------------------------------------------------------ |
| **DDD / Bounded Context**    | Модули catalog, storage, order — независимые области               |
| **Repository + Data Mapper** | `BrandRepository`: ORM ↔ Domain, без утечки ORM в домен            |
| **Unit of Work**             | `IUnitOfWork` — транзакции через async context manager             |
| **Facade**                   | `StorageFacade` — единая точка входа для файлового хранилища       |
| **FSM (конечный автомат)**   | `MediaProcessingStatus` для логотипа бренда                        |
| **Claim Check**              | Presigned S3 URL + StorageObject registry (файл минует API)        |
| **Pessimistic Locking**      | `SELECT FOR UPDATE` в `get_for_update()` при финальной записи      |
| **Two-phase commit**         | DB commit → broker dispatch (с rollback при недоступности брокера) |
| **Soft Link**                | Catalog ссылается на Storage через `logo_file_id`, не FK           |
| **Dependency Injection**     | Dishka: провайдеры для всех слоёв, `@inject` в TaskIQ-задачах      |
| **Retry**                    | `max_retries=3, retry_on_error=True` на TaskIQ-задачах             |
| **Cache-aside**              | Дерево категорий: Redis TTL=300s, инвалидация при изменении        |
