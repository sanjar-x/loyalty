# ImageBackend Roadmap — Design Spec

**Дата:** 2026-03-27
**Источник:** `image_backend/flow.md`
**Подход:** Strict Bottom-Up (послойный)
**Стек:** Python 3.14, FastAPI, Dishka, TaskIQ + RabbitMQ, Pillow, aiobotocore, PostgreSQL, Redis, Alembic
**Тесты:** Unit only
**Деплой:** Вне скоупа

---

## Обзор

ImageBackend — микросервис обработки и хранения изображений. Реализует два flow:

1. **Flow 1 — Загрузка изображения продукта:** Frontend → presigned URL → direct upload в S3 → confirm → background processing (resize/WebP) → SSE уведомление → привязка mediaId к продукту
2. **Flow 2 — Импорт из внешнего URL:** Frontend → ImageBackend скачивает, обрабатывает, загружает в S3 → возвращает готовый результат синхронно

Roadmap разбит на 7 фаз. Каждая фаза — отдельный PR. Зависимости строго однонаправленные.

---

## Граф зависимостей фаз

```
Phase 1: Shared Kernel        <- нет зависимостей
Phase 2: Domain                <- Phase 1
Phase 3: Infrastructure        <- Phase 1, 2
Phase 4: Application           <- Phase 1, 2
Phase 5: Presentation          <- Phase 1–4
Phase 6: Bootstrap & Wiring    <- Phase 1–5
Phase 7: Unit Tests            <- Phase 1–4
```

---

## Структура проекта

```
src/
├── shared/                    # Phase 1
│   ├── exceptions.py
│   ├── schemas.py
│   ├── context.py
│   └── interfaces/
│       ├── blob_storage.py
│       ├── config.py
│       ├── uow.py
│       ├── logger.py
│       ├── storage.py
│       └── entities.py
├── modules/
│   └── storage/
│       ├── domain/            # Phase 2
│       │   ├── value_objects.py
│       │   ├── entities.py
│       │   ├── interfaces.py
│       │   └── exceptions.py
│       ├── infrastructure/    # Phase 3
│       │   ├── models.py
│       │   ├── repository.py
│       │   └── service.py
│       ├── application/       # Phase 4
│       │   └── commands/
│       │       └── process_image.py
│       └── presentation/      # Phase 5
│           ├── schemas.py
│           ├── router.py
│           ├── tasks.py
│           ├── sse.py
│           ├── facade.py
│           └── dependencies.py
├── infrastructure/            # Phase 3
│   ├── database/
│   │   ├── base.py
│   │   ├── session.py
│   │   ├── uow.py
│   │   ├── registry.py
│   │   └── provider.py
│   ├── cache/
│   │   ├── redis.py
│   │   └── provider.py
│   ├── storage/
│   │   └── factory.py
│   └── logging/
│       ├── adapter.py
│       ├── provider.py
│       ├── taskiq_middleware.py
│       └── dlq_middleware.py
├── api/                       # Phase 5
│   ├── router.py
│   ├── dependencies/
│   │   └── auth.py
│   ├── exceptions/
│   │   └── handlers.py
│   └── middlewares/
│       └── logger.py
└── bootstrap/                 # Phase 6
    ├── config.py
    ├── container.py
    ├── web.py
    ├── broker.py
    ├── worker.py
    ├── logger.py
    └── scheduler.py

tests/                         # Phase 7
└── unit/
    └── modules/storage/
        ├── domain/
        │   ├── test_entities.py
        │   └── test_value_objects.py
        ├── application/
        │   └── test_process_image.py
        └── presentation/
            └── test_sse.py
```

---

## Phase 1: Shared Kernel

Фундамент. Только абстракции, ноль реализаций. Чистый Python + Pydantic (для schemas).

### 1.1 Исключения (`shared/exceptions.py`)

Иерархия бизнес-исключений:

| Класс | HTTP-код | Назначение |
|---|---|---|
| `AppError` (base) | — | Базовый класс |
| `NotFoundError` | 404 | Ресурс не найден |
| `ValidationError` | 422 | Невалидные данные |
| `UnauthorizedError` | 401 | Нет/невалидный API-key |
| `ServiceUnavailableError` | 503 | S3/Redis/DB недоступен |

Каждое исключение содержит: `message: str`, `error_code: str`, `details: dict`.

### 1.2 Интерфейсы (`shared/interfaces/`)

| Файл | Protocol | Методы |
|---|---|---|
| `blob_storage.py` | `IBlobStorage` | `download_stream`, `upload_stream`, `generate_presigned_put_url`, `object_exists`, `delete_object`, `delete_objects`, `get_object_metadata`, `list_objects`, `copy_object`, `get_presigned_url`, `get_presigned_upload_url` |
| `config.py` | `IStorageConfig` | `S3_BUCKET_NAME: str`, `S3_PUBLIC_BASE_URL: str` |
| `uow.py` | `IUnitOfWork` | `commit()`, `rollback()`, context manager |
| `logger.py` | `ILogger` | `info()`, `warning()`, `error()`, `exception()`, `bind()` |
| `storage.py` | `IStorageFacade`, `PresignedUploadData` | `request_upload()`, `request_direct_upload()`, `reserve_upload_slot()`, `verify_upload()`, `verify_module_upload()`, `register_processed_media()`, `update_object_metadata()` |
| `entities.py` | Базовые типы | Общие типы при необходимости |

### 1.3 Базовая схема (`shared/schemas.py`)

`CamelModel(BaseModel)` — автоматическая конвертация snake_case полей в camelCase JSON-ответы. Все API-схемы наследуют от неё.

### 1.4 Request context (`shared/context.py`)

Контекстные переменные через `contextvars` (request ID и т.п.).

---

## Phase 2: Domain

Чистая бизнес-логика модуля `storage`. Зависит только от Phase 1.

### 2.1 Value Objects (`domain/value_objects.py`)

```python
class StorageStatus(StrEnum):
    PENDING_UPLOAD = "PENDING_UPLOAD"
    PROCESSING     = "PROCESSING"
    COMPLETED      = "COMPLETED"
    FAILED         = "FAILED"
```

Свойство `is_terminal` — `True` для `COMPLETED`/`FAILED`. Используется в SSE для закрытия потока.

### 2.2 Entity (`domain/entities.py`)

`StorageFile` — attrs-dataclass (не Pydantic, не ORM):

| Поле | Тип | Default | Назначение |
|---|---|---|---|
| `id` | `UUID` | — | UUID v7 (хронологический) |
| `bucket_name` | `str` | — | Имя S3-бакета |
| `object_key` | `str` | — | Путь в бакете |
| `content_type` | `str` | — | MIME-тип |
| `size_bytes` | `int` | `0` | Размер файла в байтах |
| `status` | `StorageStatus` | `PENDING_UPLOAD` | Жизненный цикл обработки |
| `url` | `str \| None` | `None` | Публичный URL после обработки |
| `image_variants` | `list[dict] \| None` | `None` | Метаданные вариантов `[{size, width, height, url}]` |
| `filename` | `str \| None` | `None` | Оригинальное имя файла |
| `is_latest` | `bool` | `True` | Активная версия |
| `owner_module` | `str \| None` | `None` | Модуль-владелец |
| `version_id` | `str \| None` | `None` | S3 version ID |
| `etag` | `str \| None` | `None` | MD5 hash от S3 |
| `content_encoding` | `str \| None` | `None` | HTTP Content-Encoding |
| `cache_control` | `str \| None` | `None` | HTTP Cache-Control |
| `created_at` | `datetime \| None` | `None` | Время создания |
| `last_modified_in_s3` | `datetime \| None` | `None` | Последнее изменение в S3 |

Фабричный метод: `StorageFile.create(bucket_name, object_key, content_type, ...)` — генерирует UUID v7, статус `PENDING_UPLOAD`.

### 2.3 Repository Interface (`domain/interfaces.py`)

`IStorageRepository(ABC)`:

| Метод | Назначение |
|---|---|
| `add(storage_file)` | Сохранить новую запись |
| `update(storage_file)` | Обновить существующую |
| `get_by_id(uuid)` | Найти по PK |
| `get_by_key(uuid)` | Алиас get_by_id |
| `get_active_by_key(bucket, key)` | Активная версия по S3-пути |
| `get_all_versions(bucket, key)` | Все версии файла |
| `deactivate_previous_versions(bucket, key)` | Деактивировать старые версии |
| `mark_as_deleted(bucket, key)` | Soft-delete |
| `list_pending_expired(older_than)` | Orphan'ы для garbage collection |

### 2.4 Domain Exceptions (`domain/exceptions.py`)

- `StorageFileNotFoundError(AppError)` — файл не найден
- `StorageFileAlreadyProcessedError(AppError)` — повторная обработка

---

## Phase 3: Infrastructure

Реализации всех портов. Зависит от Phase 1 + 2.

### 3.1 Database (общая инфраструктура)

| Файл | Назначение |
|---|---|
| `database/base.py` | Декларативная `Base` для SQLAlchemy ORM |
| `database/session.py` | Хелперы для `AsyncSession` |
| `database/uow.py` | `UnitOfWork(IUnitOfWork)` через `AsyncSession` |
| `database/registry.py` | Реестр моделей |
| `database/provider.py` | Dishka-провайдер: `AsyncEngine` (APP), `async_sessionmaker` (APP), `AsyncSession` (REQUEST), `IUnitOfWork` (REQUEST) |

Конфигурация пула: `pool_size=15`, `max_overflow=10`, `pool_pre_ping=True`, `pool_recycle=3600`, `READ COMMITTED`.

### 3.2 ORM модель (`storage/infrastructure/models.py`)

`StorageObject` — таблица `storage_objects`:

- PK: UUID v7 (`default=uuid.uuid7`)
- `status`: PostgreSQL ENUM `storage_status_enum`
- `image_variants`: `JSONB` (массив `{size, width, height, url}`)
- `created_at`: `TIMESTAMP(timezone=True)`, `server_default=func.now()`
- Partial unique index: `uix_storage_active_object` на `(bucket_name, object_key) WHERE is_latest = true`

### 3.3 Alembic миграция

`alembic/versions/001_create_storage_objects.py`:
1. Создать ENUM `storage_status_enum`
2. Создать таблицу `storage_objects`
3. Создать partial unique index

### 3.4 Repository (`storage/infrastructure/repository.py`)

`StorageObjectRepository(IStorageRepository)` — Data Mapper:
- `_to_domain(orm) -> StorageFile` — ORM -> domain
- `_to_orm(entity) -> StorageObject` — domain -> ORM
- Все методы из `IStorageRepository` через SQLAlchemy `select`/`update`

### 3.5 S3 Service (`storage/infrastructure/service.py`)

`S3StorageService(IBlobStorage)` — обёртка над `aiobotocore`:
- Multipart upload (chunks 5 MB, abort при ошибке)
- `_handle_client_error` — S3 `ClientError` -> `NotFoundError`/`ServiceUnavailableError`
- Batch delete (chunks 1000 ключей)

### 3.6 S3 Client Factory (`infrastructure/storage/factory.py`)

`S3ClientFactory` — ephemeral клиенты через `aiobotocore.session`:
- `AioConfig`: `max_pool_connections=1`, `connect_timeout=5s`, `read_timeout=60s`, `retries=3`
- Один клиент на REQUEST scope

### 3.7 Cache (`infrastructure/cache/`)

- `redis.py` — создание async Redis клиента
- `provider.py` — Dishka-провайдер: `Redis` (APP scope)

### 3.8 SSE Manager (`storage/presentation/sse.py`)

`SSEManager` — Redis pub/sub:
- Канал: `media:status:{storage_object_id}`
- `publish(id, data)` — JSON в канал
- `subscribe(id)` — async generator, timeout 120s, poll 1s
- Терминальные статусы завершают подписку

### 3.9 Logging (`infrastructure/logging/`)

| Файл | Назначение |
|---|---|
| `adapter.py` | `StructlogAdapter(ILogger)` — реализация порта |
| `provider.py` | Dishka-провайдер |
| `taskiq_middleware.py` | Логирование TaskIQ задач |
| `dlq_middleware.py` | Dead Letter Queue — упавшие задачи в БД |

---

## Phase 4: Application

Бизнес-логика обработки изображений. Чистые функции, без I/O, без async.

### 4.1 Image Processing (`application/commands/process_image.py`)

Три функции:

| Функция | Вход | Выход | Логика |
|---|---|---|---|
| `resize_to_fit(img, max_w, max_h)` | `PIL.Image` + размеры | `PIL.Image` | `thumbnail()` с `Resampling.LANCZOS` |
| `convert_to_webp(raw_data, quality, lossless, max_size)` | `bytes` | `bytes` | RGBA/LA/P -> RGBA, иначе RGB. Сохранение в WebP |
| `build_variants(raw_data, storage_object_id, public_base_url)` | `bytes`, `UUID`, `str` | `(main_bytes, variants_meta, variants_data)` | Main (lossless) + 3 варианта |

### Варианты размеров

| Имя | Max Size | Суффикс S3 | Quality | Назначение |
|---|---|---|---|---|
| `thumbnail` | 150x150 | `_thumb` | 85 | Превью в списках |
| `medium` | 600x600 | `_md` | 85 | Карточка товара |
| `large` | 1200x1200 | `_lg` | 85 | Полноразмерный просмотр |

### S3 key schema

- Raw upload: `raw/{storage_object_id}/{filename}`
- Main processed: `public/{storage_object_id}.webp`
- Variant: `public/{storage_object_id}_{suffix}.webp`

---

## Phase 5: Presentation

HTTP-эндпоинты, TaskIQ-задачи, DI, фасад.

### 5.1 API Schemas (`presentation/schemas.py`)

Все наследуют `CamelModel`:

| Схема | Эндпоинт | Ключевые поля |
|---|---|---|
| `UploadRequest` | `POST /upload` | `content_type`, `filename?` |
| `UploadResponse` | `POST /upload` | `storage_object_id`, `presigned_url`, `expires_in=300` |
| `ConfirmResponse` | `POST /{id}/confirm` | `storage_object_id`, `status="processing"` |
| `MediaVariant` | Вложенный | `size`, `width`, `height`, `url` |
| `StatusEventData` | SSE | `status`, `storage_object_id`, `url?`, `variants[]`, `error?` |
| `ExternalImportRequest` | `POST /external` | `url` |
| `ExternalImportResponse` | `POST /external` | `storage_object_id`, `url`, `variants[]` |
| `MetadataResponse` | `GET /{id}` | `storage_object_id`, `status`, `url?`, `content_type?`, `size_bytes`, `variants[]`, `created_at?` |
| `DeleteResponse` | `DELETE /{id}` | `deleted: bool` |

### 5.2 Router (`presentation/router.py`) — 6 эндпоинтов

| # | Эндпоинт | Метод | Код | Flow.md | Логика |
|---|---|---|---|---|---|
| 1 | `/media/upload` | POST | 201 | Step 1 | Создать `StorageFile(PENDING_UPLOAD)`, presigned PUT URL (TTL 300s), key: `raw/{id}/{filename}` |
| 2 | `/media/{id}/confirm` | POST | 202 | Step 3 | HEAD check в S3, `PENDING_UPLOAD -> PROCESSING`, dispatch `process_image_task` |
| 3 | `/media/{id}/status` | GET | SSE | Step 5 | Текущий статус из БД, подписка Redis pub/sub, close на terminal |
| 4 | `/media/{id}` | GET | 200 | Step 5 | Метаданные + варианты из БД |
| 5 | `/media/{id}` | DELETE | 200 | — | Идемпотентный. S3 cleanup (raw + main + variants), soft-delete в БД |
| 6 | `/media/external` | POST | 201 | Flow 2 | Download (httpx, 30s, max 10 MB), process in thread, upload S3, status=COMPLETED |

### 5.3 Background Tasks (`presentation/tasks.py`)

**`process_image_task`:**
- Queue: `image_processing`
- Retry: `max_retries=2`, `retry_on_error=True`
- Timeout: `300s`
- Pipeline: download raw -> `build_variants` in thread -> upload main + variants -> delete raw -> update DB (COMPLETED) -> publish SSE
- On error: `status=FAILED`, publish SSE error, re-raise for retry

**`cleanup_orphans_task`:**
- Queue: `maintenance`
- Cron: `0 */6 * * *` (каждые 6 часов)
- Timeout: `600s`
- Logic: найти `PENDING_UPLOAD` старше 24h -> delete S3 (best-effort) -> soft-delete DB

### 5.4 Facade (`presentation/facade.py`)

`StorageFacade(IStorageFacade)` — межмодульный API:

| Метод | Назначение |
|---|---|
| `request_upload(module, entity_id, filename)` | Presigned POST URL |
| `request_direct_upload(module, entity_id, filename, content_type)` | Presigned PUT URL |
| `reserve_upload_slot(module, entity_id, filename, content_type)` | PUT URL + pre-register в БД |
| `verify_upload(file_id)` | Проверка загрузки по ID |
| `verify_module_upload(module, entity_id, object_key)` | Проверка по S3 key |
| `register_processed_media(module, entity_id, key, type, size)` | Регистрация обработанного файла |
| `update_object_metadata(file_id, key, size, type)` | Обновление метаданных |

### 5.5 DI Provider (`presentation/dependencies.py`)

`StorageProvider` — Dishka:

| Provide | Scope | Тип |
|---|---|---|
| `S3ClientFactory` | APP | Фабрика |
| `AioBaseClient` | REQUEST | Ephemeral S3 клиент |
| `IStorageRepository -> StorageObjectRepository` | REQUEST | Репозиторий |
| `IBlobStorage -> S3StorageService` | REQUEST | S3 сервис |
| `SSEManager` | APP | Redis pub/sub |
| `IStorageFacade -> StorageFacade` | REQUEST | Фасад |

### 5.6 API Layer (общий)

| Файл | Назначение |
|---|---|
| `api/router.py` | Root router, `Depends(verify_api_key)`, include `media_router` prefix `/media` |
| `api/dependencies/auth.py` | `verify_api_key` — `X-API-Key` header или `api_key` query. `hmac.compare_digest`. Dev без ключа — пропускает |
| `api/exceptions/handlers.py` | `AppError` -> HTTP: `NotFoundError->404`, `ValidationError->422`, `UnauthorizedError->401`, `ServiceUnavailableError->503` |
| `api/middlewares/logger.py` | Access logger — structlog request/response logging |

---

## Phase 6: Bootstrap & Wiring

Точки входа и сборка.

### 6.1 Config (`bootstrap/config.py`)

`Settings(BaseSettings)` — pydantic-settings:

| Группа | Переменные |
|---|---|
| App | `PROJECT_NAME`, `VERSION`, `ENVIRONMENT` (dev/test/prod), `DEBUG`, `API_V1_STR="/api/v1"` |
| CORS | `CORS_ORIGINS` (comma-separated -> list) |
| PostgreSQL | `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` -> computed `database_url` (postgresql+asyncpg) |
| Redis | `REDISHOST`, `REDISPORT`, `REDISUSER`, `REDISPASSWORD`, `REDISDATABASE` -> computed `redis_url` |
| S3 | `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`, `S3_BUCKET_NAME`, `S3_PUBLIC_BASE_URL` |
| RabbitMQ | `RABBITMQ_PRIVATE_URL` |
| Auth | `INTERNAL_API_KEY` (SecretStr) |
| Processing | `SSE_TIMEOUT=120`, `SSE_HEARTBEAT=15`, `PROCESSING_TIMEOUT=300`, `MAX_FILE_SIZE=50MB`, `PRESIGNED_URL_TTL=300` |

`Settings` реализует `IStorageConfig` через duck typing (Protocol).

### 6.2 Logger (`bootstrap/logger.py`)

`setup_logging()` — structlog: JSON в prod, цветной вывод в dev.

### 6.3 DI Container (`bootstrap/container.py`)

```python
make_async_container(
    ConfigProvider(),      # Settings, IStorageConfig
    LoggingProvider(),     # ILogger
    DatabaseProvider(),    # Engine, Session, IUnitOfWork
    CacheProvider(),       # Redis
    StorageProvider(),     # S3, Repository, SSEManager, Facade
)
```

### 6.4 Broker (`bootstrap/broker.py`)

`AioPikaBroker` (TaskIQ + RabbitMQ):
- Exchange: `taskiq_rpc_exchange`
- Queue: `taskiq_background_jobs`
- QoS: `10`
- Middleware: `LoggingTaskiqMiddleware`

### 6.5 Worker (`bootstrap/worker.py`)

Порядок инициализации (критичен):
1. Создать DI container + `setup_dishka(container, broker)`
2. DLQ middleware (отдельный engine, `pool_size=2`)
3. Импортировать `tasks.py` (регистрация задач)
4. `WORKER_STARTUP` / `WORKER_SHUTDOWN` events

### 6.6 Web Factory (`bootstrap/web.py`)

`create_app() -> FastAPI`:
1. `FastAPI(lifespan=lifespan)`
2. CORS middleware
3. Access logger middleware
4. Exception handlers
5. Router с prefix `/api/v1`
6. `GET /health -> {"status": "ok"}`
7. `setup_dishka(container, app)`

Lifespan: startup broker (если не worker) -> yield -> shutdown broker -> close container.

### 6.7 Корневые файлы

| Файл | Назначение |
|---|---|
| `main.py` | `app = create_app()` — ASGI entry point |
| `pyproject.toml` | Python >=3.14, зависимости, ruff config |
| `.env.example` | Шаблон переменных окружения |
| `Dockerfile` | `python:3.14-slim-trixie`, uv, uvicorn port 8001 |
| `docker-compose.yml` | PostgreSQL 18, Redis 8.4, RabbitMQ 4.2, MinIO latest |
| `alembic.ini` + `alembic/` | Миграции |

---

## Phase 7: Unit Tests

Unit-тесты для domain и application слоёв.

### Структура

```
tests/
└── unit/
    └── modules/storage/
        ├── domain/
        │   ├── test_entities.py
        │   └── test_value_objects.py
        ├── application/
        │   └── test_process_image.py
        └── presentation/
            └── test_sse.py
```

### Покрытие

| Файл | Кейсы |
|---|---|
| `test_entities.py` | `create()` генерирует UUID; статус по умолчанию `PENDING_UPLOAD`; все поля заполняются корректно |
| `test_value_objects.py` | `is_terminal` для каждого статуса; значения enum == строки |
| `test_process_image.py` | `convert_to_webp`: JPEG/PNG -> WebP bytes; `resize_to_fit`: пропорции сохраняются; `build_variants`: 3 варианта, правильные S3 keys и URL |
| `test_sse.py` | `channel_name` формирует правильный ключ Redis-канала |

### Конфигурация

- `pytest` + `pytest-asyncio` (asyncio_mode = "auto")
- `pytest-cov` для coverage
- Тесты не требуют внешних зависимостей (PostgreSQL, Redis, S3)
