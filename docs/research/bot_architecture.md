# Архитектура Telegram-бота на Aiogram 3.x: Полное исследование

> **Версия документа:** 1.0
> **Дата:** 2026-03-19
> **Aiogram:** 3.26.x
> **Python:** 3.12+
> **Источники:** официальная документация aiogram, GitHub-шаблоны, community best practices

---

## Содержание

1. [Структура проекта](#1-структура-проекта)
2. [Роутеры и хэндлеры](#2-роутеры-и-хэндлеры)
3. [Цепочка Middleware](#3-цепочка-middleware)
4. [FSM (Конечный автомат)](#4-fsm-конечный-автомат)
5. [Dependency Injection](#5-dependency-injection)
6. [Конфигурация](#6-конфигурация)
7. [Клавиатуры и CallbackData](#7-клавиатуры-и-callbackdata)
8. [Обработка ошибок](#8-обработка-ошибок)
9. [Интернационализация (i18n)](#9-интернационализация-i18n)
10. [Webhook vs Long-Polling](#10-webhook-vs-long-polling)
11. [Антипаттерны](#11-антипаттерны)
12. [Эталонная архитектура для продакшена](#12-эталонная-архитектура-для-продакшена)

---

## 1. Структура проекта

### 1.1 Подходы к организации кода

Существуют два основных подхода к организации файлов в Telegram-боте:

**Layer-based (по слоям)** — файлы группируются по техническому назначению:

```
handlers/
middlewares/
filters/
keyboards/
services/
repositories/
models/
```

**Feature-based (по фичам)** — файлы группируются по бизнес-модулю:

```
modules/
  orders/
    handlers.py
    keyboards.py
    states.py
    service.py
  users/
    handlers.py
    keyboards.py
    states.py
    service.py
```

**Рекомендация senior-уровня:** для малых и средних ботов — layer-based. Для крупных ботов с множеством доменных областей — feature-based или гибрид. Ключевой критерий: **один разработчик должен касаться минимального количества директорий при работе над одной фичей.**

### 1.2 Эталонная структура проекта (Layer-based)

```
bot/
├── src/
│   ├── __init__.py
│   ├── __main__.py                  # Точка входа
│   ├── config.py                    # Pydantic Settings
│   ├── constants.py                 # Константы, enum'ы
│   │
│   ├── bot/                         # Telegram-слой
│   │   ├── __init__.py
│   │   ├── factory.py               # Фабрика Bot + Dispatcher
│   │   ├── handlers/                # Хэндлеры по роутерам
│   │   │   ├── __init__.py          # Регистрация всех роутеров
│   │   │   ├── common.py            # /start, /help, /cancel
│   │   │   ├── admin.py             # Админские команды
│   │   │   ├── catalog.py           # Каталог товаров
│   │   │   ├── orders.py            # Заказы
│   │   │   └── profile.py           # Профиль пользователя
│   │   ├── keyboards/               # Клавиатуры
│   │   │   ├── __init__.py
│   │   │   ├── inline.py            # Inline-клавиатуры
│   │   │   └── reply.py             # Reply-клавиатуры
│   │   ├── filters/                 # Кастомные фильтры
│   │   │   ├── __init__.py
│   │   │   ├── admin.py             # Фильтр администратора
│   │   │   └── chat_type.py         # Фильтр типа чата
│   │   ├── states/                  # FSM-состояния
│   │   │   ├── __init__.py
│   │   │   ├── registration.py
│   │   │   └── order.py
│   │   ├── middlewares/             # Middleware
│   │   │   ├── __init__.py
│   │   │   ├── database.py          # Сессия БД
│   │   │   ├── throttling.py        # Антифлуд
│   │   │   ├── logging.py           # Логирование
│   │   │   ├── i18n.py              # Локализация
│   │   │   └── auth.py              # Авторизация
│   │   └── callbacks/               # CallbackData фабрики
│   │       ├── __init__.py
│   │       └── catalog.py
│   │
│   ├── services/                    # Бизнес-логика
│   │   ├── __init__.py
│   │   ├── user_service.py
│   │   ├── order_service.py
│   │   └── catalog_service.py
│   │
│   ├── repositories/                # Работа с БД
│   │   ├── __init__.py
│   │   ├── base.py                  # Базовый репозиторий
│   │   ├── user_repo.py
│   │   └── order_repo.py
│   │
│   ├── models/                      # ORM-модели / доменные модели
│   │   ├── __init__.py
│   │   ├── base.py                  # DeclarativeBase
│   │   ├── user.py
│   │   └── order.py
│   │
│   └── infrastructure/              # Инфраструктура
│       ├── __init__.py
│       ├── database.py              # Engine, SessionFactory
│       ├── cache.py                 # Redis клиент
│       └── logging.py              # Настройка логирования
│
├── migrations/                      # Alembic
│   ├── versions/
│   └── env.py
├── tests/
│   ├── unit/
│   └── integration/
├── locales/                         # Файлы переводов
│   ├── en/
│   └── ru/
├── .env.example
├── .env
├── alembic.ini
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── Makefile
```

### 1.3 Эталонная структура (Feature-based / Модульная)

Для крупных ботов с 10+ доменных областей:

```
bot/
├── src/
│   ├── __main__.py
│   ├── config.py
│   ├── bootstrap/                    # Инициализация приложения
│   │   ├── __init__.py
│   │   ├── bot.py                    # Фабрика Bot + Dispatcher
│   │   └── container.py             # DI-контейнер (Dishka)
│   │
│   ├── common/                       # Общие компоненты
│   │   ├── middlewares/
│   │   ├── filters/
│   │   ├── keyboards/
│   │   └── states/
│   │
│   ├── modules/                      # Бизнес-модули
│   │   ├── auth/
│   │   │   ├── handlers.py
│   │   │   ├── service.py
│   │   │   ├── repository.py
│   │   │   ├── keyboards.py
│   │   │   ├── states.py
│   │   │   └── callbacks.py
│   │   ├── catalog/
│   │   │   ├── handlers.py
│   │   │   ├── service.py
│   │   │   ├── repository.py
│   │   │   ├── keyboards.py
│   │   │   ├── states.py
│   │   │   └── callbacks.py
│   │   ├── orders/
│   │   │   └── ...
│   │   └── admin/
│   │       └── ...
│   │
│   ├── infrastructure/
│   │   ├── database.py
│   │   ├── cache.py
│   │   └── storage.py
│   │
│   └── models/
│       ├── base.py
│       ├── user.py
│       └── order.py
```

### 1.4 Точка входа (`__main__.py`)

```python
"""Точка входа бота."""
import asyncio
import logging

from src.config import Settings
from src.bot.factory import create_dispatcher, create_bot


async def main() -> None:
    settings = Settings()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    bot = create_bot(settings)
    dp = create_dispatcher(settings)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
```

### 1.5 Фабрика Dispatcher (`bot/factory.py`)

```python
"""Фабрика бота и диспетчера."""
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from src.config import Settings
from src.bot.handlers import get_all_routers
from src.bot.middlewares.database import DatabaseMiddleware
from src.bot.middlewares.throttling import ThrottlingMiddleware
from src.bot.middlewares.logging import LoggingMiddleware


def create_bot(settings: Settings) -> Bot:
    """Создание экземпляра Bot с настройками по умолчанию."""
    return Bot(
        token=settings.bot.token.get_secret_value(),
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
        ),
    )


def create_dispatcher(settings: Settings) -> Dispatcher:
    """Создание и конфигурация Dispatcher."""
    storage = RedisStorage.from_url(settings.redis.url)

    dp = Dispatcher(
        storage=storage,
        settings=settings,  # Передаётся через workflow_data
    )

    # Регистрация middleware (порядок важен!)
    dp.update.outer_middleware(LoggingMiddleware())
    dp.update.outer_middleware(DatabaseMiddleware(settings.database))
    dp.message.middleware(ThrottlingMiddleware(throttle_time=0.5))

    # Регистрация роутеров
    for router in get_all_routers():
        dp.include_router(router)

    # Lifecycle-хуки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    return dp


async def on_startup(bot: Bot, settings: Settings) -> None:
    """Вызывается при запуске бота."""
    bot_info = await bot.me()
    logging.info(f"Бот запущен: @{bot_info.username}")
    # Можно установить webhook, отправить уведомление админу и т.д.


async def on_shutdown(bot: Bot, settings: Settings) -> None:
    """Вызывается при остановке бота."""
    # Уведомить админа, закрыть соединения
    for admin_id in settings.bot.admin_ids:
        try:
            await bot.send_message(admin_id, "Бот остановлен")
        except Exception:
            pass
```

### 1.6 Регистрация роутеров (`handlers/__init__.py`)

```python
"""Сборка всех роутеров приложения."""
from aiogram import Router


def get_all_routers() -> list[Router]:
    """Возвращает список роутеров в порядке приоритета."""
    from src.bot.handlers.admin import router as admin_router
    from src.bot.handlers.common import router as common_router
    from src.bot.handlers.catalog import router as catalog_router
    from src.bot.handlers.orders import router as orders_router
    from src.bot.handlers.profile import router as profile_router

    # ПОРЯДОК ВАЖЕН: первый совпавший хэндлер обрабатывает апдейт
    return [
        admin_router,     # Админские команды — высший приоритет
        common_router,    # /start, /help, /cancel
        catalog_router,   # Каталог
        orders_router,    # Заказы
        profile_router,   # Профиль
    ]
```

**Источники:**

- [aiogram-bot-template (MrConsoleka)](https://github.com/MrConsoleka/aiogram-bot-template)
- [masson-aiogram-template](https://github.com/MassonNN/masson-aiogram-template)
- [welel/aiogram-bot-template](https://github.com/welel/aiogram-bot-template)

---

## 2. Роутеры и хэндлеры

### 2.1 Основы Router

Router — центральный механизм маршрутизации событий в aiogram 3.x. Он заменяет монолитный Dispatcher из v2 и позволяет строить иерархическую систему обработки.

```python
from aiogram import Router
from aiogram.types import Message

router = Router(name=__name__)  # name для отладки


@router.message()
async def any_message(message: Message) -> None:
    await message.answer("Получено сообщение")
```

### 2.2 Способы регистрации хэндлеров

**Через декоратор (рекомендуется):**

```python
@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer("Привет!")
```

**Через метод register:**

```python
async def cmd_start(message: Message) -> None:
    await message.answer("Привет!")

router.message.register(cmd_start, Command("start"))
```

### 2.3 Поддерживаемые типы событий

Router поддерживает все типы Telegram-событий:

| Декоратор                          | Описание                    |
| ---------------------------------- | --------------------------- |
| `@router.message()`                | Новые сообщения             |
| `@router.edited_message()`         | Редактирование сообщений    |
| `@router.callback_query()`         | Нажатия inline-кнопок       |
| `@router.inline_query()`           | Inline-запросы              |
| `@router.chosen_inline_result()`   | Выбранные inline-результаты |
| `@router.channel_post()`           | Посты в канале              |
| `@router.edited_channel_post()`    | Редактирование постов       |
| `@router.my_chat_member()`         | Изменение статуса бота      |
| `@router.chat_member()`            | Изменение статуса участника |
| `@router.chat_join_request()`      | Запросы на вступление       |
| `@router.shipping_query()`         | Запросы доставки (платежи)  |
| `@router.pre_checkout_query()`     | Предоплатная проверка       |
| `@router.poll()`                   | Обновления опросов          |
| `@router.poll_answer()`            | Ответы на опросы            |
| `@router.message_reaction()`       | Реакции на сообщения        |
| `@router.message_reaction_count()` | Счётчик реакций             |
| `@router.chat_boost()`             | Бусты чата                  |
| `@router.removed_chat_boost()`     | Удалённые бусты             |
| `@router.errors()`                 | Обработка ошибок            |

### 2.4 Вложенные роутеры (Nested Routers)

Роутеры формируют **дерево**, где дочерние роутеры включаются в родительские:

```python
from aiogram import Dispatcher, Router

# Создание роутеров
dp = Dispatcher()
main_router = Router(name="main")
admin_router = Router(name="admin")
user_router = Router(name="user")

# Построение иерархии
dp.include_router(main_router)
main_router.include_router(admin_router)
main_router.include_router(user_router)

# Или множественное включение
dp.include_routers(admin_router, user_router, main_router)
```

**Ограничения:**

- Роутер **не может** включать сам себя
- **Запрещены** циклические зависимости (A → B → C → A)

### 2.5 Порядок обработки (Event Propagation)

Апдейты распространяются **сверху вниз** по дереву роутеров (depth-first search):

```
Dispatcher
├── Router "admin"      ← проверяется первым
│   └── Handler /admin
├── Router "common"     ← проверяется вторым
│   ├── Handler /start
│   └── Handler /help
└── Router "catalog"    ← проверяется третьим
    └── Handler /catalog
```

**Первый совпавший хэндлер останавливает дальнейшее распространение** (если не вернул `UNHANDLED`).

### 2.6 Паттерн "Один роутер на фичу"

```python
# handlers/catalog.py
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

router = Router(name="catalog")

# Фильтр на уровне роутера — применяется ко ВСЕМ хэндлерам
router.message.filter(F.chat.type == "private")


@router.message(Command("catalog"))
async def cmd_catalog(message: Message) -> None:
    """Показать каталог товаров."""
    await message.answer("Выберите категорию:", reply_markup=get_categories_kb())


@router.callback_query(F.data.startswith("category:"))
async def select_category(callback: CallbackQuery) -> None:
    """Обработка выбора категории."""
    category_id = callback.data.split(":")[1]
    await callback.message.edit_text(
        f"Товары категории {category_id}",
        reply_markup=get_products_kb(category_id),
    )
    await callback.answer()
```

### 2.7 Фильтры на уровне роутера

Фильтры, установленные на роутере, применяются ко **всем** хэндлерам внутри него:

```python
from aiogram import Router, F
from aiogram.filters import ChatTypeFilter

# Роутер для приватных чатов
private_router = Router(name="private")
private_router.message.filter(F.chat.type == "private")

# Роутер для групп
group_router = Router(name="groups")
group_router.message.filter(F.chat.type.in_({"group", "supergroup"}))

# Роутер для админов
admin_router = Router(name="admin")
admin_router.message.filter(F.from_user.id.in_({111111, 222222}))
```

### 2.8 Magic Filters (F-фильтры)

Aiogram 3 использует библиотеку `magic-filter` для декларативной фильтрации:

```python
from aiogram import F

# Базовые фильтры
@router.message(F.text)                              # Только текстовые
@router.message(F.photo)                              # Только фото
@router.message(F.sticker)                            # Только стикеры
@router.message(F.document)                           # Только документы

# Проверка значений
@router.message(F.text == "привет")                   # Точное совпадение
@router.message(F.text.lower() == "привет")           # Без учёта регистра
@router.message(F.text.startswith("/"))                # Начинается с /
@router.message(F.text.in_({"да", "нет"}))            # Одно из значений

# Вложенные атрибуты
@router.message(F.from_user.id == 12345)              # Конкретный пользователь
@router.message(F.chat.type == "private")             # Приватный чат
@router.message(F.reply_to_message.from_user.is_bot)  # Ответ на бота

# Извлечение данных через .as_()
@router.message(F.photo[-1].as_("largest_photo"))
async def handle_photo(message: Message, largest_photo: PhotoSize) -> None:
    print(f"Размер: {largest_photo.width}x{largest_photo.height}")

# Проверка элементов списка
@router.message(F.entities[:].type == "email")        # ВСЕ entity — email
@router.message(F.entities[...].type == "email")      # ХОТЯ БЫ одна — email

# Forward из канала
@router.message(F.forward_from_chat[F.type == "channel"].as_("channel"))
async def forwarded(message: Message, channel: Chat) -> None:
    await message.answer(f"Переслано из канала: {channel.id}")
```

### 2.9 Кастомные фильтры

```python
from aiogram.filters import BaseFilter
from aiogram.types import Message
from typing import Union


class ChatTypeFilter(BaseFilter):
    """Фильтр по типу чата."""

    def __init__(self, chat_type: Union[str, list[str]]) -> None:
        self.chat_type = chat_type

    async def __call__(self, message: Message) -> bool:
        if isinstance(self.chat_type, str):
            return message.chat.type == self.chat_type
        return message.chat.type in self.chat_type


class IsAdminFilter(BaseFilter):
    """Проверка, является ли пользователь администратором."""

    def __init__(self, admin_ids: list[int]) -> None:
        self.admin_ids = admin_ids

    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in self.admin_ids


# Фильтр с возвратом данных в хэндлер
class HasUsernamesFilter(BaseFilter):
    """Извлекает @username из текста сообщения."""

    async def __call__(self, message: Message) -> Union[bool, dict[str, list[str]]]:
        entities = message.entities or []
        found = [
            item.extract_from(message.text)
            for item in entities
            if item.type == "mention"
        ]
        if found:
            return {"usernames": found}  # Данные попадут в хэндлер
        return False


# Использование
@router.message(F.text, HasUsernamesFilter())
async def msg_with_usernames(message: Message, usernames: list[str]) -> None:
    await message.reply(f"Упомянуты: {', '.join(usernames)}")
```

### 2.10 MagicData — фильтрация по данным контекста

```python
from aiogram.filters import MagicData

# Роутер технического обслуживания
maintenance_router = Router(name="maintenance")
maintenance_router.message.filter(MagicData(F.maintenance_mode.is_(True)))

@maintenance_router.message()
async def maintenance_handler(message: Message) -> None:
    await message.answer("Бот находится на техническом обслуживании. Попробуйте позже.")

# Регистрация с передачей флага
dp = Dispatcher(maintenance_mode=True)  # workflow_data
dp.include_routers(maintenance_router, regular_router)
```

**Источники:**

- [Router documentation](https://docs.aiogram.dev/en/latest/dispatcher/router.html)
- [DeepWiki: Router System](https://deepwiki.com/aiogram/aiogram/3.1-router-system)
- [mastergroosha: Filters](https://mastergroosha.github.io/aiogram-3-guide/filters-and-middlewares/)

---

## 3. Цепочка Middleware

### 3.1 Двухуровневая архитектура middleware

Aiogram 3 реализует **уникальную двухслойную** систему middleware:

**Outer middleware** (`outer_middleware`) — выполняется **ДО** проверки фильтров:

- Срабатывает на **каждом** входящем событии
- Не имеет доступа к результатам фильтрации
- Подходит для: логирования, throttling, бан-листов, DB-сессий

**Inner middleware** (`middleware`) — выполняется **ПОСЛЕ** прохождения фильтров, но **ДО** хэндлера:

- Срабатывает только когда фильтры совпали
- Гарантированно ведёт к выполнению хэндлера
- Подходит для: обогащения данных, аутентификации с контекстом

### 3.2 Порядок выполнения

```
Входящий Update
  │
  ▼
[Update Outer Middleware] ─── Before
  │
  ▼
[Update Inner Middleware] ─── Before
  │
  ▼
[Message Outer Middleware] ── Before
  │
  ▼
  Проверка фильтров
  │
  ▼ (фильтры прошли)
[Message Inner Middleware] ── Before
  │
  ▼
  ═══ HANDLER ═══
  │
  ▲
[Message Inner Middleware] ── After
  │
  ▲
[Message Outer Middleware] ── After
  │
  ▲
[Update Inner Middleware] ─── After
  │
  ▲
[Update Outer Middleware] ─── After
```

### 3.3 BaseMiddleware

```python
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class ExampleMiddleware(BaseMiddleware):
    """Базовый шаблон middleware."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # === BEFORE handler ===
        # Можно модифицировать data, проверить условия, залогировать

        result = await handler(event, data)  # Передать обработку дальше

        # === AFTER handler ===
        # Можно обработать результат, закрыть ресурсы

        return result
```

**Критическое правило:** если `await handler(event, data)` **НЕ вызвать**, обработка апдейта **прекращается**. Это используется для блокировки (бан, throttling).

### 3.4 Регистрация middleware

```python
from aiogram import Dispatcher, Router

dp = Dispatcher()
router = Router()

# Outer middleware — на диспетчере (глобально)
dp.update.outer_middleware(LoggingMiddleware())
dp.message.outer_middleware(ThrottlingMiddleware())

# Inner middleware — на роутере
router.message.middleware(DatabaseMiddleware())
router.callback_query.middleware(AuthMiddleware())

# Через декоратор (функциональный стиль)
@dp.update.outer_middleware()
async def logging_middleware(handler, event, data):
    print(f"Update: {event.update_id}")
    return await handler(event, data)
```

### 3.5 Middleware: Database Session (SQLAlchemy)

Один из самых важных middleware — предоставление сессии БД каждому хэндлеру:

```python
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class DatabaseMiddleware(BaseMiddleware):
    """Middleware для инъекции сессии SQLAlchemy в каждый хэндлер.

    Использует паттерн session-per-request:
    - Создаёт сессию перед обработкой
    - Коммитит при успехе
    - Откатывает при ошибке
    - Закрывает в любом случае
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with self.session_factory() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise


# Использование в хэндлере
@router.message(Command("profile"))
async def cmd_profile(message: Message, session: AsyncSession) -> None:
    user = await session.get(User, message.from_user.id)
    await message.answer(f"Ваш профиль: {user.name}")
```

### 3.6 Middleware: Throttling (Антифлуд)

```python
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.dispatcher.flags import get_flag
from aiogram.types import Message
from cachetools import TTLCache


class ThrottlingMiddleware(BaseMiddleware):
    """Антифлуд middleware с поддержкой разных TTL через флаги."""

    def __init__(self, default_ttl: float = 0.5) -> None:
        self.caches: dict[str, TTLCache] = {
            "default": TTLCache(maxsize=10_000, ttl=default_ttl),
        }

    def _get_cache(self, key: str, ttl: float) -> TTLCache:
        if key not in self.caches:
            self.caches[key] = TTLCache(maxsize=10_000, ttl=ttl)
        return self.caches[key]

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        throttling_key = get_flag(data, "throttling_key", default="default")

        cache = self.caches.get(throttling_key, self.caches["default"])

        if event.chat.id in cache:
            return  # Молча отбрасываем — НЕ вызываем handler

        cache[event.chat.id] = None
        return await handler(event, data)


# Регистрация
dp.message.middleware(ThrottlingMiddleware(default_ttl=0.5))

# Использование с флагами на хэндлерах
@router.message(Command("spin"), flags={"throttling_key": "spin"})
async def cmd_spin(message: Message) -> None:
    await message.answer("🎰 Крутим...")
```

### 3.7 Middleware: Logging

```python
import time
import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Update

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Логирование всех входящих апдейтов с замером времени."""

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        start = time.monotonic()
        user = data.get("event_from_user")
        user_info = f"user_id={user.id}" if user else "unknown_user"

        logger.info(
            "Update %s from %s — event_type=%s",
            event.update_id,
            user_info,
            event.event_type,
        )

        try:
            result = await handler(event, data)
            duration = (time.monotonic() - start) * 1000
            logger.info(
                "Update %s handled in %.1fms",
                event.update_id,
                duration,
            )
            return result
        except Exception as exc:
            duration = (time.monotonic() - start) * 1000
            logger.exception(
                "Update %s failed after %.1fms: %s",
                event.update_id,
                duration,
                exc,
            )
            raise
```

### 3.8 Middleware: Auth / Бан-лист

```python
class AuthMiddleware(BaseMiddleware):
    """Проверка бан-листа. Outer middleware на уровне Update."""

    def __init__(self, banned_users: set[int] | None = None) -> None:
        self.banned_users = banned_users or set()

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user and user.id in self.banned_users:
            # Молча отбрасываем — бот «не видит» забаненного
            return

        return await handler(event, data)


# Регистрация как outer middleware — до любых фильтров
dp.update.outer_middleware(AuthMiddleware(banned_users={999999}))
```

### 3.9 Middleware: Chat Action (Typing...)

```python
from aiogram.dispatcher.flags import get_flag
from aiogram.utils.chat_action import ChatActionSender


class ChatActionMiddleware(BaseMiddleware):
    """Показывает 'typing...' для долгих операций через флаги."""

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        long_operation = get_flag(data, "long_operation")

        if not long_operation:
            return await handler(event, data)

        async with ChatActionSender(
            action=long_operation,
            chat_id=event.chat.id,
            bot=data["bot"],
        ):
            return await handler(event, data)


# Использование
@router.message(Command("generate"), flags={"long_operation": "typing"})
async def cmd_generate(message: Message) -> None:
    result = await heavy_computation()  # Пока выполняется — бот «печатает»
    await message.answer(result)
```

### 3.10 Рекомендуемый порядок middleware

```python
dp = Dispatcher(storage=storage)

# 1. Логирование — самый первый, ловит ВСЁ
dp.update.outer_middleware(LoggingMiddleware())

# 2. Бан-лист — до любой обработки
dp.update.outer_middleware(AuthMiddleware(banned_users=banned))

# 3. Database session — нужна и фильтрам, и хэндлерам
dp.update.outer_middleware(DatabaseMiddleware(session_factory))

# 4. Throttling — после аутентификации, до хэндлеров
dp.message.middleware(ThrottlingMiddleware(default_ttl=0.5))

# 5. Chat Action — только для конкретных хэндлеров
router.message.middleware(ChatActionMiddleware())
```

**Источники:**

- [Middlewares documentation](https://docs.aiogram.dev/en/latest/dispatcher/middlewares.html)
- [mastergroosha: Filters and Middlewares](https://mastergroosha.github.io/aiogram-3-guide/filters-and-middlewares/)
- [MasterGroosha/telegram-casino-bot throttling](https://github.com/MasterGroosha/telegram-casino-bot/blob/aiogram3/bot/middlewares/throttling.py)

---

## 4. FSM (Конечный автомат)

### 4.1 Теория

Конечный автомат (Finite State Machine) — математическая модель вычислений, которая в каждый момент времени находится **ровно в одном** из конечных состояний. Переходы между состояниями происходят в ответ на входные данные.

В контексте бота FSM используется для **пошаговых диалогов**: регистрация, оформление заказа, заполнение анкеты и т.д.

### 4.2 Определение состояний

```python
from aiogram.fsm.state import StatesGroup, State


class RegistrationForm(StatesGroup):
    """Состояния для регистрации пользователя."""
    waiting_for_name = State()
    waiting_for_age = State()
    waiting_for_phone = State()
    waiting_for_confirmation = State()


class OrderForm(StatesGroup):
    """Состояния для оформления заказа."""
    choosing_product = State()
    choosing_quantity = State()
    entering_address = State()
    confirming_order = State()
```

### 4.3 Работа с FSMContext

```python
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

router = Router(name="registration")


# === НАЧАЛО ДИАЛОГА ===
@router.message(StateFilter(None), Command("register"))
async def cmd_register(message: Message, state: FSMContext) -> None:
    """Инициация процесса регистрации.

    ВАЖНО: StateFilter(None) означает "нет активного состояния".
    Без него хэндлер сработает и при активном FSM-диалоге!
    """
    await message.answer("Введите ваше имя:")
    await state.set_state(RegistrationForm.waiting_for_name)


# === ШАГ 1: Имя ===
@router.message(RegistrationForm.waiting_for_name, F.text)
async def process_name(message: Message, state: FSMContext) -> None:
    if len(message.text) < 2 or len(message.text) > 50:
        await message.answer("Имя должно быть от 2 до 50 символов. Попробуйте ещё раз:")
        return  # Состояние НЕ меняем — пользователь остаётся на этом шаге

    await state.update_data(name=message.text)
    await message.answer("Отлично! Теперь введите ваш возраст:")
    await state.set_state(RegistrationForm.waiting_for_age)


# === ШАГ 2: Возраст ===
@router.message(RegistrationForm.waiting_for_age, F.text)
async def process_age(message: Message, state: FSMContext) -> None:
    if not message.text.isdigit():
        await message.answer("Возраст должен быть числом. Попробуйте ещё раз:")
        return

    age = int(message.text)
    if not (13 <= age <= 120):
        await message.answer("Возраст должен быть от 13 до 120 лет:")
        return

    await state.update_data(age=age)
    await message.answer(
        "Отправьте ваш номер телефона:",
        reply_markup=get_phone_kb(),  # Кнопка "Поделиться контактом"
    )
    await state.set_state(RegistrationForm.waiting_for_phone)


# === ШАГ 3: Телефон ===
@router.message(RegistrationForm.waiting_for_phone, F.contact)
async def process_phone(message: Message, state: FSMContext) -> None:
    await state.update_data(phone=message.contact.phone_number)

    # Получаем ВСЕ собранные данные
    data = await state.get_data()

    await message.answer(
        f"Подтвердите регистрацию:\n"
        f"Имя: {data['name']}\n"
        f"Возраст: {data['age']}\n"
        f"Телефон: {data['phone']}\n\n"
        "Всё верно? (да/нет)",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(RegistrationForm.waiting_for_confirmation)


# === ШАГ 4: Подтверждение ===
@router.message(RegistrationForm.waiting_for_confirmation, F.text.lower() == "да")
async def confirm_registration(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()

    # Сохранение в БД
    user = User(
        telegram_id=message.from_user.id,
        name=data["name"],
        age=data["age"],
        phone=data["phone"],
    )
    session.add(user)

    await state.clear()  # Сбрасываем состояние И данные
    await message.answer("Регистрация завершена!")


@router.message(RegistrationForm.waiting_for_confirmation, F.text.lower() == "нет")
async def cancel_registration(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Регистрация отменена.", reply_markup=ReplyKeyboardRemove())
```

### 4.4 Универсальная отмена

```python
@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """Универсальная отмена текущего FSM-диалога."""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нечего отменять.")
        return

    await state.clear()
    await message.answer(
        "Действие отменено.",
        reply_markup=ReplyKeyboardRemove(),
    )
```

### 4.5 Storage (Хранилища состояний)

#### MemoryStorage (только для разработки)

```python
from aiogram.fsm.storage.memory import MemoryStorage

storage = MemoryStorage()
dp = Dispatcher(storage=storage)
```

**Данные хранятся в RAM и теряются при перезапуске. Категорически не подходит для продакшена.**

#### RedisStorage (рекомендуется для продакшена)

```python
from aiogram.fsm.storage.redis import RedisStorage

# Простой вариант
storage = RedisStorage.from_url("redis://localhost:6379/0")

# С настройками
from redis.asyncio import Redis

redis = Redis(host="localhost", port=6379, db=0)
storage = RedisStorage(
    redis=redis,
    state_ttl=3600,    # Состояние живёт 1 час
    data_ttl=3600,     # Данные живут 1 час
)

dp = Dispatcher(storage=storage)
```

#### KeyBuilder (настройка формата ключей)

```python
from aiogram.fsm.storage.redis import DefaultKeyBuilder

key_builder = DefaultKeyBuilder(
    prefix="fsm",            # Префикс ключа
    separator=":",            # Разделитель
    with_bot_id=True,         # Включить ID бота (для мультибота)
    with_destiny=True,        # Включить destiny
)

storage = RedisStorage(redis=redis, key_builder=key_builder)
# Формат ключа: fsm:<bot_id>:<chat_id>:<user_id>:<destiny>:<field>
```

### 4.6 FSM-стратегии

```python
from aiogram.fsm.strategy import FSMStrategy

# По умолчанию: уникальное состояние для каждого пользователя в каждом чате
dp = Dispatcher(storage=storage, fsm_strategy=FSMStrategy.USER_IN_CHAT)

# Общее состояние для всего чата (например, игра)
dp = Dispatcher(storage=storage, fsm_strategy=FSMStrategy.CHAT)

# Глобальное состояние пользователя (одинаковое во всех чатах)
dp = Dispatcher(storage=storage, fsm_strategy=FSMStrategy.GLOBAL_USER)

# По топикам (для форумов)
dp = Dispatcher(storage=storage, fsm_strategy=FSMStrategy.USER_IN_TOPIC)
dp = Dispatcher(storage=storage, fsm_strategy=FSMStrategy.CHAT_TOPIC)
```

| Стратегия       | Область действия                                    |
| --------------- | --------------------------------------------------- |
| `USER_IN_CHAT`  | Уникально для (user_id, chat_id) — **по умолчанию** |
| `CHAT`          | Общее для всего чата                                |
| `GLOBAL_USER`   | Одинаковое для пользователя во всех чатах           |
| `USER_IN_TOPIC` | По топикам форума для пользователя                  |
| `CHAT_TOPIC`    | По топикам форума для всего чата                    |

### 4.7 Сложные сценарии с ветвлением

```python
class SupportDialog(StatesGroup):
    """FSM для обращения в поддержку с ветвлением."""
    choosing_topic = State()

    # Ветка: техническая проблема
    tech_describe_problem = State()
    tech_attach_screenshot = State()

    # Ветка: финансовый вопрос
    finance_describe_issue = State()
    finance_attach_receipt = State()

    # Общее завершение
    confirm_ticket = State()


@router.callback_query(SupportDialog.choosing_topic, F.data == "topic:tech")
async def choose_tech(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(topic="tech")
    await callback.message.edit_text("Опишите техническую проблему:")
    await state.set_state(SupportDialog.tech_describe_problem)
    await callback.answer()


@router.callback_query(SupportDialog.choosing_topic, F.data == "topic:finance")
async def choose_finance(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(topic="finance")
    await callback.message.edit_text("Опишите финансовый вопрос:")
    await state.set_state(SupportDialog.finance_describe_issue)
    await callback.answer()
```

### 4.8 Управление FSM другого пользователя

```python
async def admin_reset_user_state(
    message: Message,
    bot: Bot,
    target_user_id: int,
) -> None:
    """Админ сбрасывает FSM-состояние пользователя."""
    from aiogram.fsm.storage.base import StorageKey

    key = StorageKey(
        bot_id=bot.id,
        chat_id=target_user_id,
        user_id=target_user_id,
    )
    # Получение контекста
    context = FSMContext(storage=dp.storage, key=key)
    await context.clear()
    await message.answer(f"Состояние пользователя {target_user_id} сброшено.")
```

### 4.9 aiogram-dialog (альтернатива FSM)

Для сложных UI-диалогов с виджетами рекомендуется библиотека `aiogram-dialog`:

```python
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Button, Select

# Определение диалога
dialog = Dialog(
    Window(
        Const("Выберите категорию:"),
        Select(
            Format("{item.name}"),
            id="category",
            items="categories",
            item_id_getter=lambda item: item.id,
            on_click=on_category_selected,
        ),
        state=CatalogSG.choosing_category,
        getter=get_categories,
    ),
    Window(
        Format("Вы выбрали: {selected_category}"),
        Button(Const("Назад"), id="back", on_click=go_back),
        state=CatalogSG.viewing_category,
        getter=get_category_details,
    ),
)
```

**Источники:**

- [FSM documentation](https://docs.aiogram.dev/en/latest/dispatcher/finite_state_machine/index.html)
- [FSM Storages](https://docs.aiogram.dev/en/latest/dispatcher/finite_state_machine/storages.html)
- [mastergroosha: FSM](https://mastergroosha.github.io/aiogram-3-guide/fsm/)
- [aiogram-dialog](https://github.com/Tishka17/aiogram_dialog)

---

## 5. Dependency Injection

### 5.1 Встроенный DI в aiogram 3

Aiogram 3 реализует DI через **автоматическую инъекцию по имени параметра**. Контекстные данные передаются через цепочку Dispatcher → Middleware → Filter → Handler.

```python
# Данные, переданные в Dispatcher, доступны во ВСЕХ хэндлерах
dp = Dispatcher(
    storage=storage,
    config=settings,            # Доступно как config
    session_factory=session_factory,  # Доступно как session_factory
)

# Запуск с дополнительными данными
await dp.start_polling(bot, allowed_updates=..., my_param="value")

# Хэндлер автоматически получает нужные параметры по имени
@router.message(Command("info"))
async def cmd_info(
    message: Message,
    bot: Bot,               # Встроенный — экземпляр бота
    config: Settings,        # Из workflow_data Dispatcher
    state: FSMContext,       # Встроенный — FSM-контекст
) -> None:
    await message.answer(f"Bot: {bot.id}, Env: {config.environment}")
```

### 5.2 Стандартные доступные зависимости

| Параметр          | Тип           | Описание                             |
| ----------------- | ------------- | ------------------------------------ |
| `bot`             | `Bot`         | Экземпляр бота                       |
| `event_update`    | `Update`      | Исходный Update                      |
| `event_router`    | `Router`      | Текущий роутер                       |
| `event_from_user` | `User`        | Пользователь, инициировавший событие |
| `event_chat`      | `Chat`        | Чат, в котором произошло событие     |
| `state`           | `FSMContext`  | Контекст конечного автомата          |
| `fsm_storage`     | `BaseStorage` | Хранилище FSM                        |
| `raw_state`       | `str`         | Текущее состояние FSM (строка)       |

### 5.3 Три способа инъекции зависимостей

#### Способ 1: Через Dispatcher (workflow_data)

```python
dp = Dispatcher(storage=storage)

# Через именованные аргументы конструктора
dp = Dispatcher(storage=storage, config=settings, redis=redis_client)

# Через dict-синтаксис (для динамических данных)
dp["user_service"] = UserService(session_factory)
dp["order_service"] = OrderService(session_factory)
```

#### Способ 2: Через middleware (data dict)

```python
class InjectServicesMiddleware(BaseMiddleware):
    """Инъекция сервисов через middleware."""

    def __init__(
        self,
        user_service: UserService,
        order_service: OrderService,
    ) -> None:
        self.user_service = user_service
        self.order_service = order_service

    async def __call__(self, handler, event, data) -> Any:
        data["user_service"] = self.user_service
        data["order_service"] = self.order_service
        return await handler(event, data)
```

#### Способ 3: Через возвращаемое значение фильтра

```python
class InjectUserFilter(BaseFilter):
    """Фильтр, который загружает пользователя из БД и прокидывает в хэндлер."""

    async def __call__(
        self,
        message: Message,
        session: AsyncSession,
    ) -> dict[str, Any] | bool:
        user = await session.get(User, message.from_user.id)
        if user is None:
            return False  # Фильтр не прошёл
        return {"db_user": user}  # Данные попадают в хэндлер


@router.message(InjectUserFilter())
async def profile(message: Message, db_user: User) -> None:
    await message.answer(f"Привет, {db_user.name}!")
```

### 5.4 Dishka — продвинутый DI-контейнер

Для крупных проектов рекомендуется использовать Dishka — полноценный async DI-контейнер с поддержкой scoped-зависимостей:

```python
import asyncio
from collections.abc import AsyncIterator

from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.aiogram import (
    AiogramProvider,
    FromDishka,
    inject,
    setup_dishka,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


# === Определение провайдеров ===

class DatabaseProvider(Provider):
    """Провайдер для инфраструктуры БД."""

    @provide(scope=Scope.APP)
    def get_engine(self, config: Settings) -> AsyncEngine:
        return create_async_engine(config.database.url)

    @provide(scope=Scope.APP)
    def get_session_factory(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(engine, expire_on_commit=False)

    @provide(scope=Scope.REQUEST)
    async def get_session(
        self,
        factory: async_sessionmaker[AsyncSession],
    ) -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session


class ServiceProvider(Provider):
    """Провайдер бизнес-сервисов."""

    @provide(scope=Scope.REQUEST)
    def get_user_service(self, session: AsyncSession) -> UserService:
        return UserService(UserRepository(session))

    @provide(scope=Scope.REQUEST)
    def get_order_service(self, session: AsyncSession) -> OrderService:
        return OrderService(OrderRepository(session))


# === Хэндлеры с инъекцией ===

router = Router()


@router.message(Command("profile"))
@inject
async def cmd_profile(
    message: Message,
    user_service: FromDishka[UserService],
) -> None:
    user = await user_service.get_or_create(message.from_user.id)
    await message.answer(f"Ваш профиль: {user.name}")


@router.message(Command("orders"))
@inject
async def cmd_orders(
    message: Message,
    order_service: FromDishka[OrderService],
) -> None:
    orders = await order_service.get_user_orders(message.from_user.id)
    await message.answer(f"У вас {len(orders)} заказов")


# === Инициализация ===

async def main() -> None:
    settings = Settings()
    bot = Bot(token=settings.bot.token.get_secret_value())
    dp = Dispatcher()
    dp.include_router(router)

    # Создание контейнера
    container = make_async_container(
        DatabaseProvider(),
        ServiceProvider(),
        AiogramProvider(),   # Провайдер aiogram-специфичных зависимостей
    )

    # Подключение Dishka к диспетчеру
    setup_dishka(container=container, router=dp, auto_inject=True)

    try:
        await dp.start_polling(bot)
    finally:
        await container.close()
        await bot.session.close()
```

### 5.5 Scopes в Dishka

| Scope           | Время жизни                    | Пример                               |
| --------------- | ------------------------------ | ------------------------------------ |
| `Scope.APP`     | Весь жизненный цикл приложения | Engine, SessionFactory, Config       |
| `Scope.REQUEST` | Один Telegram Update           | AsyncSession, Services, Repositories |

**Источники:**

- [Dependency Injection docs](https://docs.aiogram.dev/en/latest/dispatcher/dependency_injection.html)
- [Dishka + aiogram](https://dishka.readthedocs.io/en/stable/integrations/aiogram.html)
- [Dishka example](https://github.com/reagento/dishka/blob/develop/examples/integrations/aiogram_bot.py)

---

## 6. Конфигурация

### 6.1 Pydantic Settings

```python
"""Конфигурация приложения через Pydantic Settings."""
from pathlib import Path
from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    """Настройки Telegram-бота."""
    token: SecretStr
    admin_ids: list[int] = []

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: str | list[int]) -> list[int]:
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v


class DatabaseSettings(BaseSettings):
    """Настройки PostgreSQL."""
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: SecretStr = SecretStr("postgres")
    name: str = "bot_db"

    @property
    def url(self) -> str:
        pwd = self.password.get_secret_value()
        return f"postgresql+asyncpg://{self.user}:{pwd}@{self.host}:{self.port}/{self.name}"


class RedisSettings(BaseSettings):
    """Настройки Redis."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: SecretStr | None = None

    @property
    def url(self) -> str:
        if self.password:
            pwd = self.password.get_secret_value()
            return f"redis://:{pwd}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class WebhookSettings(BaseSettings):
    """Настройки вебхука (опционально)."""
    use: bool = False
    url: str = ""
    host: str = "0.0.0.0"
    port: int = 8080
    path: str = "/webhook"
    secret: SecretStr = SecretStr("")


class Settings(BaseSettings):
    """Главный конфигурационный класс."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",  # BOT__TOKEN, DB__HOST и т.д.
        extra="ignore",
    )

    environment: str = "development"
    debug: bool = False

    bot: BotSettings = BotSettings()
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    webhook: WebhookSettings = WebhookSettings()

    @property
    def is_production(self) -> bool:
        return self.environment == "production"
```

### 6.2 Файл `.env.example`

```env
# === Окружение ===
ENVIRONMENT=development
DEBUG=true

# === Telegram Bot ===
BOT__TOKEN=123456:ABC-DEF
BOT__ADMIN_IDS=111111,222222

# === PostgreSQL ===
DATABASE__HOST=localhost
DATABASE__PORT=5432
DATABASE__USER=postgres
DATABASE__PASSWORD=postgres
DATABASE__NAME=bot_db

# === Redis ===
REDIS__HOST=localhost
REDIS__PORT=6379
REDIS__DB=0

# === Webhook (опционально) ===
WEBHOOK__USE=false
WEBHOOK__URL=https://example.com
WEBHOOK__HOST=0.0.0.0
WEBHOOK__PORT=8080
WEBHOOK__PATH=/webhook
WEBHOOK__SECRET=mysecrettoken
```

### 6.3 Разделение окружений

```python
# Загрузка разных .env файлов
import os

env = os.getenv("ENVIRONMENT", "development")
env_file = f".env.{env}" if env != "development" else ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=env_file,
        env_nested_delimiter="__",
    )
```

Структура файлов:

```
.env              # development (gitignored)
.env.example      # шаблон (в git)
.env.staging      # staging (gitignored)
.env.production   # production (gitignored или через CI/CD secrets)
```

### 6.4 Валидация конфигурации при старте

```python
async def main() -> None:
    try:
        settings = Settings()
    except ValidationError as e:
        print(f"Ошибка конфигурации:\n{e}")
        sys.exit(1)

    # Проверка подключений при старте
    if settings.is_production:
        assert settings.bot.token.get_secret_value() != "123456:ABC-DEF", \
            "Используется тестовый токен в production!"
```

**Источники:**

- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [aiogram-bot-template (MrConsoleka)](https://github.com/MrConsoleka/aiogram-bot-template)

---

## 7. Клавиатуры и CallbackData

### 7.1 Reply-клавиатуры

```python
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder


# Способ 1: Явное создание
def get_main_menu_kb() -> ReplyKeyboardMarkup:
    """Главное меню бота."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Каталог"), KeyboardButton(text="Корзина")],
            [KeyboardButton(text="Мои заказы"), KeyboardButton(text="Профиль")],
            [KeyboardButton(text="Поддержка")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )


# Способ 2: Через Builder (динамическая генерация)
def get_categories_kb(categories: list[str]) -> ReplyKeyboardMarkup:
    """Клавиатура с категориями."""
    builder = ReplyKeyboardBuilder()
    for category in categories:
        builder.button(text=category)
    builder.adjust(2)  # По 2 кнопки в ряд
    return builder.as_markup(
        resize_keyboard=True,
        one_time_keyboard=True,
    )


# Кнопка "Поделиться контактом"
def get_phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отправить номер телефона", request_contact=True)],
        ],
        resize_keyboard=True,
    )


# Удаление клавиатуры
await message.answer("Готово!", reply_markup=ReplyKeyboardRemove())
```

### 7.2 Inline-клавиатуры

```python
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


# Способ 1: Явное создание
def get_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Подтвердить", callback_data="confirm:yes"),
            InlineKeyboardButton(text="Отменить", callback_data="confirm:no"),
        ],
    ])


# Способ 2: Builder
def get_products_kb(products: list[Product]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for product in products:
        builder.button(
            text=f"{product.name} — {product.price}₸",
            callback_data=f"product:{product.id}",
        )
    builder.adjust(1)  # По 1 кнопке в ряд

    # Добавляем навигацию отдельной строкой
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="page:prev"),
        InlineKeyboardButton(text="Вперёд ▶️", callback_data="page:next"),
    )
    return builder.as_markup()


# Кнопка-ссылка
def get_url_kb(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть", url=url)],
    ])
```

### 7.3 CallbackData Factory (типобезопасные callback_data)

Вместо ручного парсинга строк `"product:42:buy"` используйте фабрику:

```python
from aiogram.filters.callback_data import CallbackData
from enum import IntEnum


class ProductAction(IntEnum):
    VIEW = 0
    BUY = 1
    FAVORITE = 2


class ProductCallback(CallbackData, prefix="product"):
    """Callback для действий с товарами.

    Формат: product:<id>:<action>
    Пример: product:42:1
    """
    id: int
    action: ProductAction


class PaginationCallback(CallbackData, prefix="page"):
    """Callback для пагинации.

    Формат: page:<module>:<current_page>:<direction>
    """
    module: str
    page: int
    direction: int  # -1 или +1


# === Создание клавиатуры ===

def get_product_card_kb(product_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(
        text="Купить",
        callback_data=ProductCallback(id=product_id, action=ProductAction.BUY),
    )
    builder.button(
        text="В избранное",
        callback_data=ProductCallback(id=product_id, action=ProductAction.FAVORITE),
    )
    builder.adjust(2)
    return builder.as_markup()


# === Обработка callback ===

@router.callback_query(ProductCallback.filter(F.action == ProductAction.BUY))
async def buy_product(
    callback: CallbackQuery,
    callback_data: ProductCallback,  # Автоматически распарсен!
) -> None:
    product_id = callback_data.id
    await callback.message.answer(f"Вы покупаете товар #{product_id}")
    await callback.answer()


@router.callback_query(ProductCallback.filter(F.action == ProductAction.FAVORITE))
async def favorite_product(
    callback: CallbackQuery,
    callback_data: ProductCallback,
) -> None:
    await callback.answer(f"Товар #{callback_data.id} добавлен в избранное!", show_alert=True)


# === Пагинация ===

@router.callback_query(PaginationCallback.filter())
async def handle_pagination(
    callback: CallbackQuery,
    callback_data: PaginationCallback,
) -> None:
    new_page = callback_data.page + callback_data.direction
    # Обновляем клавиатуру с новой страницей
    await callback.message.edit_reply_markup(
        reply_markup=get_paginated_kb(callback_data.module, new_page),
    )
    await callback.answer()
```

### 7.4 Допустимые типы полей в CallbackData

- `str`, `int`, `float`, `bool`
- `Decimal`, `Fraction`, `UUID`
- `Enum` (строковые и IntEnum)

**Максимальный размер callback_data — 64 байта!** Используйте короткие префиксы и числовые enum'ы.

### 7.5 Комбинирование Builder'ов

```python
# Создание комплексной клавиатуры из нескольких источников
main_builder = InlineKeyboardBuilder()
main_builder.button(text="Товар 1", callback_data="p:1")
main_builder.button(text="Товар 2", callback_data="p:2")

nav_builder = InlineKeyboardBuilder()
nav_builder.button(text="◀️", callback_data="prev")
nav_builder.button(text="1/5", callback_data="noop")
nav_builder.button(text="▶️", callback_data="next")

# Прикрепляем навигацию к основной клавиатуре
main_builder.attach(nav_builder)

# adjust применяется к кнопкам, добавленным ДО attach
main_builder.adjust(2)
```

**Источники:**

- [Keyboard Builder](https://docs.aiogram.dev/en/latest/utils/keyboard.html)
- [CallbackData Factory & Filter](https://docs.aiogram.dev/en/latest/dispatcher/filters/callback_data.html)

---

## 8. Обработка ошибок

### 8.1 Глобальный Error Handler

```python
from aiogram import Router
from aiogram.types import ErrorEvent, Update
from aiogram.filters import ExceptionTypeFilter
import logging

logger = logging.getLogger(__name__)

router = Router(name="errors")


@router.error()
async def global_error_handler(event: ErrorEvent) -> bool:
    """Глобальный обработчик всех необработанных ошибок."""
    logger.exception(
        "Необработанная ошибка при обработке update %s: %s",
        event.update.update_id,
        event.exception,
    )

    # Попытка уведомить пользователя
    update = event.update
    if update.message:
        try:
            await update.message.answer(
                "Произошла ошибка. Попробуйте позже или обратитесь в поддержку."
            )
        except Exception:
            pass

    return True  # Ошибка обработана
```

### 8.2 Обработка конкретных исключений

```python
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError


@router.error(ExceptionTypeFilter(TelegramBadRequest), F.update.callback_query.as_("callback"))
async def handle_bad_request(event: ErrorEvent, callback: CallbackQuery) -> bool:
    """Обработка ошибок некорректных запросов к API."""
    logger.warning("Bad Request: %s", event.exception)
    await callback.answer("Не удалось выполнить действие.", show_alert=True)
    return True


@router.error(ExceptionTypeFilter(TelegramForbiddenError))
async def handle_forbidden(event: ErrorEvent) -> bool:
    """Бот заблокирован пользователем."""
    logger.info("Бот заблокирован пользователем: %s", event.exception)
    # Можно пометить пользователя как неактивного в БД
    return True


# Пользовательские исключения
class InsufficientBalanceError(Exception):
    def __init__(self, balance: float, required: float) -> None:
        self.balance = balance
        self.required = required


@router.error(
    ExceptionTypeFilter(InsufficientBalanceError),
    F.update.message.as_("message"),
)
async def handle_insufficient_balance(
    event: ErrorEvent,
    message: Message,
) -> bool:
    exc: InsufficientBalanceError = event.exception
    await message.answer(
        f"Недостаточно средств! Баланс: {exc.balance}₸, требуется: {exc.required}₸"
    )
    return True
```

### 8.3 Иерархия исключений aiogram

```
AiogramError
├── DetailedAiogramError
├── TelegramAPIError
│   ├── TelegramBadRequest          # 400 — неверный запрос
│   ├── TelegramUnauthorizedError   # 401 — неверный токен
│   ├── TelegramForbiddenError      # 403 — бот заблокирован
│   ├── TelegramNotFound            # 404 — чат/сообщение не найдены
│   ├── TelegramConflictError       # 409 — конфликт (polling + webhook)
│   ├── TelegramRetryAfter          # 429 — flood control
│   ├── TelegramServerError         # 5xx — ошибки серверов Telegram
│   ├── TelegramEntityTooLarge      # 413 — файл слишком большой
│   └── RestartingTelegram          # Перезагрузка серверов
├── TelegramNetworkError            # Сетевые ошибки
├── ClientDecodeError               # Ошибка декодирования ответа
└── SceneException                  # Ошибки сцен
```

### 8.4 Паттерн try-except в хэндлерах

```python
@router.message(Command("send_all"))
async def cmd_send_all(
    message: Message,
    bot: Bot,
    session: AsyncSession,
) -> None:
    """Рассылка всем пользователям с обработкой ошибок."""
    users = await get_all_users(session)
    sent = 0
    failed = 0

    for user in users:
        try:
            await bot.send_message(user.telegram_id, "Новость!")
            sent += 1
        except TelegramForbiddenError:
            # Бот заблокирован — помечаем пользователя
            user.is_active = False
            failed += 1
        except TelegramRetryAfter as e:
            # Flood control — ждём
            await asyncio.sleep(e.retry_after)
            await bot.send_message(user.telegram_id, "Новость!")
            sent += 1
        except TelegramAPIError as e:
            logger.warning("Ошибка при отправке %s: %s", user.telegram_id, e)
            failed += 1

    await message.answer(f"Отправлено: {sent}, Ошибки: {failed}")
```

**Источники:**

- [Errors documentation](https://docs.aiogram.dev/en/latest/dispatcher/errors.html)
- [Error class hierarchy](https://docs.aiogram.dev/en/latest/dispatcher/class_based_handlers/error.html)

---

## 9. Интернационализация (i18n)

### 9.1 Встроенный i18n с Babel

```python
from aiogram.utils.i18n import I18n, gettext as _, lazy_gettext as __

# Инициализация
i18n = I18n(path="locales", default_locale="ru", domain="messages")
```

### 9.2 I18n Middleware

Aiogram предоставляет три варианта middleware:

```python
from aiogram.utils.i18n import SimpleI18nMiddleware, ConstI18nMiddleware, FSMI18nMiddleware

# 1. Simple — определяет язык из User.language_code
dp.update.outer_middleware(SimpleI18nMiddleware(i18n))

# 2. Const — фиксированный язык
dp.update.outer_middleware(ConstI18nMiddleware(i18n, locale="ru"))

# 3. FSM — хранит выбор пользователя в FSM-storage
dp.update.outer_middleware(FSMI18nMiddleware(i18n))
```

### 9.3 Кастомный I18n Middleware с БД

```python
from aiogram.utils.i18n.middleware import I18nMiddleware


class DatabaseI18nMiddleware(I18nMiddleware):
    """Middleware, который берёт язык из БД."""

    async def get_locale(self, event: TelegramObject, data: dict) -> str:
        user = data.get("event_from_user")
        if user is None:
            return self.i18n.default_locale

        session: AsyncSession = data.get("session")
        if session:
            db_user = await session.get(User, user.id)
            if db_user and db_user.locale:
                return db_user.locale

        # Fallback на Telegram language_code
        return user.language_code or self.i18n.default_locale
```

### 9.4 Использование переводов

```python
from aiogram.utils.i18n import gettext as _
from aiogram.utils.i18n import lazy_gettext as __

@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(_("Добро пожаловать в бот!"))

# lazy_gettext для фильтров (вычисляется отложенно)
@router.message(F.text == __("Каталог"))
async def catalog(message: Message) -> None:
    await message.answer(_("Выберите категорию"))
```

### 9.5 Fluentogram (альтернатива)

```python
from fluentogram import TranslatorRunner

@router.message(Command("start"))
async def cmd_start(message: Message, i18n: TranslatorRunner) -> None:
    await message.answer(i18n.welcome.message())
```

Файлы переводов (Fluent):

```ftl
# locales/ru/main.ftl
welcome-message = Добро пожаловать в бот!
catalog-title = Выберите категорию:
order-created = Заказ #{$order_id} создан

# locales/en/main.ftl
welcome-message = Welcome to the bot!
catalog-title = Choose a category:
order-created = Order #{$order_id} created
```

**Источники:**

- [Translation docs](https://docs.aiogram.dev/en/latest/utils/i18n.html)
- [fluentogram](https://github.com/Arustinal/fluentogram)

---

## 10. Webhook vs Long-Polling

### 10.1 Сравнение

| Критерий               | Long-Polling                  | Webhook                        |
| ---------------------- | ----------------------------- | ------------------------------ |
| **Простота настройки** | Просто — `start_polling()`    | Нужен HTTPS, домен, веб-сервер |
| **Масштабирование**    | Только 1 процесс на токен     | Несколько воркеров             |
| **Мультибот**          | Невозможен                    | Поддерживается                 |
| **Разработка**         | Идеально                      | Нужен ngrok/tunnel             |
| **Задержка**           | ~1-3 сек (зависит от timeout) | Мгновенно                      |
| **Инфраструктура**     | Не нужна                      | Нужен веб-сервер               |

### 10.2 Long-Polling (для разработки и малой нагрузки)

```python
async def main() -> None:
    bot = Bot(token=settings.bot.token.get_secret_value())
    dp = Dispatcher(storage=storage)

    # Lifecycle hooks
    @dp.startup()
    async def on_startup(bot: Bot) -> None:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Бот запущен (polling)")

    @dp.shutdown()
    async def on_shutdown(bot: Bot) -> None:
        logger.info("Бот остановлен")

    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types(),
    )
```

### 10.3 Webhook (для продакшена)

```python
from aiohttp import web
from aiogram.webhook.aiohttp_server import (
    SimpleRequestHandler,
    setup_application,
)


async def on_startup(bot: Bot) -> None:
    await bot.set_webhook(
        url=f"{settings.webhook.url}{settings.webhook.path}",
        secret_token=settings.webhook.secret.get_secret_value(),
        allowed_updates=dp.resolve_used_update_types(),
    )


async def main() -> None:
    bot = Bot(token=settings.bot.token.get_secret_value())
    dp = Dispatcher(storage=storage)
    dp.startup.register(on_startup)

    app = web.Application()
    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=settings.webhook.secret.get_secret_value(),
    )
    webhook_handler.register(app, path=settings.webhook.path)
    setup_application(app, dp, bot=bot)

    await web._run_app(
        app,
        host=settings.webhook.host,
        port=settings.webhook.port,
    )
```

### 10.4 Webhook через FastAPI

```python
from fastapi import FastAPI, Request
from aiogram.types import Update

app = FastAPI()


@app.on_event("startup")
async def startup() -> None:
    await bot.set_webhook(
        url=f"{WEBHOOK_URL}{WEBHOOK_PATH}",
        secret_token=WEBHOOK_SECRET,
    )


@app.post(WEBHOOK_PATH)
async def webhook_handler(request: Request) -> None:
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot=bot, update=update)


@app.on_event("shutdown")
async def shutdown() -> None:
    await bot.delete_webhook()
    await bot.session.close()
```

**Источники:**

- [Webhook docs](https://docs.aiogram.dev/en/latest/dispatcher/webhook.html)
- [Long-polling docs](https://docs.aiogram.dev/en/latest/dispatcher/long_polling.html)

---

## 11. Антипаттерны

### 11.1 Критические ошибки

#### 1. Использование MemoryStorage в продакшене

```python
# НЕПРАВИЛЬНО — данные потеряются при перезапуске
dp = Dispatcher(storage=MemoryStorage())

# ПРАВИЛЬНО
storage = RedisStorage.from_url("redis://localhost:6379/0")
dp = Dispatcher(storage=storage)
```

#### 2. Передача parse_mode напрямую в Bot()

```python
# НЕПРАВИЛЬНО (удалено в 3.7.0)
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)

# ПРАВИЛЬНО
from aiogram.client.default import DefaultBotProperties
bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
```

#### 3. Отсутствие StateFilter(None) для начальных команд

```python
# НЕПРАВИЛЬНО — сработает даже если пользователь в FSM-диалоге
@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer("Привет!")

# ПРАВИЛЬНО
@router.message(StateFilter(None), Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer("Привет!")

# ИЛИ: зарегистрировать /cancel без StateFilter, чтобы он работал всегда
@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменено")
```

#### 4. Блокирующие вызовы в async-хэндлерах

```python
# НЕПРАВИЛЬНО — блокирует event loop!
import requests
import time

@router.message(Command("data"))
async def cmd_data(message: Message) -> None:
    time.sleep(5)  # БЛОКИРУЕТ!
    response = requests.get("https://api.example.com")  # БЛОКИРУЕТ!
    await message.answer(response.text)

# ПРАВИЛЬНО
import aiohttp
import asyncio

@router.message(Command("data"))
async def cmd_data(message: Message) -> None:
    await asyncio.sleep(5)  # Неблокирующий
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.example.com") as resp:
            data = await resp.text()
    await message.answer(data)
```

#### 5. Глобальные переменные вместо DI

```python
# НЕПРАВИЛЬНО — глобальное состояние, невозможно тестировать
db = Database()
config = load_config()

@router.message(Command("info"))
async def cmd_info(message: Message) -> None:
    user = await db.get_user(message.from_user.id)  # Глобальная переменная
    await message.answer(f"Привет, {user.name}")

# ПРАВИЛЬНО — инъекция через middleware/DI
@router.message(Command("info"))
async def cmd_info(message: Message, session: AsyncSession) -> None:
    user = await session.get(User, message.from_user.id)
    await message.answer(f"Привет, {user.name}")
```

#### 6. Отсутствие callback.answer()

```python
# НЕПРАВИЛЬНО — пользователь видит "часики" на кнопке
@router.callback_query(F.data == "action")
async def handle_callback(callback: CallbackQuery) -> None:
    await callback.message.answer("Готово!")
    # Забыли callback.answer()!

# ПРАВИЛЬНО
@router.callback_query(F.data == "action")
async def handle_callback(callback: CallbackQuery) -> None:
    await callback.message.answer("Готово!")
    await callback.answer()  # Убирает "часики"
```

#### 7. Импорт из aiogram 2.x

```python
# НЕПРАВИЛЬНО — этого больше нет
from aiogram.utils import executor
executor.start_polling(dp)

# ПРАВИЛЬНО
async def main():
    await dp.start_polling(bot)

asyncio.run(main())
```

#### 8. Ручной парсинг callback_data

```python
# НЕПРАВИЛЬНО — хрупко, нетипизировано
@router.callback_query(F.data.startswith("product:"))
async def handle(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    product_id = int(parts[1])
    action = parts[2]

# ПРАВИЛЬНО — типобезопасная фабрика
class ProductCallback(CallbackData, prefix="product"):
    id: int
    action: str

@router.callback_query(ProductCallback.filter(F.action == "buy"))
async def handle(callback: CallbackQuery, callback_data: ProductCallback) -> None:
    product_id = callback_data.id
```

### 11.2 Архитектурные антипаттерны

#### 9. Бизнес-логика в хэндлерах

```python
# НЕПРАВИЛЬНО — хэндлер содержит бизнес-логику
@router.message(Command("order"))
async def cmd_order(message: Message, session: AsyncSession) -> None:
    # Вся логика прямо в хэндлере
    product = await session.get(Product, product_id)
    if product.stock <= 0:
        await message.answer("Нет в наличии")
        return
    product.stock -= 1
    order = Order(user_id=message.from_user.id, product_id=product_id)
    session.add(order)
    await session.commit()
    await message.answer("Заказ создан!")

# ПРАВИЛЬНО — хэндлер вызывает сервис
@router.message(Command("order"))
async def cmd_order(
    message: Message,
    order_service: FromDishka[OrderService],
) -> None:
    try:
        order = await order_service.create_order(
            user_id=message.from_user.id,
            product_id=product_id,
        )
        await message.answer(f"Заказ #{order.id} создан!")
    except OutOfStockError:
        await message.answer("Товар закончился.")
```

#### 10. Один огромный файл с хэндлерами

```python
# НЕПРАВИЛЬНО — bot.py на 2000 строк

# ПРАВИЛЬНО — разделение по файлам
# handlers/common.py    — /start, /help
# handlers/catalog.py   — каталог
# handlers/orders.py    — заказы
# handlers/admin.py     — администрирование
```

#### 11. Игнорирование ошибок API Telegram

```python
# НЕПРАВИЛЬНО
await bot.send_message(user_id, "Привет")  # Может упасть!

# ПРАВИЛЬНО
try:
    await bot.send_message(user_id, "Привет")
except TelegramForbiddenError:
    logger.info("Пользователь %s заблокировал бота", user_id)
except TelegramRetryAfter as e:
    await asyncio.sleep(e.retry_after)
    await bot.send_message(user_id, "Привет")
```

#### 12. Хранение токена в коде

```python
# НЕПРАВИЛЬНО
BOT_TOKEN = "123456:ABC-DEF1234..."

# ПРАВИЛЬНО
from pydantic import SecretStr
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    bot_token: SecretStr

    model_config = SettingsConfigDict(env_file=".env")
```

**Источники:**

- [Aiogram 3 FAQ: Common Errors](https://akchonya.github.io/aiogram-3-faq/common_errors/)
- [Aiogram 3 FAQ: Common Questions](https://akchonya.github.io/aiogram-3-faq/common_questions/)

---

## 12. Эталонная архитектура для продакшена

### 12.1 Полная схема инициализации

```python
"""src/__main__.py — Точка входа приложения."""
import asyncio
import logging
import sys

from src.config import Settings
from src.infrastructure.database import create_session_factory
from src.infrastructure.cache import create_redis
from src.bot.factory import create_bot, create_dispatcher


async def main() -> None:
    # 1. Конфигурация
    settings = Settings()

    # 2. Логирование
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s",
        stream=sys.stdout,
    )
    logger = logging.getLogger(__name__)

    # 3. Инфраструктура
    session_factory = create_session_factory(settings.database.url)
    redis = create_redis(settings.redis.url)

    # 4. Bot и Dispatcher
    bot = create_bot(settings)
    dp = create_dispatcher(
        settings=settings,
        session_factory=session_factory,
        redis=redis,
    )

    # 5. Запуск
    logger.info("Запуск бота в режиме %s", settings.environment)
    try:
        if settings.webhook.use:
            await run_webhook(dp, bot, settings)
        else:
            await dp.start_polling(
                bot,
                allowed_updates=dp.resolve_used_update_types(),
            )
    finally:
        await redis.aclose()
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())
```

### 12.2 Инфраструктура БД

```python
"""src/infrastructure/database.py"""
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(
        database_url,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
```

### 12.3 Слой сервисов

```python
"""src/services/user_service.py"""
from src.repositories.user_repo import UserRepository
from src.models.user import User


class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def get_or_create(self, telegram_id: int, **kwargs) -> User:
        user = await self._repo.get_by_telegram_id(telegram_id)
        if user is None:
            user = User(telegram_id=telegram_id, **kwargs)
            await self._repo.create(user)
        return user

    async def update_language(self, telegram_id: int, locale: str) -> None:
        user = await self._repo.get_by_telegram_id(telegram_id)
        if user:
            user.locale = locale
            await self._repo.update(user)
```

### 12.4 Слой репозиториев

```python
"""src/repositories/base.py"""
from typing import Generic, TypeVar
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseRepository(Generic[T]):
    def __init__(self, session: AsyncSession, model: type[T]) -> None:
        self._session = session
        self._model = model

    async def get_by_id(self, id: int) -> T | None:
        return await self._session.get(self._model, id)

    async def create(self, entity: T) -> T:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: T) -> T:
        merged = await self._session.merge(entity)
        await self._session.flush()
        return merged

    async def delete(self, entity: T) -> None:
        await self._session.delete(entity)
        await self._session.flush()


"""src/repositories/user_repo.py"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_users(self) -> list[User]:
        stmt = select(User).where(User.is_active.is_(True))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
```

### 12.5 ORM-модели

```python
"""src/models/base.py"""
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Базовая модель с общими полями."""
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


"""src/models/user.py"""
from sqlalchemy import BigInteger, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20))
    locale: Mapped[str] = mapped_column(String(10), default="ru")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
```

### 12.6 Docker-compose для инфраструктуры

```yaml
# docker-compose.yml
services:
  bot:
    build: .
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    restart: unless-stopped

  postgres:
    image: postgres:17-alpine
    environment:
      POSTGRES_USER: ${DATABASE__USER:-postgres}
      POSTGRES_PASSWORD: ${DATABASE__PASSWORD:-postgres}
      POSTGRES_DB: ${DATABASE__NAME:-bot_db}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DATABASE__USER:-postgres}"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:8-alpine
    command: redis-server --requirepass ${REDIS__PASSWORD:-}
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data

volumes:
  pgdata:
  redisdata:
```

### 12.7 Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Установка uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Зависимости
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Код приложения
COPY . .

# Миграции и запуск
CMD ["sh", "-c", "uv run alembic upgrade head && uv run python -m src"]
```

### 12.8 Makefile

```makefile
.PHONY: run lint format migrate test

run:
	uv run python -m src

lint:
	uv run ruff check .

format:
	uv run ruff format .

migrate:
	uv run alembic upgrade head

migrate-create:
	uv run alembic revision --autogenerate -m "$(NAME)"

test:
	uv run pytest tests/ -v

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-build:
	docker compose build
```

### 12.9 Чеклист для продакшена

- [ ] RedisStorage для FSM (не MemoryStorage)
- [ ] SecretStr для токенов и паролей
- [ ] Webhook или polling с graceful shutdown
- [ ] Database middleware с session-per-request
- [ ] Throttling middleware
- [ ] Глобальный error handler
- [ ] Логирование входящих апдейтов
- [ ] Разделение хэндлеров по роутерам
- [ ] CallbackData Factory вместо строковых callback_data
- [ ] Бизнес-логика в сервисах, а не в хэндлерах
- [ ] `.env` в `.gitignore`
- [ ] Docker + docker-compose
- [ ] Alembic миграции
- [ ] Тесты (unit + integration)
- [ ] CI/CD (lint, test, deploy)

---

## Источники

### Официальная документация

- [aiogram 3.x documentation](https://docs.aiogram.dev/)
- [Router](https://docs.aiogram.dev/en/latest/dispatcher/router.html)
- [Middlewares](https://docs.aiogram.dev/en/latest/dispatcher/middlewares.html)
- [FSM](https://docs.aiogram.dev/en/latest/dispatcher/finite_state_machine/index.html)
- [FSM Storages](https://docs.aiogram.dev/en/latest/dispatcher/finite_state_machine/storages.html)
- [Dependency Injection](https://docs.aiogram.dev/en/latest/dispatcher/dependency_injection.html)
- [Keyboard Builder](https://docs.aiogram.dev/en/latest/utils/keyboard.html)
- [CallbackData Factory](https://docs.aiogram.dev/en/latest/dispatcher/filters/callback_data.html)
- [Errors](https://docs.aiogram.dev/en/latest/dispatcher/errors.html)
- [Webhook](https://docs.aiogram.dev/en/latest/dispatcher/webhook.html)
- [Long-Polling](https://docs.aiogram.dev/en/latest/dispatcher/long_polling.html)
- [i18n / Translation](https://docs.aiogram.dev/en/latest/utils/i18n.html)

### Руководства и туториалы

- [mastergroosha: Пишем Telegram-ботов с aiogram 3.x](https://mastergroosha.github.io/aiogram-3-guide/)
- [Aiogram 3 FAQ](https://akchonya.github.io/aiogram-3-faq/)
- [DeepWiki: aiogram Router System](https://deepwiki.com/aiogram/aiogram/3.1-router-system)

### Шаблоны проектов

- [MrConsoleka/aiogram-bot-template](https://github.com/MrConsoleka/aiogram-bot-template)
- [MassonNN/masson-aiogram-template](https://github.com/MassonNN/masson-aiogram-template)
- [welel/aiogram-bot-template](https://github.com/welel/aiogram-bot-template)
- [one-zero-eight/aiogram-template](https://github.com/one-zero-eight/aiogram-template)

### DI и инструменты

- [Dishka documentation](https://dishka.readthedocs.io/en/stable/)
- [Dishka + aiogram integration](https://dishka.readthedocs.io/en/stable/integrations/aiogram.html)
- [aiogram-dialog](https://github.com/Tishka17/aiogram_dialog)
- [fluentogram (i18n)](https://github.com/Arustinal/fluentogram)

### Примеры кода

- [MasterGroosha/telegram-casino-bot (throttling middleware)](https://github.com/MasterGroosha/telegram-casino-bot/blob/aiogram3/bot/middlewares/throttling.py)
- [MasterGroosha/aiogram-and-sqlalchemy-demo](https://github.com/MasterGroosha/aiogram-and-sqlalchemy-demo)
- [Dishka aiogram example](https://github.com/reagento/dishka/blob/develop/examples/integrations/aiogram_bot.py)
