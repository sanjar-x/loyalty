# Исследование бэкенд-решений для Telegram-бота на Aiogram 3.x

> Дата: 2026-03-19
> Версия aiogram: 3.26.x
> Python: 3.14+

---

## Содержание

1. [Webhook vs Long Polling](#1-webhook-vs-long-polling)
2. [База данных (SQLAlchemy 2.x Async + Alembic)](#2-база-данных-sqlalchemy-2x-async--alembic)
3. [Redis](#3-redis)
4. [Очереди задач (Task Queues)](#4-очереди-задач-task-queues)
5. [Интеграция с внешними API](#5-интеграция-с-внешними-api)
6. [Анти-паттерны](#6-анти-паттерны)

---

## 1. Webhook vs Long Polling

### 1.1. Сравнительная таблица

| Критерий | Long Polling | Webhook |
|----------|-------------|---------|
| **Инфраструктура** | Не требует белого IP/домена | Требует HTTPS-домен |
| **Масштабирование** | Один процесс на токен | Горизонтальное масштабирование |
| **Задержка** | Минимальная (постоянное соединение) | Минимальная (push от Telegram) |
| **Сложность** | Минимальная | Требует веб-сервер + SSL |
| **Использование ресурсов** | Постоянное соединение к API | Только при получении апдейтов |
| **Debugging** | Простой — запустил и работает | Нужен ngrok / tunnel для локалки |
| **Мульти-бот** | Нет (1 процесс = 1 токен) | Да (все боты через один сервер) |
| **Рекомендация** | Development | Production |

### 1.2. Long Polling — для разработки

Long polling — это режим, при котором бот постоянно опрашивает серверы Telegram на наличие новых обновлений. Это самый простой способ запуска бота.

**Ключевое ограничение:** Можно использовать polling только из одного процесса на один токен бота, иначе сервер Telegram вернёт ошибку.

```python
"""
Long Polling — минимальный рабочий пример.
Идеален для разработки и отладки.
"""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, Router, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router(name="main")


@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """Обработчик команды /start."""
    await message.answer(
        f"Привет, {html.bold(message.from_user.full_name)}!"
    )


async def main() -> None:
    bot = Bot(
        token="YOUR_TOKEN",
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    # drop_pending_updates=True — игнорируем все апдейты,
    # которые пришли, пока бот был выключен
    await dp.start_polling(bot, drop_pending_updates=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
```

### 1.3. Webhook через aiohttp — встроенная поддержка

Aiogram имеет встроенную интеграцию с aiohttp для webhook-режима. Это рекомендуемый подход для production.

```python
"""
Webhook через aiohttp — встроенная интеграция aiogram.
Рекомендуемый подход для production за nginx reverse proxy.
"""
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import (
    SimpleRequestHandler,
    setup_application,
)

# ---------- Конфигурация ----------
BOT_TOKEN = "YOUR_TOKEN"
WEBHOOK_HOST = "https://yourdomain.com"
WEBHOOK_PATH = "/webhook"
WEBHOOK_SECRET = "your-secret-token-here"  # Для валидации запросов
WEBAPP_HOST = "127.0.0.1"  # За nginx — слушаем localhost
WEBAPP_PORT = 8080

router = Router(name="main")


@router.message(CommandStart())
async def command_start(message: Message) -> None:
    await message.answer("Привет! Бот работает на webhook.")


async def on_startup(bot: Bot) -> None:
    """Устанавливаем webhook при старте."""
    await bot.set_webhook(
        url=f"{WEBHOOK_HOST}{WEBHOOK_PATH}",
        secret_token=WEBHOOK_SECRET,
        drop_pending_updates=True,
        # allowed_updates можно получить автоматически:
        # allowed_updates=dp.resolve_used_update_types(),
    )
    logging.info("Webhook установлен: %s%s", WEBHOOK_HOST, WEBHOOK_PATH)


async def on_shutdown(bot: Bot) -> None:
    """Удаляем webhook при остановке."""
    await bot.delete_webhook()
    logging.info("Webhook удалён")


def main() -> None:
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    # Регистрация lifecycle-хуков
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Создаём aiohttp-приложение
    app = web.Application()

    # Привязываем обработчик webhook
    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET,
    )
    webhook_handler.register(app, path=WEBHOOK_PATH)

    # Связываем lifecycle aiohttp с aiogram
    setup_application(app, dp, bot=bot)

    # Запускаем
    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
```

### 1.4. Webhook через FastAPI — кастомная интеграция

FastAPI позволяет совмещать бота с REST API (админка, BFF, webhooks платёжных систем).

```python
"""
Webhook через FastAPI — совмещаем бота с REST API.
Подходит, когда бот — часть более крупного приложения.
"""
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import uvicorn
from fastapi import FastAPI, Request, Response
from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, Update

# ---------- Конфигурация ----------
BOT_TOKEN = "YOUR_TOKEN"
WEBHOOK_URL = "https://yourdomain.com/webhook"
WEBHOOK_PATH = "/webhook"
WEBHOOK_SECRET = "your-secret-token-here"

# ---------- Bot & Dispatcher ----------
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()
router = Router(name="main")
dp.include_router(router)


@router.message(CommandStart())
async def command_start(message: Message) -> None:
    await message.answer("Привет! Бот на FastAPI webhook.")


# ---------- FastAPI Lifespan ----------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Управление жизненным циклом приложения."""
    # Startup: устанавливаем webhook
    await bot.set_webhook(
        url=WEBHOOK_URL,
        secret_token=WEBHOOK_SECRET,
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True,
    )
    logging.info("Webhook установлен: %s", WEBHOOK_URL)

    yield

    # Shutdown: удаляем webhook и закрываем сессии
    await bot.delete_webhook()
    await bot.session.close()
    logging.info("Webhook удалён, сессия закрыта")


app = FastAPI(lifespan=lifespan)


@app.post(WEBHOOK_PATH)
async def webhook_endpoint(request: Request) -> Response:
    """Обработка входящих обновлений от Telegram."""
    # Проверяем secret token
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret != WEBHOOK_SECRET:
        return Response(status_code=403)

    # Парсим и обрабатываем апдейт
    update = Update.model_validate(
        await request.json(),
        context={"bot": bot},
    )
    await dp.feed_update(bot, update)
    return Response(status_code=200)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check для мониторинга."""
    return {"status": "ok"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 1.5. Nginx конфигурация для webhook

```nginx
# /etc/nginx/sites-available/telegram-bot
server {
    listen 443 ssl http2;
    server_name bot.yourdomain.com;

    # SSL сертификат (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/bot.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bot.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Webhook endpoint
    location /webhook {
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_buffering off;
        proxy_pass http://127.0.0.1:8080;
    }

    # Health check (если нужно)
    location /health {
        proxy_pass http://127.0.0.1:8080;
    }

    # Блокируем все остальные пути
    location / {
        return 404;
    }
}

# Редирект с HTTP на HTTPS
server {
    listen 80;
    server_name bot.yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

### 1.6. Self-Signed SSL (без reverse proxy)

Для случаев, когда нет nginx (VPS напрямую):

```python
"""
Webhook с self-signed SSL сертификатом.
Используется, когда нет reverse proxy.
"""
import ssl
from pathlib import Path

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

WEBHOOK_SSL_CERT = Path("/path/to/cert.pem")
WEBHOOK_SSL_PRIV = Path("/path/to/key.pem")
WEBHOOK_HOST = "https://YOUR_IP:8443"
WEBHOOK_PATH = "/webhook"


async def on_startup(bot: Bot) -> None:
    # Передаём сертификат Telegram, чтобы он доверял self-signed
    await bot.set_webhook(
        url=f"{WEBHOOK_HOST}{WEBHOOK_PATH}",
        certificate=WEBHOOK_SSL_CERT.open("rb"),
    )


def main() -> None:
    bot = Bot(token="YOUR_TOKEN")
    dp = Dispatcher()
    dp.startup.register(on_startup)

    app = web.Application()
    handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    # SSL контекст
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(str(WEBHOOK_SSL_CERT), str(WEBHOOK_SSL_PRIV))

    # Telegram поддерживает порты: 443, 80, 88, 8443
    web.run_app(app, host="0.0.0.0", port=8443, ssl_context=context)


if __name__ == "__main__":
    main()
```

### 1.7. Рекомендация: стратегия переключения

```python
"""
Универсальный запуск: polling для dev, webhook для production.
Определяется через переменную окружения.
"""
import os
import asyncio
import logging

from aiogram import Bot, Dispatcher


async def start_polling(bot: Bot, dp: Dispatcher) -> None:
    """Запуск в режиме Long Polling (development)."""
    logging.info("Запуск в режиме POLLING")
    await dp.start_polling(bot, drop_pending_updates=True)


async def start_webhook(bot: Bot, dp: Dispatcher) -> None:
    """Запуск в режиме Webhook (production)."""
    from aiohttp import web
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

    webhook_url = os.environ["WEBHOOK_URL"]
    webhook_path = os.environ.get("WEBHOOK_PATH", "/webhook")
    secret = os.environ.get("WEBHOOK_SECRET", "")
    host = os.environ.get("WEBAPP_HOST", "127.0.0.1")
    port = int(os.environ.get("WEBAPP_PORT", "8080"))

    await bot.set_webhook(
        url=f"{webhook_url}{webhook_path}",
        secret_token=secret,
        drop_pending_updates=True,
    )

    app = web.Application()
    handler = SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=secret)
    handler.register(app, path=webhook_path)
    setup_application(app, dp, bot=bot)

    logging.info("Запуск в режиме WEBHOOK на %s:%d", host, port)
    web.run_app(app, host=host, port=port)


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=os.environ["BOT_TOKEN"])
    dp = Dispatcher()
    # dp.include_router(...)  # Подключение роутеров

    mode = os.environ.get("BOT_MODE", "polling").lower()

    if mode == "webhook":
        asyncio.run(start_webhook(bot, dp))
    else:
        asyncio.run(start_polling(bot, dp))


if __name__ == "__main__":
    main()
```

**Источники:**
- [Aiogram 3 Long Polling документация](https://docs.aiogram.dev/en/latest/dispatcher/long_polling.html)
- [Aiogram 3 Webhook документация](https://docs.aiogram.dev/en/latest/dispatcher/webhook.html)
- [Habr — Aiogram 3 webhook через FastAPI](https://habr.com/ru/articles/819955/)
- [Aiogram webhook FastAPI template](https://github.com/QuvonchbekBobojonov/aiogram-webhook-template)

---

## 2. База данных (SQLAlchemy 2.x Async + Alembic)

### 2.1. Архитектура слоя данных

Для Telegram-бота на aiogram 3.x рекомендуется следующая архитектура:

```
bot/
├── src/
│   ├── infrastructure/
│   │   └── database/
│   │       ├── __init__.py
│   │       ├── engine.py          # AsyncEngine, session factory
│   │       ├── base.py            # DeclarativeBase
│   │       ├── models/            # ORM-модели
│   │       │   ├── __init__.py
│   │       │   ├── user.py
│   │       │   └── subscription.py
│   │       ├── repositories/      # Repository Pattern
│   │       │   ├── __init__.py
│   │       │   ├── base.py
│   │       │   └── user.py
│   │       └── uow.py            # Unit of Work
│   ├── middlewares/
│   │   ├── __init__.py
│   │   └── db.py                  # DB Session Middleware
│   └── handlers/
│       └── ...
├── alembic/
│   ├── env.py
│   └── versions/
├── alembic.ini
└── ...
```

### 2.2. Настройка AsyncEngine и Session Factory

```python
"""
src/infrastructure/database/engine.py

Создание AsyncEngine и фабрики сессий.
Ключевые параметры для production.
"""
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_engine(
    database_url: str,
    echo: bool = False,
) -> AsyncEngine:
    """
    Создаёт AsyncEngine с оптимальными параметрами.

    Параметры:
    - pool_pre_ping: проверяет соединение перед использованием
      (защита от "стухших" соединений после restart PostgreSQL)
    - pool_size: базовый размер пула соединений
    - max_overflow: дополнительные соединения сверх pool_size
    - pool_recycle: время жизни соединения в секундах
      (важно для PostgreSQL с PgBouncer)
    """
    return create_async_engine(
        url=database_url,
        echo=echo,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,  # 1 час
        # Для asyncpg (рекомендуемый драйвер):
        # connect_args={"server_settings": {"jit": "off"}},
    )


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """
    Создаёт фабрику AsyncSession.

    expire_on_commit=False — объекты не "протухают" после commit,
    что важно для async-кода, где повторный lazy load невозможен.
    """
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
```

### 2.3. Декларативная база и модели

```python
"""
src/infrastructure/database/base.py

Базовый класс для ORM-моделей с общими миксинами.
"""
import datetime
from typing import Annotated

from sqlalchemy import BigInteger, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# Аннотированные типы для переиспользования
int_pk = Annotated[int, mapped_column(primary_key=True, autoincrement=True)]
bigint_pk = Annotated[int, mapped_column(BigInteger, primary_key=True)]
created_at = Annotated[
    datetime.datetime,
    mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    ),
]
updated_at = Annotated[
    datetime.datetime,
    mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    ),
]


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""

    __abstract__ = True

    def __repr__(self) -> str:
        cols = [
            f"{col}={getattr(self, col)!r}"
            for col in self.__table__.columns.keys()
        ]
        return f"<{self.__class__.__name__}({', '.join(cols)})>"
```

```python
"""
src/infrastructure/database/models/user.py

Пример ORM-модели пользователя Telegram.
"""
import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, String, Boolean, DateTime, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base, created_at, updated_at

if TYPE_CHECKING:
    from src.infrastructure.database.models.subscription import Subscription


class User(Base):
    __tablename__ = "users"

    # Telegram user_id — BigInteger, т.к. ID может быть > 2^31
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    is_blocked: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )

    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    # Relationships
    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="user",
        lazy="selectin",  # Eager loading по умолчанию
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username!r})>"
```

```python
"""
src/infrastructure/database/models/subscription.py

Модель подписки пользователя.
"""
import datetime

from sqlalchemy import BigInteger, ForeignKey, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base, int_pk, created_at


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int_pk]
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    plan: Mapped[str] = mapped_column(String(50))
    expires_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
    )
    created_at: Mapped[created_at]

    # Relationships
    user: Mapped["User"] = relationship(back_populates="subscriptions")
```

### 2.4. Repository Pattern

```python
"""
src/infrastructure/database/repositories/base.py

Базовый репозиторий с общими CRUD-операциями.
Все операции — через AsyncSession, никогда session.commit() в репозитории!
"""
from typing import Any, Generic, TypeVar, Sequence

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from src.infrastructure.database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Базовый репозиторий.

    Правила:
    1. Никогда не вызывать session.commit() — это ответственность UoW
    2. Использовать select() для всех запросов (SQLAlchemy 2.0 style)
    3. Возвращать доменные объекты или None
    """

    def __init__(self, session: AsyncSession, model: type[ModelType]) -> None:
        self._session = session
        self._model = model

    async def get_by_id(self, id: Any) -> ModelType | None:
        """Получить запись по первичному ключу."""
        return await self._session.get(self._model, id)

    async def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[ModelType]:
        """Получить все записи с пагинацией."""
        stmt = (
            select(self._model)
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count(self) -> int:
        """Получить общее количество записей."""
        stmt = select(func.count()).select_from(self._model)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create(self, obj: ModelType) -> ModelType:
        """Создать новую запись."""
        self._session.add(obj)
        await self._session.flush()  # flush, не commit!
        return obj

    async def create_many(self, objects: list[ModelType]) -> list[ModelType]:
        """Создать несколько записей."""
        self._session.add_all(objects)
        await self._session.flush()
        return objects

    async def update_by_id(self, id: Any, **values: Any) -> None:
        """Обновить запись по ID."""
        stmt = (
            update(self._model)
            .where(self._model.id == id)  # type: ignore[attr-defined]
            .values(**values)
        )
        await self._session.execute(stmt)

    async def delete_by_id(self, id: Any) -> None:
        """Удалить запись по ID."""
        stmt = delete(self._model).where(
            self._model.id == id  # type: ignore[attr-defined]
        )
        await self._session.execute(stmt)

    async def exists(self, id: Any) -> bool:
        """Проверить существование записи."""
        stmt = (
            select(func.count())
            .select_from(self._model)
            .where(self._model.id == id)  # type: ignore[attr-defined]
        )
        result = await self._session.execute(stmt)
        return result.scalar_one() > 0
```

```python
"""
src/infrastructure/database/repositories/user.py

Репозиторий для работы с пользователями.
Специфичные запросы, выходящие за рамки базового CRUD.
"""
from typing import Sequence

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infrastructure.database.models.user import User
from src.infrastructure.database.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Получить пользователя по Telegram ID."""
        return await self._session.get(User, telegram_id)

    async def get_by_username(self, username: str) -> User | None:
        """Получить пользователя по username."""
        stmt = select(User).where(User.username == username)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_subscriptions(self, telegram_id: int) -> User | None:
        """
        Получить пользователя вместе с подписками.
        selectinload — решение проблемы N+1 для async.
        """
        stmt = (
            select(User)
            .options(selectinload(User.subscriptions))
            .where(User.id == telegram_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_users(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[User]:
        """Получить активных (не заблокированных) пользователей."""
        stmt = (
            select(User)
            .where(User.is_blocked == False)  # noqa: E712
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def upsert_from_telegram(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str,
        last_name: str | None,
        language_code: str | None,
        is_premium: bool,
    ) -> User:
        """
        Создать или обновить пользователя из данных Telegram.
        Вызывается при каждом взаимодействии — обновляет актуальные данные.
        """
        user = await self.get_by_telegram_id(telegram_id)
        if user is None:
            user = User(
                id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code,
                is_premium=is_premium,
            )
            self._session.add(user)
        else:
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            user.language_code = language_code
            user.is_premium = is_premium

        await self._session.flush()
        return user

    async def get_users_count(self) -> int:
        """Общее количество пользователей."""
        return await self.count()

    async def bulk_get_by_ids(self, ids: list[int]) -> Sequence[User]:
        """Получить несколько пользователей по списку ID."""
        stmt = select(User).where(User.id.in_(ids))
        result = await self._session.execute(stmt)
        return result.scalars().all()
```

### 2.5. Unit of Work Pattern

```python
"""
src/infrastructure/database/uow.py

Unit of Work — единая транзакция для группы операций.
Все записи в БД происходят только через UoW.commit().
"""
from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.infrastructure.database.repositories.user import UserRepository


class UnitOfWork:
    """
    Паттерн Unit of Work.

    Обеспечивает:
    1. Единую транзакцию для всех репозиториев
    2. Автоматический rollback при ошибках
    3. Ленивую инициализацию репозиториев
    4. Корректное закрытие сессии

    Использование:
        async with uow:
            user = await uow.users.get_by_telegram_id(123)
            user.username = "new_username"
            await uow.commit()
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("UnitOfWork не инициализирован. Используйте async with.")
        return self._session

    # Ленивая инициализация репозиториев
    @property
    def users(self) -> UserRepository:
        return UserRepository(self.session)

    async def __aenter__(self) -> "UnitOfWork":
        self._session = self._session_factory()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()
        await self.close()

    async def commit(self) -> None:
        """Зафиксировать все изменения."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Откатить все изменения."""
        await self.session.rollback()

    async def close(self) -> None:
        """Закрыть сессию."""
        if self._session is not None:
            await self._session.close()
            self._session = None
```

### 2.6. Database Middleware для Aiogram

```python
"""
src/middlewares/db.py

Middleware для инъекции UnitOfWork в каждый обработчик.
"""
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.infrastructure.database.uow import UnitOfWork


class DbSessionMiddleware(BaseMiddleware):
    """
    Middleware, который создаёт UnitOfWork для каждого входящего апдейта.

    Преимущества:
    - Каждый хендлер получает изолированную транзакцию
    - Автоматический rollback при ошибках
    - Сессия закрывается после обработки, соединение возвращается в пул
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        super().__init__()
        self._session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with UnitOfWork(self._session_factory) as uow:
            data["uow"] = uow
            result = await handler(event, data)
            return result


class RawSessionMiddleware(BaseMiddleware):
    """
    Альтернативный middleware — инъекция чистой AsyncSession.
    Для случаев, когда UoW избыточен (read-only операции).
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        super().__init__()
        self._session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self._session_factory() as session:
            data["session"] = session
            return await handler(event, data)
```

```python
"""
Использование в хендлерах:
"""
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from src.infrastructure.database.uow import UnitOfWork

router = Router(name="users")


@router.message(CommandStart())
async def cmd_start(message: Message, uow: UnitOfWork) -> None:
    """
    UoW инъектируется через middleware.
    aiogram 3 автоматически пробрасывает ключи из data в аргументы хендлера.
    """
    user = await uow.users.upsert_from_telegram(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        language_code=message.from_user.language_code,
        is_premium=message.from_user.is_premium or False,
    )
    await uow.commit()
    await message.answer(f"Добро пожаловать, {user.first_name}!")
```

### 2.7. Настройка Alembic для Async

```bash
# Инициализация Alembic с async-шаблоном
alembic init -t async alembic
```

```ini
# alembic.ini — ключевые параметры
[alembic]
script_location = alembic
# URL задаётся в env.py из конфигурации
# sqlalchemy.url = postgresql+asyncpg://user:pass@localhost/dbname
file_template = %%(year)d_%%(month).2d_%%(day).2d_%%(rev)s_%%(slug)s
```

```python
"""
alembic/env.py

Асинхронный env.py для Alembic.
Поддерживает автогенерацию миграций.
"""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from src.infrastructure.database.base import Base

# Импортируем ВСЕ модели, чтобы Alembic знал о них
from src.infrastructure.database.models.user import User  # noqa: F401
from src.infrastructure.database.models.subscription import Subscription  # noqa: F401

# Alembic Config
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Генерация SQL без подключения к БД."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,  # Отслеживать изменение типов колонок
        compare_server_default=True,  # Отслеживать изменение дефолтов
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Асинхронный запуск миграций."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Запуск миграций с подключением к БД."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### 2.8. Работа с миграциями

```bash
# Создание миграции (автогенерация из моделей)
alembic revision --autogenerate -m "add users table"

# Применение всех миграций
alembic upgrade head

# Откат на 1 шаг
alembic downgrade -1

# Откат к конкретной ревизии
alembic downgrade abc123

# Просмотр текущей ревизии
alembic current

# История миграций
alembic history --verbose

# Генерация SQL без применения (для ревью)
alembic upgrade head --sql > migration.sql
```

### 2.9. PostgreSQL vs SQLite

| Критерий | PostgreSQL | SQLite |
|----------|-----------|--------|
| **Параллелизм** | Полная поддержка | WAL mode, ограниченная запись |
| **Масштабирование** | До тысяч соединений | Один файл |
| **Типы данных** | JSONB, Array, UUID, INET | Базовые типы |
| **Async драйвер** | asyncpg (стабильный) | aiosqlite (менее надёжный) |
| **Полнотекстовый поиск** | pg_trgm, GIN indexes | FTS5 (ограниченный) |
| **Рекомендация** | Production | Прототипирование, тесты |

**Вердикт:** Для production-бота всегда PostgreSQL. SQLite допустим только для прототипов и юнит-тестов (через `aiosqlite`).

### 2.10. Интеграция с Dishka DI

```python
"""
Интеграция БД через Dishka — полная конфигурация.
Рекомендуемый подход для крупных проектов.
"""
from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide, make_async_container
from dishka.integrations.aiogram import AiogramProvider, FromDishka, setup_dishka
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.infrastructure.database.uow import UnitOfWork
from src.infrastructure.database.repositories.user import UserRepository


class DatabaseProvider(Provider):
    """Провайдер зависимостей для базы данных."""

    @provide(scope=Scope.APP)
    async def get_engine(self) -> AsyncIterator[AsyncEngine]:
        """AsyncEngine — singleton на всё время жизни приложения."""
        engine = create_async_engine(
            "postgresql+asyncpg://user:pass@localhost/botdb",
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
        yield engine
        await engine.dispose()

    @provide(scope=Scope.APP)
    def get_session_factory(
        self, engine: AsyncEngine,
    ) -> async_sessionmaker[AsyncSession]:
        """Фабрика сессий — singleton."""
        return async_sessionmaker(
            bind=engine,
            expire_on_commit=False,
            autoflush=False,
        )

    @provide(scope=Scope.REQUEST)
    async def get_session(
        self, factory: async_sessionmaker[AsyncSession],
    ) -> AsyncIterator[AsyncSession]:
        """AsyncSession — создаётся на каждый запрос (апдейт)."""
        async with factory() as session:
            yield session

    @provide(scope=Scope.REQUEST)
    def get_uow(
        self, factory: async_sessionmaker[AsyncSession],
    ) -> UnitOfWork:
        """UnitOfWork — для транзакционных операций."""
        return UnitOfWork(factory)

    @provide(scope=Scope.REQUEST)
    def get_user_repo(self, session: AsyncSession) -> UserRepository:
        """UserRepository — для read-only операций."""
        return UserRepository(session)


# ---------- Инициализация ----------
async def main() -> None:
    from aiogram import Bot, Dispatcher

    bot = Bot(token="YOUR_TOKEN")
    dp = Dispatcher()

    container = make_async_container(
        DatabaseProvider(),
        AiogramProvider(),
    )
    setup_dishka(container=container, router=dp, auto_inject=True)

    try:
        await dp.start_polling(bot)
    finally:
        await container.close()
        await bot.session.close()
```

```python
"""
Хендлер с Dishka — зависимости инъектируются автоматически.
"""
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from dishka.integrations.aiogram import FromDishka

from src.infrastructure.database.uow import UnitOfWork

router = Router(name="users")


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    uow: FromDishka[UnitOfWork],
) -> None:
    """UoW инъектируется через Dishka автоматически."""
    async with uow:
        user = await uow.users.upsert_from_telegram(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            language_code=message.from_user.language_code,
            is_premium=message.from_user.is_premium or False,
        )
        await uow.commit()

    await message.answer(f"Добро пожаловать, {user.first_name}!")
```

**Источники:**
- [SQLAlchemy 2.1 Async документация](https://docs.sqlalchemy.org/en/21/orm/extensions/asyncio.html)
- [MasterGroosha aiogram + SQLAlchemy demo](https://github.com/MasterGroosha/aiogram-and-sqlalchemy-demo)
- [Aiogram bot template с PostgreSQL + Alembic](https://github.com/wakaree/aiogram_bot_template)
- [Dishka интеграция с aiogram](https://dishka.readthedocs.io/en/stable/integrations/aiogram.html)
- [Cosmic Python — Unit of Work](https://www.cosmicpython.com/book/chapter_06_uow.html)

---

## 3. Redis

### 3.1. FSM Storage

Redis — рекомендуемое хранилище для FSM (Finite State Machine) в production. В отличие от `MemoryStorage`, данные сохраняются при перезапуске бота.

```python
"""
Настройка RedisStorage для FSM.
"""
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder


# Вариант 1: Простое подключение через URL
storage = RedisStorage.from_url(
    "redis://localhost:6379/0",
    state_ttl=3600,      # Состояние живёт 1 час
    data_ttl=3600,       # Данные живут 1 час
)

# Вариант 2: Тонкая настройка
from redis.asyncio import Redis

redis = Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True,
    max_connections=20,
)

storage = RedisStorage(
    redis=redis,
    key_builder=DefaultKeyBuilder(
        prefix="fsm",
        separator=":",
        with_bot_id=True,       # Разделение по ботам (мульти-бот)
        with_destiny=True,       # Разделение по контекстам
    ),
    state_ttl=7200,   # 2 часа
    data_ttl=7200,
)

# Создание диспетчера с Redis Storage
dp = Dispatcher(storage=storage)
```

```python
"""
Полный пример FSM с Redis Storage.
Сценарий: сбор обратной связи от пользователя.
"""
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove


class FeedbackForm(StatesGroup):
    """Состояния формы обратной связи."""
    waiting_for_category = State()
    waiting_for_text = State()
    waiting_for_rating = State()


router = Router(name="feedback")


@router.message(Command("feedback"))
async def cmd_feedback(message: Message, state: FSMContext) -> None:
    """Начало сбора обратной связи."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Качество"), KeyboardButton(text="Доставка")],
            [KeyboardButton(text="Сервис"), KeyboardButton(text="Другое")],
        ],
        resize_keyboard=True,
    )
    await state.set_state(FeedbackForm.waiting_for_category)
    await message.answer("Выберите категорию:", reply_markup=keyboard)


@router.message(FeedbackForm.waiting_for_category)
async def process_category(message: Message, state: FSMContext) -> None:
    """Обработка выбора категории."""
    valid_categories = {"Качество", "Доставка", "Сервис", "Другое"}
    if message.text not in valid_categories:
        await message.answer("Пожалуйста, выберите категорию из предложенных.")
        return

    await state.update_data(category=message.text)
    await state.set_state(FeedbackForm.waiting_for_text)
    await message.answer(
        "Опишите вашу проблему:",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(FeedbackForm.waiting_for_text)
async def process_text(message: Message, state: FSMContext) -> None:
    """Обработка текста обратной связи."""
    if len(message.text) < 10:
        await message.answer("Пожалуйста, опишите проблему подробнее (минимум 10 символов).")
        return

    await state.update_data(text=message.text)
    await state.set_state(FeedbackForm.waiting_for_rating)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=str(i)) for i in range(1, 6)]],
        resize_keyboard=True,
    )
    await message.answer("Оцените от 1 до 5:", reply_markup=keyboard)


@router.message(FeedbackForm.waiting_for_rating, F.text.in_({"1", "2", "3", "4", "5"}))
async def process_rating(message: Message, state: FSMContext) -> None:
    """Завершение формы."""
    data = await state.get_data()
    data["rating"] = int(message.text)

    # Здесь сохраняем в БД через UoW
    await message.answer(
        f"Спасибо за обратную связь!\n"
        f"Категория: {data['category']}\n"
        f"Оценка: {data['rating']}/5",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.clear()
```

### 3.2. Кеширование данных

```python
"""
src/infrastructure/cache/redis_cache.py

Сервис кеширования на Redis.
Используется для кеширования часто запрашиваемых данных:
каталог, настройки, профили пользователей.
"""
import json
from typing import Any

from redis.asyncio import Redis


class RedisCacheService:
    """
    Универсальный сервис кеширования.

    Паттерны:
    1. Cache-Aside: читаем из кеша, при промахе — из БД, пишем в кеш
    2. Write-Through: при записи в БД обновляем кеш
    3. TTL-based: автоматическая инвалидация по времени
    """

    def __init__(self, redis: Redis, default_ttl: int = 300) -> None:
        self._redis = redis
        self._default_ttl = default_ttl

    # ---------- Базовые операции ----------

    async def get(self, key: str) -> Any | None:
        """Получить значение из кеша."""
        value = await self._redis.get(key)
        if value is None:
            return None
        return json.loads(value)

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        """Записать значение в кеш."""
        await self._redis.set(
            key,
            json.dumps(value, ensure_ascii=False, default=str),
            ex=ttl or self._default_ttl,
        )

    async def delete(self, key: str) -> None:
        """Удалить значение из кеша."""
        await self._redis.delete(key)

    async def delete_pattern(self, pattern: str) -> None:
        """Удалить все ключи по шаблону (инвалидация группы)."""
        async for key in self._redis.scan_iter(pattern):
            await self._redis.delete(key)

    async def exists(self, key: str) -> bool:
        """Проверить наличие ключа."""
        return bool(await self._redis.exists(key))

    # ---------- Паттерн Cache-Aside ----------

    async def get_or_set(
        self,
        key: str,
        factory,  # Callable[[], Awaitable[Any]]
        ttl: int | None = None,
    ) -> Any:
        """
        Получить из кеша или вычислить и сохранить.

        Usage:
            data = await cache.get_or_set(
                f"user:{user_id}",
                lambda: repo.get_by_id(user_id),
                ttl=600,
            )
        """
        cached = await self.get(key)
        if cached is not None:
            return cached

        value = await factory()
        if value is not None:
            await self.set(key, value, ttl)
        return value

    # ---------- Инкременты / Счётчики ----------

    async def increment(self, key: str, amount: int = 1) -> int:
        """Атомарный инкремент (для счётчиков, лимитов)."""
        return await self._redis.incrby(key, amount)

    async def get_counter(self, key: str) -> int:
        """Получить значение счётчика."""
        value = await self._redis.get(key)
        return int(value) if value else 0

    # ---------- Hash-операции (для структур) ----------

    async def hset(self, key: str, field: str, value: Any) -> None:
        """Записать поле в hash."""
        await self._redis.hset(key, field, json.dumps(value, default=str))

    async def hget(self, key: str, field: str) -> Any | None:
        """Получить поле из hash."""
        value = await self._redis.hget(key, field)
        return json.loads(value) if value else None

    async def hgetall(self, key: str) -> dict[str, Any]:
        """Получить все поля hash."""
        raw = await self._redis.hgetall(key)
        return {k: json.loads(v) for k, v in raw.items()}
```

```python
"""
Использование кеша в хендлерах.
"""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="catalog")


@router.message(Command("catalog"))
async def cmd_catalog(
    message: Message,
    cache: RedisCacheService,
    uow: UnitOfWork,
) -> None:
    """Показать каталог с кешированием."""
    categories = await cache.get_or_set(
        key="catalog:categories",
        factory=lambda: get_categories_from_db(uow),
        ttl=600,  # 10 минут
    )

    text = "Категории:\n"
    for cat in categories:
        text += f"  - {cat['name']}\n"

    await message.answer(text)


async def get_categories_from_db(uow: UnitOfWork) -> list[dict]:
    """Загрузка категорий из БД (вызывается при cache miss)."""
    async with uow:
        categories = await uow.categories.get_all()
        return [{"id": c.id, "name": c.name} for c in categories]
```

### 3.3. Rate Limiting (Throttling)

```python
"""
src/middlewares/throttling.py

Middleware для ограничения частоты запросов.
Защита от спама и DDoS через Redis.
"""
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from redis.asyncio import Redis


class ThrottlingMiddleware(BaseMiddleware):
    """
    Ограничение частоты запросов (rate limiting).

    Использует Redis для хранения счётчиков.
    Алгоритм: Sliding Window Counter.
    """

    def __init__(
        self,
        redis: Redis,
        rate_limit: float = 0.5,  # Минимальный интервал между сообщениями (секунды)
        key_prefix: str = "throttle",
    ) -> None:
        super().__init__()
        self._redis = redis
        self._rate_limit = rate_limit
        self._key_prefix = key_prefix

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        key = f"{self._key_prefix}:{user.id}"

        # Проверяем, есть ли активный throttle
        if await self._redis.exists(key):
            # Пользователь отправляет слишком часто — игнорируем
            return None

        # Устанавливаем throttle
        await self._redis.set(key, "1", ex=self._rate_limit)

        return await handler(event, data)


class AdvancedThrottlingMiddleware(BaseMiddleware):
    """
    Продвинутый throttling с разными лимитами для разных хендлеров.

    Использование:
        @router.message(Command("heavy_command"))
        @rate_limit(limit=5.0, key="heavy")
        async def heavy_handler(message: Message) -> None:
            ...
    """

    def __init__(self, redis: Redis) -> None:
        super().__init__()
        self._redis = redis

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        # Получаем настройки rate_limit из хендлера (если есть)
        real_handler = data.get("handler")
        if real_handler is not None:
            throttle_key = getattr(
                real_handler.callback, "throttle_key", "default"
            )
            throttle_rate = getattr(
                real_handler.callback, "throttle_rate", 0.5
            )
        else:
            throttle_key = "default"
            throttle_rate = 0.5

        key = f"throttle:{throttle_key}:{user.id}"

        if await self._redis.exists(key):
            # Можно отправить предупреждение при первом превышении
            exceeded_key = f"throttle_warn:{throttle_key}:{user.id}"
            if not await self._redis.exists(exceeded_key):
                await self._redis.set(exceeded_key, "1", ex=int(throttle_rate))
                if isinstance(event, Message):
                    await event.answer(
                        "⏳ Слишком быстро! Подождите немного."
                    )
            return None

        await self._redis.set(
            key, "1", px=int(throttle_rate * 1000)
        )

        return await handler(event, data)


def rate_limit(limit: float = 0.5, key: str = "default"):
    """
    Декоратор для задания rate limit на уровне хендлера.

    @rate_limit(limit=5.0, key="broadcast")
    async def handler(...): ...
    """
    def decorator(func):
        func.throttle_rate = limit
        func.throttle_key = key
        return func
    return decorator
```

### 3.4. Session Management и Lock

```python
"""
src/infrastructure/cache/redis_lock.py

Распределённые блокировки через Redis.
Для операций, которые не должны выполняться параллельно.
"""
import uuid
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from redis.asyncio import Redis


class RedisLock:
    """
    Распределённая блокировка на Redis.

    Сценарии:
    - Предотвращение двойной оплаты
    - Атомарное обновление баланса
    - Защита от race condition при одновременных нажатиях
    """

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    @asynccontextmanager
    async def acquire(
        self,
        key: str,
        timeout: int = 10,
        blocking_timeout: float = 5.0,
    ) -> AsyncIterator[bool]:
        """
        Захватить блокировку.

        Args:
            key: Уникальный ключ блокировки
            timeout: Автоматическое освобождение через N секунд
            blocking_timeout: Максимальное время ожидания блокировки

        Usage:
            async with lock.acquire(f"payment:{user_id}") as acquired:
                if acquired:
                    await process_payment(...)
                else:
                    await message.answer("Операция уже выполняется")
        """
        lock_key = f"lock:{key}"
        lock_value = str(uuid.uuid4())
        acquired = False

        try:
            acquired = await self._redis.set(
                lock_key,
                lock_value,
                nx=True,  # Только если не существует
                ex=timeout,
            )
            yield bool(acquired)
        finally:
            if acquired:
                # Удаляем только свою блокировку (Lua-скрипт для атомарности)
                script = """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("del", KEYS[1])
                else
                    return 0
                end
                """
                await self._redis.eval(script, 1, lock_key, lock_value)


# ---------- Использование в хендлерах ----------

@router.callback_query(F.data.startswith("buy:"))
async def process_purchase(
    callback: CallbackQuery,
    lock: RedisLock,
    uow: UnitOfWork,
) -> None:
    """Обработка покупки с блокировкой."""
    user_id = callback.from_user.id
    product_id = callback.data.split(":")[1]

    async with lock.acquire(f"purchase:{user_id}:{product_id}") as acquired:
        if not acquired:
            await callback.answer("Операция уже обрабатывается!", show_alert=True)
            return

        async with uow:
            # Безопасная обработка покупки
            success = await process_payment(uow, user_id, product_id)
            if success:
                await uow.commit()
                await callback.answer("Покупка успешна!")
            else:
                await callback.answer("Недостаточно средств", show_alert=True)
```

**Источники:**
- [Aiogram FSM Storages документация](https://docs.aiogram.dev/en/latest/dispatcher/finite_state_machine/storages.html)
- [Aiogram RedisStorage исходный код](https://docs.aiogram.dev/en/latest/_modules/aiogram/fsm/storage/redis.html)
- [Aiogram 3 Middlewares документация](https://docs.aiogram.dev/en/latest/dispatcher/middlewares.html)
- [GitHub Issue: ThrottlingMiddleware](https://github.com/aiogram/aiogram/issues/1413)

---

## 4. Очереди задач (Task Queues)

### 4.1. Сравнение решений

| Критерий | Taskiq | ARQ | Celery |
|----------|--------|-----|--------|
| **Async-native** | Да | Да | Нет (есть обёртки) |
| **Интеграция с aiogram** | Официальная (taskiq-aiogram) | Нет | Нет |
| **Брокеры** | Redis, RabbitMQ, NATS, Kafka | Только Redis | Redis, RabbitMQ |
| **Планировщик** | Встроенный | Встроенный (cron) | Celery Beat |
| **Dead Letter Queue** | Да (через RabbitMQ) | Да (через Redis) | Да |
| **Retry** | Встроенный | Встроенный | Встроенный |
| **Вес** | Лёгкий | Минимальный | Тяжёлый |
| **Экосистема** | Активно развивается | Стабильный | Зрелый |
| **Рекомендация** | **Для aiogram** | Для простых случаев | Для legacy |

**Вердикт:** Для Telegram-бота на aiogram 3.x — однозначно **Taskiq**. Он async-native, имеет официальную интеграцию с aiogram, поддерживает множество брокеров и активно развивается.

### 4.2. Настройка Taskiq с Aiogram

```python
"""
src/worker/broker.py

Настройка брокера Taskiq.
"""
import taskiq_aiogram
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

# Брокер: Redis для очереди задач
broker = ListQueueBroker(
    "redis://localhost:6379/1",
).with_result_backend(
    RedisAsyncResultBackend(
        redis_url="redis://localhost:6379/2",
    )
)

# Интеграция с aiogram — указываем пути к dp и bot
taskiq_aiogram.init(
    broker,
    "src.bot:dp",    # Путь к Dispatcher
    "src.bot:bot",   # Путь к Bot
)
```

```python
"""
src/worker/tasks.py

Определение фоновых задач.
"""
import asyncio
import logging
from typing import Any

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from taskiq import TaskiqDepends

from src.worker.broker import broker

logger = logging.getLogger(__name__)


@broker.task(task_name="send_delayed_message")
async def send_delayed_message(
    chat_id: int,
    text: str,
    delay_seconds: int = 0,
    bot: Bot = TaskiqDepends(),
) -> dict[str, Any]:
    """
    Отправка отложенного сообщения.

    Используется для:
    - Напоминания
    - Отложенные уведомления
    - Follow-up сообщения
    """
    if delay_seconds > 0:
        await asyncio.sleep(delay_seconds)

    try:
        result = await bot.send_message(chat_id=chat_id, text=text)
        return {"status": "sent", "message_id": result.message_id}
    except Exception as e:
        logger.error("Failed to send message to %d: %s", chat_id, e)
        return {"status": "error", "error": str(e)}


@broker.task(task_name="broadcast_message")
async def broadcast_message(
    user_ids: list[int],
    text: str,
    bot: Bot = TaskiqDepends(),
) -> dict[str, Any]:
    """
    Массовая рассылка сообщений.

    Соблюдаем лимиты Telegram API:
    - Не более 30 сообщений в секунду
    - Не более 20 сообщений в секунду в один чат
    """
    sent = 0
    failed = 0
    blocked = 0

    for user_id in user_ids:
        try:
            await bot.send_message(chat_id=user_id, text=text)
            sent += 1
        except Exception as e:
            error_msg = str(e).lower()
            if "blocked" in error_msg or "deactivated" in error_msg:
                blocked += 1
            else:
                failed += 1
                logger.warning("Broadcast failed for %d: %s", user_id, e)

        # Соблюдаем rate limit Telegram (30 msg/sec)
        await asyncio.sleep(0.05)  # ~20 msg/sec — с запасом

    return {
        "total": len(user_ids),
        "sent": sent,
        "failed": failed,
        "blocked": blocked,
    }


@broker.task(
    task_name="generate_report",
    retry_on_error=True,
    max_retries=3,
)
async def generate_report(
    chat_id: int,
    report_type: str,
    bot: Bot = TaskiqDepends(),
) -> None:
    """
    Генерация тяжёлого отчёта в фоне.

    retry_on_error=True — автоматический перезапуск при ошибке.
    """
    # Уведомляем пользователя о начале генерации
    status_msg = await bot.send_message(
        chat_id=chat_id,
        text="📊 Генерация отчёта... Это может занять несколько минут.",
    )

    try:
        # Тяжёлая операция
        report_data = await generate_heavy_report(report_type)

        # Отправляем результат
        await bot.send_document(
            chat_id=chat_id,
            document=report_data,
            caption=f"Отчёт: {report_type}",
        )
    except Exception as e:
        await bot.send_message(
            chat_id=chat_id,
            text=f"Ошибка генерации отчёта: {e}",
        )
        raise  # retry_on_error перехватит


@broker.task(task_name="process_payment_webhook")
async def process_payment_webhook(
    payment_data: dict[str, Any],
    bot: Bot = TaskiqDepends(),
) -> None:
    """
    Обработка вебхука платёжной системы в фоне.

    Вынесено в таск, чтобы не блокировать ответ платёжной системе.
    """
    user_id = payment_data["user_id"]
    amount = payment_data["amount"]

    # Обновляем баланс в БД
    # async with uow: ...

    # Уведомляем пользователя
    await bot.send_message(
        chat_id=user_id,
        text=f"Оплата на сумму {amount}₽ получена! Спасибо!",
    )
```

### 4.3. Вызов задач из хендлеров

```python
"""
src/handlers/admin.py

Вызов фоновых задач из хендлеров бота.
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from src.worker.tasks import (
    send_delayed_message,
    broadcast_message,
    generate_report,
)
from src.infrastructure.database.uow import UnitOfWork

router = Router(name="admin")


@router.message(Command("remind"))
async def cmd_remind(message: Message) -> None:
    """Установить напоминание через 1 час."""
    # kiq() — отправка задачи в очередь (kick into queue)
    await send_delayed_message.kiq(
        chat_id=message.chat.id,
        text="Напоминание: не забудьте проверить заказы!",
        delay_seconds=3600,
    )
    await message.answer("Напоминание установлено на 1 час!")


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, uow: UnitOfWork) -> None:
    """Массовая рассылка всем пользователям."""
    text = message.text.replace("/broadcast ", "", 1)
    if not text or text == "/broadcast":
        await message.answer("Использование: /broadcast <текст>")
        return

    async with uow:
        users = await uow.users.get_active_users(limit=10000)
        user_ids = [u.id for u in users]

    # Отправляем в фоновую задачу
    task = await broadcast_message.kiq(
        user_ids=user_ids,
        text=text,
    )
    await message.answer(
        f"Рассылка запущена для {len(user_ids)} пользователей.\n"
        f"Task ID: {task.task_id}"
    )


@router.message(Command("report"))
async def cmd_report(message: Message) -> None:
    """Сгенерировать отчёт в фоне."""
    await generate_report.kiq(
        chat_id=message.chat.id,
        report_type="weekly_sales",
    )
    await message.answer("Генерация отчёта запущена...")
```

### 4.4. Lifecycle — startup/shutdown

```python
"""
src/bot.py

Правильная инициализация и остановка брокера.
"""
from aiogram import Bot, Dispatcher

from src.worker.broker import broker

bot = Bot(token="YOUR_TOKEN")
dp = Dispatcher()


@dp.startup()
async def on_startup(bot: Bot) -> None:
    """Запуск брокера при старте бота."""
    # Не запускаем брокер в worker-процессе
    if not broker.is_worker_process:
        await broker.startup()


@dp.shutdown()
async def on_shutdown(bot: Bot) -> None:
    """Остановка брокера при завершении бота."""
    if not broker.is_worker_process:
        await broker.shutdown()
```

```bash
# Запуск worker-процесса (отдельный терминал)
taskiq worker src.worker.broker:broker

# Запуск планировщика (если используются cron-задачи)
taskiq scheduler src.worker.scheduler:scheduler
```

### 4.5. Планирование задач (Scheduler)

```python
"""
src/worker/scheduler.py

Планировщик периодических задач.
"""
from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource

from src.worker.broker import broker

scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)
```

```python
"""
src/worker/periodic_tasks.py

Периодические задачи с cron-расписанием.
"""
from aiogram import Bot
from taskiq import TaskiqDepends

from src.worker.broker import broker


@broker.task(
    task_name="daily_stats",
    schedule=[{"cron": "0 9 * * *"}],  # Каждый день в 9:00
)
async def daily_stats(bot: Bot = TaskiqDepends()) -> None:
    """Ежедневная отправка статистики админу."""
    # Собираем статистику из БД
    stats = await collect_daily_stats()

    await bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"📊 Статистика за сегодня:\n{stats}",
    )


@broker.task(
    task_name="cleanup_expired_sessions",
    schedule=[{"cron": "0 */6 * * *"}],  # Каждые 6 часов
)
async def cleanup_expired_sessions() -> None:
    """Очистка истёкших сессий."""
    # ...


@broker.task(
    task_name="check_subscriptions",
    schedule=[{"cron": "0 8 * * *"}],  # Каждый день в 8:00
)
async def check_subscriptions(bot: Bot = TaskiqDepends()) -> None:
    """Проверка истекающих подписок и уведомление пользователей."""
    # Находим подписки, истекающие через 3 дня
    expiring = await get_expiring_subscriptions(days=3)

    for sub in expiring:
        try:
            await bot.send_message(
                chat_id=sub.user_id,
                text=(
                    f"Ваша подписка '{sub.plan}' истекает "
                    f"через {sub.days_left} дня. Продлите её!"
                ),
            )
        except Exception:
            pass  # Пользователь заблокировал бота

        await asyncio.sleep(0.05)
```

### 4.6. Динамическое планирование через Redis

```python
"""
Динамическое планирование задач (не через cron, а по запросу).
Полезно для пользовательских напоминаний.
"""
import datetime

from taskiq_redis import RedisScheduleSource

from src.worker.broker import broker
from src.worker.tasks import send_delayed_message

# Источник расписания на Redis
redis_schedule_source = RedisScheduleSource("redis://localhost:6379/3")


async def schedule_reminder(
    user_id: int,
    text: str,
    remind_at: datetime.datetime,
) -> str:
    """
    Запланировать напоминание на конкретное время.
    Возвращает schedule_id для возможной отмены.
    """
    await redis_schedule_source.startup()

    schedule = await send_delayed_message.schedule_by_time(
        redis_schedule_source,
        remind_at,
        chat_id=user_id,
        text=text,
    )

    return schedule.schedule_id


async def cancel_reminder(schedule_id: str) -> None:
    """Отменить запланированное напоминание."""
    # schedule.unschedule() — отменяет задачу
    pass
```

### 4.7. Retry и Dead Letter Queue

```python
"""
Настройка retry и DLQ через RabbitMQ.
"""
from taskiq_aio_pika import AioPikaBroker

# Брокер с RabbitMQ + Dead Letter Queue
broker = AioPikaBroker(
    "amqp://guest:guest@localhost:5672/",
    # DLQ: сообщения, которые не удалось обработать, попадают сюда
    dead_letter_queue_name="bot_dlq",
    # Delayed messages через DLQ
    delay_queue="bot_delayed",
)


@broker.task(
    task_name="critical_operation",
    retry_on_error=True,
    max_retries=5,
)
async def critical_operation(data: dict) -> None:
    """
    Критическая операция с повторными попытками.

    После 5 неудачных попыток задача попадёт в DLQ,
    где её можно проанализировать и обработать вручную.
    """
    # Бизнес-логика
    pass
```

**Источники:**
- [Taskiq + Aiogram интеграция](https://taskiq-python.github.io/framework_integrations/taskiq-with-aiogram.html)
- [taskiq-aiogram на PyPI](https://pypi.org/project/taskiq-aiogram/)
- [Taskiq GitHub](https://github.com/taskiq-python/taskiq)
- [Taskiq scheduling tasks](https://taskiq-python.github.io/guide/scheduling-tasks.html)
- [ARQ vs Taskiq сравнение](https://chris48s.github.io/blogmarks/posts/2024/arq-taskiq/)
- [Celery vs ARQ](https://leapcell.io/blog/celery-versus-arq-choosing-the-right-task-queue-for-python-applications)
- [taskiq-aio-pika (RabbitMQ)](https://github.com/taskiq-python/taskiq-aio-pika)

---

## 5. Интеграция с внешними API

### 5.1. Паттерн API-клиента с переиспользованием сессии

```python
"""
src/infrastructure/http/base_client.py

Базовый HTTP-клиент с правильным lifecycle aiohttp.ClientSession.

Ключевые правила:
1. Один ClientSession на всё время жизни приложения
2. Не создавать сессию в каждом запросе
3. Закрывать сессию при остановке приложения
"""
import logging
from typing import Any

import aiohttp
from aiohttp import ClientTimeout

logger = logging.getLogger(__name__)


class BaseHTTPClient:
    """
    Базовый HTTP-клиент.

    Переиспользует одну ClientSession для всех запросов.
    Поддерживает retry, timeout, и базовую обработку ошибок.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = ClientTimeout(total=timeout)
        self._headers = headers or {}
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Lazy initialization сессии."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                base_url=self._base_url,
                timeout=self._timeout,
                headers=self._headers,
                # Оптимизация: переиспользование TCP-соединений
                connector=aiohttp.TCPConnector(
                    limit=100,          # Макс. соединений
                    limit_per_host=30,  # Макс. соединений на хост
                    ttl_dns_cache=600,  # DNS-кеш на 10 минут
                    keepalive_timeout=30,
                ),
            )
        return self._session

    async def close(self) -> None:
        """Закрыть сессию. Вызывать при shutdown."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Базовый метод запроса."""
        session = await self._get_session()

        try:
            async with session.request(method, path, **kwargs) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as e:
            logger.error(
                "HTTP %d %s %s: %s",
                e.status, method, path, e.message,
            )
            raise
        except aiohttp.ClientConnectionError as e:
            logger.error("Connection error %s %s: %s", method, path, e)
            raise
        except TimeoutError:
            logger.error("Timeout %s %s", method, path)
            raise

    async def get(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return await self._request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return await self._request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return await self._request("PUT", path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return await self._request("DELETE", path, **kwargs)
```

### 5.2. Retry с exponential backoff

```python
"""
src/infrastructure/http/retry_client.py

HTTP-клиент с retry, exponential backoff и jitter.
"""
import asyncio
import random
import logging
from typing import Any

import aiohttp
from aiohttp import ClientTimeout

logger = logging.getLogger(__name__)


class RetryConfig:
    """Конфигурация повторных попыток."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retry_statuses: set[int] | None = None,
        retry_exceptions: tuple[type[Exception], ...] = (
            aiohttp.ClientConnectionError,
            asyncio.TimeoutError,
        ),
    ) -> None:
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_statuses = retry_statuses or {429, 500, 502, 503, 504}
        self.retry_exceptions = retry_exceptions

    def get_delay(self, attempt: int) -> float:
        """
        Вычисляет задержку с exponential backoff + jitter.

        attempt=0: base_delay * 1 = 1s
        attempt=1: base_delay * 2 = 2s
        attempt=2: base_delay * 4 = 4s
        + random jitter ±25%
        """
        delay = self.base_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            delay *= 0.75 + random.random() * 0.5  # ±25%

        return delay


class RetryHTTPClient:
    """HTTP-клиент с автоматическим retry."""

    def __init__(
        self,
        base_url: str,
        retry_config: RetryConfig | None = None,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._retry = retry_config or RetryConfig()
        self._timeout = ClientTimeout(total=timeout)
        self._headers = headers or {}
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                base_url=self._base_url,
                timeout=self._timeout,
                headers=self._headers,
                connector=aiohttp.TCPConnector(
                    limit=50,
                    limit_per_host=20,
                ),
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Запрос с автоматическим retry.

        Повторяет запрос при:
        - Сетевых ошибках (ConnectionError, Timeout)
        - HTTP статусах 429, 500, 502, 503, 504
        """
        session = await self._get_session()
        last_exception: Exception | None = None

        for attempt in range(self._retry.max_retries + 1):
            try:
                async with session.request(method, path, **kwargs) as resp:
                    # Проверяем, нужен ли retry по статусу
                    if resp.status in self._retry.retry_statuses:
                        if attempt < self._retry.max_retries:
                            # Для 429 используем Retry-After, если есть
                            retry_after = resp.headers.get("Retry-After")
                            if retry_after and resp.status == 429:
                                delay = float(retry_after)
                            else:
                                delay = self._retry.get_delay(attempt)

                            logger.warning(
                                "Retry %d/%d %s %s (status %d, delay %.1fs)",
                                attempt + 1,
                                self._retry.max_retries,
                                method,
                                path,
                                resp.status,
                                delay,
                            )
                            await asyncio.sleep(delay)
                            continue

                    resp.raise_for_status()
                    return await resp.json()

            except self._retry.retry_exceptions as e:
                last_exception = e
                if attempt < self._retry.max_retries:
                    delay = self._retry.get_delay(attempt)
                    logger.warning(
                        "Retry %d/%d %s %s (%s, delay %.1fs)",
                        attempt + 1,
                        self._retry.max_retries,
                        method,
                        path,
                        type(e).__name__,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "All retries exhausted %s %s: %s",
                        method, path, e,
                    )

        raise last_exception or RuntimeError("All retries exhausted")

    async def get(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return await self.request("POST", path, **kwargs)
```

### 5.3. Использование aiohttp-retry

```python
"""
Альтернатива — использование библиотеки aiohttp-retry.
Менее кода, но менее гибко.
"""
from aiohttp import ClientSession
from aiohttp_retry import RetryClient, ExponentialRetry


async def create_retry_client() -> RetryClient:
    """
    Создание клиента с автоматическим retry.

    pip install aiohttp-retry
    """
    retry_options = ExponentialRetry(
        attempts=3,
        start_timeout=1.0,
        max_timeout=30.0,
        factor=2.0,
        statuses={429, 500, 502, 503, 504},
    )

    client = RetryClient(
        client_session=ClientSession(
            base_url="https://api.example.com",
        ),
        retry_options=retry_options,
        raise_for_status=True,
    )

    return client


# Использование
async def fetch_data() -> dict:
    async with create_retry_client() as client:
        async with client.get("/api/v1/data") as resp:
            return await resp.json()
```

### 5.4. Circuit Breaker

```python
"""
src/infrastructure/http/circuit_breaker.py

Реализация паттерна Circuit Breaker.
Предотвращает каскадные отказы при падении внешнего API.

Состояния:
- CLOSED: нормальная работа, запросы проходят
- OPEN: API недоступен, запросы блокируются (быстрый fail)
- HALF_OPEN: пробный запрос для проверки восстановления
"""
import asyncio
import time
import logging
from enum import Enum
from typing import Any, Callable, TypeVar
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerError(Exception):
    """Ошибка — circuit breaker в состоянии OPEN."""

    def __init__(self, remaining_seconds: float) -> None:
        self.remaining_seconds = remaining_seconds
        super().__init__(
            f"Circuit breaker is OPEN. "
            f"Retry in {remaining_seconds:.1f} seconds."
        )


class CircuitBreaker:
    """
    Circuit Breaker для защиты от каскадных отказов.

    Параметры:
        failure_threshold: Количество ошибок для перехода в OPEN
        recovery_timeout: Время ожидания перед пробным запросом (HALF_OPEN)
        expected_exceptions: Исключения, которые считаются "отказом"
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        expected_exceptions: tuple[type[Exception], ...] = (Exception,),
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._expected_exceptions = expected_exceptions

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Текущее состояние circuit breaker."""
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self._recovery_timeout:
                return CircuitState.HALF_OPEN
        return self._state

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        Выполнить функцию через circuit breaker.

        Raises:
            CircuitBreakerError: Если circuit breaker в состоянии OPEN
        """
        async with self._lock:
            current_state = self.state

            if current_state == CircuitState.OPEN:
                remaining = (
                    self._recovery_timeout
                    - (time.monotonic() - self._last_failure_time)
                )
                raise CircuitBreakerError(remaining)

        try:
            result = await func(*args, **kwargs)

            # Успех — сбрасываем счётчик
            async with self._lock:
                self._failure_count = 0
                if self._state != CircuitState.CLOSED:
                    logger.info("Circuit breaker CLOSED (recovered)")
                self._state = CircuitState.CLOSED

            return result

        except self._expected_exceptions as e:
            async with self._lock:
                self._failure_count += 1
                self._last_failure_time = time.monotonic()

                if self._failure_count >= self._failure_threshold:
                    self._state = CircuitState.OPEN
                    logger.warning(
                        "Circuit breaker OPEN after %d failures: %s",
                        self._failure_count,
                        e,
                    )

            raise


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
    expected_exceptions: tuple[type[Exception], ...] = (Exception,),
):
    """
    Декоратор circuit breaker.

    Использование:
        @circuit_breaker(failure_threshold=3, recovery_timeout=60)
        async def call_external_api():
            ...
    """
    cb = CircuitBreaker(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        expected_exceptions=expected_exceptions,
    )

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await cb.call(func, *args, **kwargs)

        wrapper.circuit_breaker = cb  # Доступ к CB для мониторинга
        return wrapper

    return decorator
```

### 5.5. Конкретный API-клиент (пример)

```python
"""
src/infrastructure/http/payment_client.py

Клиент платёжной системы с retry и circuit breaker.
"""
import logging
from typing import Any
from dataclasses import dataclass

import aiohttp

from src.infrastructure.http.retry_client import RetryHTTPClient, RetryConfig
from src.infrastructure.http.circuit_breaker import circuit_breaker, CircuitBreakerError

logger = logging.getLogger(__name__)


@dataclass
class PaymentResult:
    success: bool
    transaction_id: str | None = None
    error: str | None = None


class PaymentAPIClient:
    """
    Клиент платёжной системы.

    Объединяет:
    - Retry с exponential backoff
    - Circuit breaker
    - Правильное управление сессией
    """

    def __init__(
        self,
        api_url: str,
        api_key: str,
    ) -> None:
        self._client = RetryHTTPClient(
            base_url=api_url,
            retry_config=RetryConfig(
                max_retries=3,
                base_delay=1.0,
                retry_statuses={429, 500, 502, 503},
            ),
            timeout=15.0,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    async def close(self) -> None:
        await self._client.close()

    @circuit_breaker(
        failure_threshold=5,
        recovery_timeout=60.0,
        expected_exceptions=(aiohttp.ClientError, TimeoutError),
    )
    async def create_payment(
        self,
        amount: int,
        currency: str,
        description: str,
        metadata: dict[str, Any] | None = None,
    ) -> PaymentResult:
        """Создать платёж."""
        try:
            response = await self._client.post(
                "/api/v1/payments",
                json={
                    "amount": amount,
                    "currency": currency,
                    "description": description,
                    "metadata": metadata or {},
                },
            )
            return PaymentResult(
                success=True,
                transaction_id=response["transaction_id"],
            )
        except aiohttp.ClientResponseError as e:
            if e.status == 400:
                return PaymentResult(success=False, error=response.get("error", str(e)))
            raise

    @circuit_breaker(
        failure_threshold=5,
        recovery_timeout=60.0,
        expected_exceptions=(aiohttp.ClientError, TimeoutError),
    )
    async def check_payment_status(
        self,
        transaction_id: str,
    ) -> dict[str, Any]:
        """Проверить статус платежа."""
        return await self._client.get(f"/api/v1/payments/{transaction_id}")
```

### 5.6. Интеграция клиентов через Dishka

```python
"""
Провайдер HTTP-клиентов для Dishka DI.
"""
from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide

from src.infrastructure.http.payment_client import PaymentAPIClient


class HTTPClientsProvider(Provider):
    """Провайдер HTTP-клиентов."""

    @provide(scope=Scope.APP)
    async def get_payment_client(self) -> AsyncIterator[PaymentAPIClient]:
        """
        PaymentAPIClient — singleton на всё время жизни приложения.
        Сессия переиспользуется между запросами.
        """
        client = PaymentAPIClient(
            api_url="https://api.payment.com",
            api_key="your-api-key",
        )
        yield client
        await client.close()
```

```python
"""
Использование в хендлерах.
"""
from aiogram import Router
from aiogram.types import CallbackQuery
from dishka.integrations.aiogram import FromDishka

from src.infrastructure.http.payment_client import PaymentAPIClient, PaymentResult
from src.infrastructure.http.circuit_breaker import CircuitBreakerError

router = Router(name="payments")


@router.callback_query(F.data.startswith("pay:"))
async def process_payment(
    callback: CallbackQuery,
    payment_client: FromDishka[PaymentAPIClient],
) -> None:
    """Обработка оплаты через внешний API."""
    amount = int(callback.data.split(":")[1])

    try:
        result: PaymentResult = await payment_client.create_payment(
            amount=amount,
            currency="RUB",
            description=f"Заказ от пользователя {callback.from_user.id}",
        )

        if result.success:
            await callback.answer("Платёж создан!")
            await callback.message.answer(
                f"Перейдите по ссылке для оплаты: ...\n"
                f"ID транзакции: {result.transaction_id}"
            )
        else:
            await callback.answer(f"Ошибка: {result.error}", show_alert=True)

    except CircuitBreakerError as e:
        await callback.answer(
            f"Платёжная система временно недоступна. "
            f"Попробуйте через {e.remaining_seconds:.0f} сек.",
            show_alert=True,
        )
```

### 5.7. Использование tenacity для retry

```python
"""
Альтернативный подход — retry через tenacity.
Более декларативный и гибкий.
"""
import aiohttp
import asyncio
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import logging

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=60),
    retry=retry_if_exception_type((
        aiohttp.ClientConnectionError,
        asyncio.TimeoutError,
        aiohttp.ServerDisconnectedError,
    )),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def fetch_with_retry(
    session: aiohttp.ClientSession,
    url: str,
) -> dict:
    """
    Запрос с декларативным retry через tenacity.

    Стратегия:
    - До 5 попыток
    - Exponential backoff: 1s, 2s, 4s, 8s, 16s (max 60s)
    - Retry на сетевые ошибки и таймауты
    """
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
        resp.raise_for_status()
        return await resp.json()
```

**Источники:**
- [aiohttp Request Lifecycle](https://docs.aiohttp.org/en/latest/http_request_lifecycle.html)
- [aiohttp-retry на PyPI](https://pypi.org/project/aiohttp-retry/)
- [Tenacity retry для aiohttp](https://likegeeks.com/retry-requests-aiohttp-tenacity/)
- [aiomisc Circuit Breaker](https://aiomisc.readthedocs.io/en/latest/circuit_breaker.html)
- [aiobreaker — async Circuit Breaker](https://github.com/arlyon/aiobreaker)
- [Aiogram AiohttpSession](https://docs.aiogram.dev/en/latest/api/session/aiohttp.html)

---

## 6. Анти-паттерны

### 6.1. Блокирующие вызовы в async-коде

Это **самый распространённый и опасный** анти-паттерн. Блокирующий вызов "замораживает" весь event loop, и все пользователи бота перестают получать ответы.

```python
"""
АНТИ-ПАТТЕРН: Блокирующие вызовы в async-хендлерах.
"""
import time
import requests  # Синхронная библиотека!

from aiogram import Router
from aiogram.types import Message

router = Router()


# ❌ ПЛОХО: requests блокирует event loop
@router.message()
async def bad_handler(message: Message) -> None:
    # Этот вызов ЗАБЛОКИРУЕТ весь event loop на время запроса!
    # Ни один другой пользователь не получит ответ.
    response = requests.get("https://api.example.com/data", timeout=30)
    await message.answer(response.text)


# ❌ ПЛОХО: time.sleep блокирует event loop
@router.message()
async def bad_sleep(message: Message) -> None:
    time.sleep(5)  # ВСЁ ЗАМЕРЛО НА 5 СЕКУНД!
    await message.answer("Готово")


# ❌ ПЛОХО: синхронная работа с файлами
@router.message()
async def bad_file_handler(message: Message) -> None:
    with open("large_file.csv") as f:
        data = f.read()  # Блокирует при большом файле
    await message.answer(f"Прочитано {len(data)} байт")


# ❌ ПЛОХО: CPU-bound операция в event loop
@router.message()
async def bad_cpu_handler(message: Message) -> None:
    # Тяжёлое вычисление блокирует event loop
    result = sum(i * i for i in range(10_000_000))
    await message.answer(str(result))
```

```python
"""
ПРАВИЛЬНЫЕ РЕШЕНИЯ для блокирующих операций.
"""
import asyncio
import aiohttp
import aiofiles
from concurrent.futures import ProcessPoolExecutor

from aiogram import Router
from aiogram.types import Message

router = Router()


# ✅ ХОРОШО: используем aiohttp вместо requests
@router.message()
async def good_http_handler(message: Message) -> None:
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.example.com/data") as resp:
            data = await resp.text()
    await message.answer(data)


# ✅ ХОРОШО: asyncio.sleep вместо time.sleep
@router.message()
async def good_sleep(message: Message) -> None:
    await asyncio.sleep(5)  # Не блокирует event loop
    await message.answer("Готово")


# ✅ ХОРОШО: aiofiles для работы с файлами
@router.message()
async def good_file_handler(message: Message) -> None:
    async with aiofiles.open("large_file.csv") as f:
        data = await f.read()
    await message.answer(f"Прочитано {len(data)} байт")


# ✅ ХОРОШО: CPU-bound через ProcessPoolExecutor
@router.message()
async def good_cpu_handler(message: Message) -> None:
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        ProcessPoolExecutor(),
        heavy_computation,
        10_000_000,
    )
    await message.answer(str(result))


def heavy_computation(n: int) -> int:
    """Тяжёлое вычисление (вынесено в отдельный процесс)."""
    return sum(i * i for i in range(n))


# ✅ ХОРОШО: asyncio.to_thread для синхронных функций (Python 3.9+)
@router.message()
async def good_sync_in_thread(message: Message) -> None:
    result = await asyncio.to_thread(
        some_sync_library_call,
        param1="value",
    )
    await message.answer(str(result))
```

### 6.2. Утечки соединений к БД

```python
"""
АНТИ-ПАТТЕРН: Утечки соединений к базе данных.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

engine = create_async_engine("postgresql+asyncpg://...")
session_factory = async_sessionmaker(engine)


# ❌ ПЛОХО: сессия не закрывается при ошибке
@router.message()
async def bad_db_handler(message: Message) -> None:
    session = session_factory()
    user = await session.get(User, message.from_user.id)
    # Если здесь возникнет исключение — сессия НИКОГДА не закроется!
    # Соединение останется "залипшим" в пуле.
    await session.commit()
    await session.close()
    await message.answer(f"Привет, {user.name}")


# ❌ ПЛОХО: множественные сессии без закрытия
@router.message()
async def bad_multiple_sessions(message: Message) -> None:
    session1 = session_factory()
    users = await session1.execute(select(User))
    # Забыли закрыть session1!

    session2 = session_factory()
    orders = await session2.execute(select(Order))
    # Забыли закрыть session2!

    await message.answer("Done")


# ❌ ПЛОХО: commit() вместо flush() в репозитории
class BadUserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.commit()  # ПЛОХО: commit в репозитории!
        # Это нарушает Unit of Work — если после create()
        # будет ещё операция, и она упадёт,
        # нельзя откатить предыдущий commit.
        return user
```

```python
"""
ПРАВИЛЬНЫЕ РЕШЕНИЯ: управление соединениями.
"""

# ✅ ХОРОШО: context manager гарантирует закрытие
@router.message()
async def good_db_handler(message: Message) -> None:
    async with session_factory() as session:
        user = await session.get(User, message.from_user.id)
        # Даже если здесь будет исключение — сессия закроется
        await message.answer(f"Привет, {user.name}")


# ✅ ХОРОШО: UoW pattern с context manager
@router.message()
async def good_uow_handler(message: Message, uow: UnitOfWork) -> None:
    async with uow:
        user = await uow.users.get_by_telegram_id(message.from_user.id)
        if user:
            user.last_activity = datetime.utcnow()
            await uow.commit()
    # Сессия автоматически закрыта

    await message.answer(f"Привет, {user.name}")


# ✅ ХОРОШО: middleware управляет lifecycle сессии
class DbSessionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        async with self._session_factory() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()  # Commit после успеха
                return result
            except Exception:
                await session.rollback()  # Rollback при ошибке
                raise
        # Сессия автоматически закрыта через context manager


# ✅ ХОРОШО: flush() в репозитории, commit() в UoW
class GoodUserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()  # flush — отправляет SQL, но не commit'ит
        return user
```

### 6.3. N+1 запросы

```python
"""
АНТИ-ПАТТЕРН: N+1 запросы в SQLAlchemy async.

N+1 — это когда для загрузки N связанных объектов
выполняется N+1 запрос вместо 1-2.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


# ❌ ПЛОХО: N+1 в async (и lazy load не работает!)
async def bad_n_plus_one(session: AsyncSession) -> None:
    """
    В async SQLAlchemy lazy loading ЗАПРЕЩЁН.
    Обращение к relationship вызовет MissingGreenlet ошибку!
    """
    result = await session.execute(select(User))
    users = result.scalars().all()

    for user in users:
        # MissingGreenlet: greenlet_spawn has not been called!
        # Lazy load в async недоступен!
        print(user.subscriptions)  # ОШИБКА!


# ❌ ПЛОХО: "Ручной" N+1 — отдельный запрос для каждого пользователя
async def bad_manual_n_plus_one(session: AsyncSession) -> None:
    result = await session.execute(select(User))
    users = result.scalars().all()

    for user in users:
        # N дополнительных запросов!
        subs_result = await session.execute(
            select(Subscription).where(Subscription.user_id == user.id)
        )
        subs = subs_result.scalars().all()
        print(f"{user.username}: {len(subs)} subscriptions")


# ❌ ПЛОХО: joinedload для one-to-many (дублирование строк)
async def bad_joined_one_to_many(session: AsyncSession) -> None:
    """
    joinedload для one-to-many создаёт декартово произведение.
    Если у пользователя 10 подписок — строка пользователя
    продублируется 10 раз в результате JOIN.
    """
    from sqlalchemy.orm import joinedload

    result = await session.execute(
        select(User).options(joinedload(User.subscriptions))
    )
    users = result.unique().scalars().all()  # unique() обязателен!
```

```python
"""
ПРАВИЛЬНЫЕ РЕШЕНИЯ: устранение N+1 запросов.
"""
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload, subqueryload
from sqlalchemy.ext.asyncio import AsyncSession


# ✅ ХОРОШО: selectinload для one-to-many
async def good_selectin(session: AsyncSession) -> list[User]:
    """
    selectinload выполняет 2 запроса:
    1. SELECT * FROM users
    2. SELECT * FROM subscriptions WHERE user_id IN (...)

    Лучший выбор для one-to-many в async.
    """
    result = await session.execute(
        select(User).options(selectinload(User.subscriptions))
    )
    return list(result.scalars().all())


# ✅ ХОРОШО: joinedload для many-to-one (один связанный объект)
async def good_joined_many_to_one(session: AsyncSession) -> list[Subscription]:
    """
    joinedload для many-to-one — один JOIN, без дублирования.
    """
    result = await session.execute(
        select(Subscription).options(joinedload(Subscription.user))
    )
    return list(result.scalars().all())


# ✅ ХОРОШО: вложенные eager loads
async def good_nested_loading(session: AsyncSession) -> list[User]:
    """
    Загрузка нескольких уровней связей за минимум запросов.
    """
    result = await session.execute(
        select(User).options(
            selectinload(User.subscriptions),
            selectinload(User.orders).selectinload(Order.items),
        )
    )
    return list(result.scalars().all())


# ✅ ХОРОШО: явный запрос вместо relationship
async def good_explicit_query(session: AsyncSession, user_ids: list[int]) -> dict:
    """
    Иногда лучше написать явный запрос вместо relationship.
    Особенно для агрегаций.
    """
    from sqlalchemy import func

    result = await session.execute(
        select(
            Subscription.user_id,
            func.count(Subscription.id).label("count"),
        )
        .where(Subscription.user_id.in_(user_ids))
        .group_by(Subscription.user_id)
    )
    return dict(result.all())


# ✅ ХОРОШО: установить eager loading на уровне модели
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # ...

    # Eager loading по умолчанию для этого relationship
    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="user",
        lazy="selectin",  # Автоматический selectinload
    )
```

### 6.4. Другие распространённые анти-паттерны

```python
"""
Дополнительные анти-паттерны и их решения.
"""
import asyncio
from aiogram import Router, Bot
from aiogram.types import Message

router = Router()


# ❌ ПЛОХО: создание Bot внутри хендлера
@router.message()
async def bad_bot_creation(message: Message) -> None:
    bot = Bot(token="TOKEN")  # Создаётся новая сессия каждый раз!
    await bot.send_message(123, "Hello")
    # Сессия не закрывается — утечка!


# ✅ ХОРОШО: используем bot из контекста
@router.message()
async def good_bot_usage(message: Message, bot: Bot) -> None:
    await bot.send_message(123, "Hello")


# ❌ ПЛОХО: обработка ошибок "глушит" все исключения
@router.message()
async def bad_error_handling(message: Message) -> None:
    try:
        result = 1 / 0
    except Exception:
        pass  # Проглотили ошибку!
    await message.answer(str(result))  # NameError!


# ✅ ХОРОШО: логируем и обрабатываем корректно
@router.message()
async def good_error_handling(message: Message) -> None:
    try:
        result = await some_operation()
    except ValueError as e:
        logger.warning("Validation error: %s", e)
        await message.answer("Некорректные данные")
        return
    except Exception:
        logger.exception("Unexpected error")
        await message.answer("Произошла ошибка. Попробуйте позже.")
        return

    await message.answer(str(result))


# ❌ ПЛОХО: хранение состояния в глобальных переменных
user_data = {}  # Пропадёт при перезапуске!

@router.message()
async def bad_global_state(message: Message) -> None:
    user_data[message.from_user.id] = {"step": 1}


# ✅ ХОРОШО: используем FSM Storage (Redis)
@router.message()
async def good_state(message: Message, state: FSMContext) -> None:
    await state.update_data(step=1)


# ❌ ПЛОХО: неограниченный параллелизм
@router.message()
async def bad_unlimited_concurrency(message: Message) -> None:
    # 10000 одновременных запросов — убьёт API и event loop
    tasks = [
        fetch_data(url) for url in urls  # 10000 URLs
    ]
    results = await asyncio.gather(*tasks)


# ✅ ХОРОШО: ограниченный параллелизм через Semaphore
@router.message()
async def good_limited_concurrency(message: Message) -> None:
    semaphore = asyncio.Semaphore(10)  # Максимум 10 одновременных запросов

    async def fetch_limited(url: str) -> dict:
        async with semaphore:
            return await fetch_data(url)

    tasks = [fetch_limited(url) for url in urls]
    results = await asyncio.gather(*tasks)


# ❌ ПЛОХО: отсутствие graceful shutdown
async def bad_main() -> None:
    bot = Bot(token="TOKEN")
    dp = Dispatcher()
    await dp.start_polling(bot)
    # При Ctrl+C — сессии не закрываются, задачи не завершаются


# ✅ ХОРОШО: graceful shutdown
async def good_main() -> None:
    bot = Bot(token="TOKEN")
    dp = Dispatcher(storage=RedisStorage.from_url("redis://localhost"))

    try:
        await dp.start_polling(bot, drop_pending_updates=True)
    finally:
        await dp.storage.close()
        await bot.session.close()
```

### 6.5. Детектирование блокирующих вызовов

```python
"""
Инструменты для обнаружения блокировок event loop.
"""
import asyncio
import logging


def enable_slow_callback_detection(threshold: float = 0.1) -> None:
    """
    Включить предупреждения о медленных callback'ах.

    Если callback выполняется дольше threshold секунд,
    asyncio залогирует предупреждение.
    """
    # Метод 1: asyncio debug mode
    loop = asyncio.get_event_loop()
    loop.slow_callback_duration = threshold  # Порог в секундах

    # Метод 2: через переменную окружения
    # PYTHONASYNCIODEBUG=1

    logging.basicConfig(level=logging.WARNING)


# Использование в main():
if __name__ == "__main__":
    import os
    os.environ["PYTHONASYNCIODEBUG"] = "1"

    asyncio.run(main(), debug=True)
```

### 6.6. Чеклист: проверка на анти-паттерны

| Проблема | Признак | Решение |
|----------|---------|---------|
| Блокирующий HTTP | `import requests` | Заменить на `aiohttp` |
| Блокирующий sleep | `time.sleep()` | Заменить на `asyncio.sleep()` |
| Блокирующий файл I/O | `open()` без `aiofiles` | Использовать `aiofiles` |
| CPU-bound в event loop | Долгие вычисления | `run_in_executor()` или Taskiq |
| Утечка сессий БД | `session = factory()` без `close()` | `async with factory() as session:` |
| N+1 запросы | Цикл с запросами к БД | `selectinload()` / `joinedload()` |
| Глобальные переменные | `user_data = {}` | FSM Storage (Redis) |
| Неограниченный параллелизм | `gather(*10000_tasks)` | `asyncio.Semaphore` |
| Проглатывание ошибок | `except: pass` | Логирование + корректная обработка |
| Отсутствие shutdown | Нет `finally` блока | `try/finally` с закрытием ресурсов |

**Источники:**
- [Python asyncio debug mode](https://docs.python.org/3/library/asyncio-dev.html)
- [Blocking calls in asyncio](https://superfastpython.com/asyncio-blocking-tasks/)
- [SQLAlchemy Eager Loading стратегии](https://docs.sqlalchemy.org/en/21/orm/loading_relationships.html)
- [N+1 проблема и её решения](https://hevalhazalkurt.com/blog/how-to-defeat-the-n1-problem-with-joinedload-selectinload-and-subqueryload/)
- [Python async/sync blocking detection](https://dzone.com/articles/python-asyncsync-advanced-blocking-detection-and-b)

---

## Приложение A: Рекомендуемая структура проекта

```
bot/
├── src/
│   ├── __init__.py
│   ├── __main__.py                    # Точка входа (python -m src)
│   ├── config.py                      # Pydantic Settings (из .env)
│   │
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── factory.py                 # Создание Bot + Dispatcher
│   │   ├── handlers/                  # Хендлеры (по роутерам)
│   │   │   ├── __init__.py
│   │   │   ├── start.py
│   │   │   ├── catalog.py
│   │   │   ├── orders.py
│   │   │   ├── profile.py
│   │   │   └── admin/
│   │   │       ├── __init__.py
│   │   │       ├── broadcast.py
│   │   │       └── stats.py
│   │   ├── filters/                   # Кастомные фильтры
│   │   │   ├── __init__.py
│   │   │   ├── admin.py
│   │   │   └── subscription.py
│   │   ├── keyboards/                 # Клавиатуры
│   │   │   ├── __init__.py
│   │   │   ├── inline.py
│   │   │   └── reply.py
│   │   ├── middlewares/               # Middleware
│   │   │   ├── __init__.py
│   │   │   ├── db.py
│   │   │   ├── throttling.py
│   │   │   └── logging.py
│   │   └── states/                    # FSM-состояния
│   │       ├── __init__.py
│   │       └── feedback.py
│   │
│   ├── services/                      # Бизнес-логика
│   │   ├── __init__.py
│   │   ├── user_service.py
│   │   ├── order_service.py
│   │   └── notification_service.py
│   │
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── engine.py
│   │   │   ├── base.py
│   │   │   ├── models/
│   │   │   ├── repositories/
│   │   │   └── uow.py
│   │   ├── cache/
│   │   │   ├── __init__.py
│   │   │   ├── redis_cache.py
│   │   │   └── redis_lock.py
│   │   └── http/
│   │       ├── __init__.py
│   │       ├── base_client.py
│   │       ├── retry_client.py
│   │       ├── circuit_breaker.py
│   │       └── payment_client.py
│   │
│   ├── di/                            # Dependency Injection (Dishka)
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── cache.py
│   │   └── http_clients.py
│   │
│   └── worker/                        # Taskiq
│       ├── __init__.py
│       ├── broker.py
│       ├── scheduler.py
│       ├── tasks.py
│       └── periodic_tasks.py
│
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── alembic.ini
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── CLAUDE.md
```

---

## Приложение B: Конфигурация через Pydantic Settings

```python
"""
src/config.py

Типизированная конфигурация через Pydantic Settings.
Автоматическая загрузка из .env файла с валидацией.
"""
from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotConfig(BaseSettings):
    """Настройки Telegram бота."""
    model_config = SettingsConfigDict(
        env_prefix="BOT_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    token: SecretStr
    mode: str = "polling"  # "polling" или "webhook"
    webhook_url: str = ""
    webhook_path: str = "/webhook"
    webhook_secret: str = ""
    admin_ids: list[int] = []

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: str | list[int]) -> list[int]:
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v


class DatabaseConfig(BaseSettings):
    """Настройки базы данных."""
    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=".env",
    )

    host: str = "localhost"
    port: int = 5432
    name: str = "botdb"
    user: str = "postgres"
    password: SecretStr = SecretStr("postgres")
    echo: bool = False

    @property
    def url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.user}:"
            f"{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.name}"
        )


class RedisConfig(BaseSettings):
    """Настройки Redis."""
    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        env_file=".env",
    )

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: SecretStr | None = None

    @property
    def url(self) -> str:
        auth = ""
        if self.password:
            auth = f":{self.password.get_secret_value()}@"
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"

    @property
    def fsm_url(self) -> str:
        """Отдельная БД для FSM."""
        auth = ""
        if self.password:
            auth = f":{self.password.get_secret_value()}@"
        return f"redis://{auth}{self.host}:{self.port}/{self.db + 1}"


class AppConfig(BaseSettings):
    """Главная конфигурация приложения."""
    bot: BotConfig = BotConfig()
    db: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()


def load_config() -> AppConfig:
    """Загрузить конфигурацию."""
    return AppConfig()
```

---

## Приложение C: Graceful Shutdown

```python
"""
src/__main__.py

Точка входа с graceful shutdown.
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from src.config import load_config
from src.infrastructure.database.engine import create_engine, create_session_factory
from src.bot.middlewares.db import DbSessionMiddleware
from src.bot.middlewares.throttling import ThrottlingMiddleware

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


async def main() -> None:
    config = load_config()

    # ---------- Инфраструктура ----------
    engine = create_engine(config.db.url, echo=config.db.echo)
    session_factory = create_session_factory(engine)

    redis = Redis.from_url(config.redis.url)
    fsm_storage = RedisStorage.from_url(config.redis.fsm_url)

    # ---------- Bot & Dispatcher ----------
    bot = Bot(
        token=config.bot.token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=fsm_storage)

    # ---------- Middleware ----------
    dp.update.outer_middleware(DbSessionMiddleware(session_factory))
    dp.update.outer_middleware(ThrottlingMiddleware(redis=redis, rate_limit=0.5))

    # ---------- Routers ----------
    from src.bot.handlers import start, catalog, orders, profile
    dp.include_routers(
        start.router,
        catalog.router,
        orders.router,
        profile.router,
    )

    # ---------- Lifecycle ----------
    try:
        logger.info("Запуск бота в режиме %s", config.bot.mode)

        if config.bot.mode == "webhook":
            from aiohttp import web
            from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

            await bot.set_webhook(
                url=f"{config.bot.webhook_url}{config.bot.webhook_path}",
                secret_token=config.bot.webhook_secret,
                drop_pending_updates=True,
            )

            app = web.Application()
            handler = SimpleRequestHandler(
                dispatcher=dp, bot=bot,
                secret_token=config.bot.webhook_secret,
            )
            handler.register(app, path=config.bot.webhook_path)
            setup_application(app, dp, bot=bot)

            web.run_app(app, host="127.0.0.1", port=8080)
        else:
            await dp.start_polling(bot, drop_pending_updates=True)

    finally:
        # Graceful shutdown — закрываем все ресурсы
        logger.info("Остановка бота...")
        await fsm_storage.close()
        await redis.close()
        await engine.dispose()
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    asyncio.run(main())
```

---

## Приложение D: Docker-конфигурация

```dockerfile
# Dockerfile
FROM python:3.14-slim AS base

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Установка uv для управления зависимостями
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Копируем файлы зависимостей
COPY pyproject.toml uv.lock ./

# Установка зависимостей
RUN uv sync --frozen --no-dev

# Копируем исходный код
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .

# Запуск
CMD ["uv", "run", "python", "-m", "src"]
```

```yaml
# docker-compose.yml (для bot-сервиса)
services:
  bot:
    build: ./bot
    env_file: ./bot/.env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "0.5"

  bot-worker:
    build: ./bot
    command: uv run taskiq worker src.worker.broker:broker
    env_file: ./bot/.env
    depends_on:
      - bot
      - redis
    restart: unless-stopped

  bot-scheduler:
    build: ./bot
    command: uv run taskiq scheduler src.worker.scheduler:scheduler
    env_file: ./bot/.env
    depends_on:
      - bot
      - redis
    restart: unless-stopped

  postgres:
    image: postgres:18
    environment:
      POSTGRES_DB: botdb
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:8-alpine
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

---

## Приложение E: Зависимости (pyproject.toml)

```toml
[project]
name = "loyalty-bot"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = [
    # Telegram Bot Framework
    "aiogram>=3.26.0",

    # Database
    "sqlalchemy[asyncio]>=2.1.0",
    "asyncpg>=0.30.0",
    "alembic>=1.18.0",

    # Redis
    "redis[hiredis]>=5.2.0",

    # Task Queue
    "taskiq>=0.11.0",
    "taskiq-aiogram>=0.4.0",
    "taskiq-redis>=1.0.0",

    # DI
    "dishka>=1.4.0",

    # HTTP Client
    "aiohttp>=3.11.0",
    "aiohttp-retry>=2.9.0",

    # Configuration
    "pydantic-settings>=2.7.0",

    # Utilities
    "aiofiles>=24.1.0",
]

[project.optional-dependencies]
dev = [
    "ruff>=0.9.0",
    "mypy>=1.14.0",
    "pytest>=8.3.0",
    "pytest-asyncio>=0.25.0",
    "pytest-cov>=6.0.0",
]
```
