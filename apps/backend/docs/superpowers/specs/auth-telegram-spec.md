# Technical Specification: Telegram Mini App Authorization

**Проект:** Loyalty-система (Telegram Mini App)
**Дата:** 2026-03-20
**Версия:** 1.0
**Статус:** Draft
**Основание:** PDR "Backend Authorization" v1.0
**Область:** `src/modules/identity/` + `src/modules/user/` + `src/bot/`

---

## 1. Контекст и анализ текущей архитектуры

### 1.1. Что уже есть

Проект — **модульный монолит** на FastAPI + SQLAlchemy 2.x (async) + PostgreSQL + Redis, организованный по принципам DDD / Hexagonal / CQRS.

**Identity модуль** (`src/modules/identity/`) уже реализует:

| Компонент              | Реализация                                                                              | Файл                                       |
| ---------------------- | --------------------------------------------------------------------------------------- | ------------------------------------------ |
| Identity (агрегат)     | `IdentityType.LOCAL \| OIDC`, `AccountType.CUSTOMER \| STAFF`                           | `domain/entities.py`                       |
| Session (сущность)     | Refresh token rotation, reuse detection, NIST role activation                           | `domain/entities.py`                       |
| JWT Access Token       | HS256, `sub` + `sid` + `jti`, TTL 15 мин                                                | `infrastructure/security/jwt.py`           |
| Refresh Token          | Opaque 32-byte, SHA-256 hash в БД, TTL 30 дней                                          | `infrastructure/security/jwt.py`           |
| Login (email/password) | `LoginHandler` → сессия + токены                                                        | `application/commands/login.py`            |
| Refresh                | `RefreshTokenHandler` → ротация + reuse detection через Redis                           | `application/commands/refresh_token.py`    |
| Logout / Logout All    | Revoke session(s) + invalidate permission cache                                         | `application/commands/logout*.py`          |
| RBAC                   | Roles → Permissions, cache-aside resolver (Redis + CTE), `RequirePermission` dependency | `infrastructure/security/authorization.py` |
| Auth dependency        | `get_auth_context()` → `AuthContext(identity_id, session_id)`                           | `presentation/dependencies.py`             |
| Linked Accounts        | `LinkedAccountModel` — provider + provider_sub_id                                       | `infrastructure/models.py`                 |
| OIDC flow              | `login_oidc.py` — расширяемый                                                           | `application/commands/login_oidc.py`       |

**User модуль** (`src/modules/user/`) уже реализует:

| Компонент        | Реализация                                                                               |
| ---------------- | ---------------------------------------------------------------------------------------- |
| CustomerModel    | `id` (FK→identities), `first_name`, `last_name`, `phone`, `referral_code`, `referred_by` |
| StaffMemberModel | `id` (FK→identities), `first_name`, `last_name`, `position`, `department`                |

**Bot модуль** (`src/bot/`) уже реализует:

| Компонент     | Реализация                                                            |
| ------------- | --------------------------------------------------------------------- |
| aiogram 3.26+ | `factory.py` — Bot + Dispatcher                                       |
| Handlers      | `/start`, `/help`, `/cancel`, error handler                           |
| Middleware    | `UserIdentifyMiddleware`, `ThrottlingMiddleware`, `LoggingMiddleware` |
| Config        | `BOT_TOKEN`, `BOT_ADMIN_IDS`, webhook support                         |

### 1.2. Что нужно добавить

| Задача                         | Описание                                                            |
| ------------------------------ | ------------------------------------------------------------------- |
| **TELEGRAM identity type**     | Новое значение в `IdentityType` enum                                |
| **TelegramCredentials**        | Новая сущность: `telegram_id` (BigInt), профильные поля из initData |
| **initData валидация**         | HMAC-SHA256 проверка с `BOT_TOKEN` + freshness check                |
| **POST /api/v1/auth/telegram** | Новый endpoint: initData → JWT пара                                 |
| **Auto-provisioning**          | Создание Identity + Customer при первом входе                       |
| **Profile sync**               | Обновление профильных данных при каждом входе                       |
| **Referral через start_param** | Привязка `referred_by` при первом входе                             |
| **Настройка TTL**              | `REFRESH_TOKEN_EXPIRE_DAYS`: 30 → 7 (для Telegram сессий)           |
| **Миграция**                   | Таблица `telegram_credentials` + расширение `customers`             |

---

## 2. Источник доверия: Telegram initData

### 2.1. Структура данных

При открытии Mini App клиент Telegram формирует URL-encoded query string (`initData`) и подписывает его HMAC-SHA256.

**WebAppInitData** (из Telegram Bot API):

| Поле             | Тип               | Обязательное | Описание                                                        |
| ---------------- | ----------------- | :----------: | --------------------------------------------------------------- |
| `user`           | WebAppUser (JSON) |     Да\*     | Данные текущего пользователя                                    |
| `auth_date`      | Integer           |      Да      | Unix timestamp момента подписи                                  |
| `hash`           | String            |      Да      | HMAC-SHA256 подпись                                             |
| `signature`      | String            |    Да\*\*    | Ed25519 подпись (для third-party)                               |
| `query_id`       | String            |     Нет      | ID сессии для `answerWebAppQuery`                               |
| `chat_type`      | String            |     Нет      | `"sender"`, `"private"`, `"group"`, `"supergroup"`, `"channel"` |
| `chat_instance`  | String            |     Нет      | Глобальный ID чата                                              |
| `start_param`    | String            |     Нет      | Значение из deep link (реферальный код)                         |
| `can_send_after` | Integer           |     Нет      | Секунды до разрешения `answerWebAppQuery`                       |

\* `user` отсутствует, если Mini App запущен из keyboard button или inline mode.
\*\* `signature` добавлен для third-party валидации без `bot_token`.

**WebAppUser** (вложенный объект):

| Поле                 | Тип     | Обязательное | Описание                             |
| -------------------- | ------- | :----------: | ------------------------------------ |
| `id`                 | Integer |      Да      | Уникальный Telegram ID (до 52 бит)   |
| `first_name`         | String  |      Да      | Имя                                  |
| `last_name`          | String  |     Нет      | Фамилия                              |
| `username`           | String  |     Нет      | Username без @                       |
| `language_code`      | String  |     Нет      | IETF language tag (`ru`, `en`, `uz`) |
| `is_premium`         | Boolean |     Нет      | Telegram Premium подписка            |
| `allows_write_to_pm` | Boolean |     Нет      | Разрешил ли бот писать в ЛС          |
| `photo_url`          | String  |     Нет      | URL аватарки (.jpeg/.svg)            |

**Что НЕ содержит initData:**

- Номер телефона — только через `requestContact()` (Bot API 6.9+)
- Email — недоступен через Telegram API
- Геолокация — только через `LocationManager`

### 2.2. Алгоритм HMAC-SHA256 валидации

Telegram использует двухступенчатый HMAC для подписи initData:

```
┌──────────────────────────────────────────────────────────┐
│ 1. Парсинг initData (URL query string → key=value пары) │
│                                                          │
│ 2. Извлечь поле 'hash', убрать его из набора             │
│                                                          │
│ 3. Оставшиеся пары отсортировать по ключу (ASCII)        │
│    → Склеить через '\n' (0x0A)                           │
│    → Это data_check_string                               │
│                                                          │
│ 4. secret_key = HMAC-SHA256(key="WebAppData", msg=token) │
│    ⚠ "WebAppData" — КЛЮЧ, bot_token — СООБЩЕНИЕ!        │
│                                                          │
│ 5. computed = HMAC-SHA256(key=secret_key,                │
│                           msg=data_check_string)         │
│                                                          │
│ 6. hex(computed) == hash → подпись верна                  │
│                                                          │
│ 7. now() - auth_date ≤ INIT_DATA_MAX_AGE → данные свежие │
└──────────────────────────────────────────────────────────┘
```

**Критические детали:**

- Константа `"WebAppData"` используется как **ключ** первого HMAC, а `bot_token` — как **сообщение** (не наоборот!)
- Поле `user` в `data_check_string` — это JSON-строка целиком, как `user={"id":123,...}`
- Сравнение хешей — через `hmac.compare_digest()` (constant-time)

### 2.3. aiogram утилиты

aiogram предоставляет готовые функции в `aiogram.utils.web_app`:

| Функция                                                          | Описание                            |
| ---------------------------------------------------------------- | ----------------------------------- |
| `check_webapp_signature(token, init_data) → bool`                | Только проверка подписи             |
| `parse_webapp_init_data(init_data) → WebAppInitData`             | Парсинг без валидации (unsafe)      |
| `safe_parse_webapp_init_data(token, init_data) → WebAppInitData` | Валидация + парсинг (рекомендуется) |

**Решение:** Использовать `safe_parse_webapp_init_data` как основу, но добавить:

- Проверку `auth_date` freshness (aiogram не делает это по умолчанию)
- Проверку наличия `user` объекта
- Маппинг в доменные объекты

---

## 3. Доменный слой (Domain Layer)

### 3.1. Value Objects

**Файл:** `src/modules/identity/domain/value_objects.py`

```python
class IdentityType(enum.StrEnum):
    LOCAL = "LOCAL"
    OIDC = "OIDC"
    TELEGRAM = "TELEGRAM"  # ← НОВОЕ
```

**Новый value object:**

```python
@dataclass(frozen=True, slots=True)
class TelegramUserData:
    """Immutable snapshot данных пользователя из initData.

    Используется как входной параметр для команд.
    Не хранится напрямую — маппится в TelegramCredentials.
    """
    telegram_id: int          # user.id (до 52 бит)
    first_name: str           # user.first_name
    last_name: str | None     # user.last_name
    username: str | None      # user.username
    language_code: str | None  # user.language_code
    is_premium: bool          # user.is_premium (default False)
    photo_url: str | None     # user.photo_url
    allows_write_to_pm: bool  # user.allows_write_to_pm (default False)
```

### 3.2. Entities

**Файл:** `src/modules/identity/domain/entities.py`

**Новая сущность `TelegramCredentials`:**

```python
@dataclass
class TelegramCredentials:
    """Telegram-specific credentials linked to an Identity.

    Аналог LocalCredentials, но вместо email/password хранит
    telegram_id и профильные данные из WebAppUser.

    Отношение к Identity: 1:1 (Shared PK pattern, как LocalCredentials).
    """
    identity_id: uuid.UUID
    telegram_id: int            # Telegram user ID (уникальный, индексированный)
    first_name: str
    last_name: str | None
    username: str | None
    language_code: str | None
    is_premium: bool
    photo_url: str | None
    allows_write_to_pm: bool
    created_at: datetime
    updated_at: datetime

    def update_profile(self, data: TelegramUserData) -> bool:
        """Обновить профильные данные из нового initData.

        Returns:
            True если хотя бы одно поле изменилось.
        """
        changed = False
        for field in ("first_name", "last_name", "username",
                      "language_code", "is_premium", "photo_url",
                      "allows_write_to_pm"):
            new_val = getattr(data, field)
            if getattr(self, field) != new_val:
                setattr(self, field, new_val)
                changed = True
        if changed:
            self.updated_at = datetime.now(UTC)
        return changed
```

**Расширение фабричного метода `Identity.register()`:**

```python
@classmethod
def register_telegram(cls) -> Identity:
    """Create a new active customer identity authenticated via Telegram."""
    return cls.register(IdentityType.TELEGRAM, AccountType.CUSTOMER)
```

### 3.3. Domain Events

**Файл:** `src/modules/identity/domain/events.py`

```python
@dataclass(frozen=True)
class TelegramIdentityCreatedEvent:
    """Emitted when a new Identity is created via Telegram Mini App."""
    identity_id: uuid.UUID
    telegram_id: int
    start_param: str | None      # Реферальный код из deep link
    aggregate_id: str

@dataclass(frozen=True)
class TelegramProfileUpdatedEvent:
    """Emitted when Telegram profile data changes on login."""
    identity_id: uuid.UUID
    telegram_id: int
    changed_fields: tuple[str, ...]
    aggregate_id: str
```

### 3.4. Domain Exceptions

**Файл:** `src/modules/identity/domain/exceptions.py`

```python
class InvalidInitDataError(DomainException):
    """initData signature verification failed."""
    def __init__(self) -> None:
        super().__init__("Invalid or tampered Telegram initData")

class InitDataExpiredError(DomainException):
    """initData auth_date is too old."""
    def __init__(self, age_seconds: int, max_seconds: int) -> None:
        super().__init__(
            f"initData expired: age {age_seconds}s > max {max_seconds}s"
        )

class InitDataMissingUserError(DomainException):
    """initData does not contain user object."""
    def __init__(self) -> None:
        super().__init__("initData does not contain user data")
```

### 3.5. Repository Interface

**Файл:** `src/modules/identity/domain/interfaces.py`

```python
class ITelegramCredentialsRepository(ABC):
    """Repository contract for TelegramCredentials persistence."""

    @abstractmethod
    async def add(self, credentials: TelegramCredentials) -> TelegramCredentials:
        """Persist new Telegram credentials."""

    @abstractmethod
    async def get_by_telegram_id(self, telegram_id: int) -> tuple[Identity, TelegramCredentials] | None:
        """Find Identity + TelegramCredentials by Telegram user ID.

        JOIN identities ON telegram_credentials.identity_id = identities.id
        """

    @abstractmethod
    async def update(self, credentials: TelegramCredentials) -> None:
        """Update Telegram credentials (profile sync)."""
```

### 3.6. Service Interface

**Файл:** `src/shared/interfaces/security.py`

```python
class ITelegramInitDataValidator(Protocol):
    """Contract for Telegram initData validation."""

    def validate_and_parse(self, init_data_raw: str) -> TelegramUserData:
        """Validate HMAC-SHA256 signature, check freshness, parse user.

        Args:
            init_data_raw: Raw URL-encoded initData string from client.

        Returns:
            Parsed TelegramUserData value object.

        Raises:
            InvalidInitDataError: Signature mismatch.
            InitDataExpiredError: auth_date too old.
            InitDataMissingUserError: No user object in initData.
        """
        ...
```

---

## 4. Infrastructure Layer

### 4.1. ORM Model

**Файл:** `src/modules/identity/infrastructure/models.py`

```python
class TelegramCredentialsModel(Base):
    """ORM model for the ``telegram_credentials`` table."""

    __tablename__ = "telegram_credentials"
    __table_args__ = (
        Index("ix_telegram_credentials_telegram_id", "telegram_id", unique=True),
        {"comment": "Telegram auth credentials (Shared PK 1:1 with identities)"},
    )

    identity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="CASCADE"),
        primary_key=True,
        comment="PK + FK → identities (Shared PK 1:1)",
    )
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
        comment="Telegram user ID (up to 52 significant bits)",
    )
    first_name: Mapped[str] = mapped_column(
        String(100), server_default="", nullable=False
    )
    last_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    username: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="Telegram username without @"
    )
    language_code: Mapped[str | None] = mapped_column(
        String(10), nullable=True,
        comment="IETF language tag from Telegram"
    )
    is_premium: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False,
        comment="Telegram Premium subscription status"
    )
    photo_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True,
        comment="Telegram profile photo URL"
    )
    allows_write_to_pm: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False,
        comment="Whether user allows bot to send messages"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False
    )
```

**Расширение `IdentityModel`:**

```python
# В IdentityModel.__init__ добавить relationship:
telegram_credentials: Mapped[TelegramCredentialsModel | None] = relationship(
    back_populates="identity",
    uselist=False,
    cascade="all, delete-orphan",
)
```

**Обновление `IdentityType` Enum:**

Значение `TELEGRAM` добавляется в `IdentityType`. PostgreSQL enum — `native_enum=False` (хранится как VARCHAR), поэтому миграция данных не требуется.

### 4.2. initData Validator

**Файл:** `src/infrastructure/security/telegram.py`

```python
"""Telegram initData HMAC-SHA256 validator.

Uses aiogram's safe_parse_webapp_init_data as the cryptographic core,
then applies additional business rules (freshness, user presence).
"""

import time

from aiogram.utils.web_app import safe_parse_webapp_init_data

from src.bootstrap.config import settings
from src.modules.identity.domain.exceptions import (
    InitDataExpiredError,
    InitDataMissingUserError,
    InvalidInitDataError,
)
from src.modules.identity.domain.value_objects import TelegramUserData


class TelegramInitDataValidator:
    """Validates and parses Telegram Mini App initData."""

    # Maximum age of initData before rejection (seconds)
    INIT_DATA_MAX_AGE: int = 300  # 5 minutes

    def __init__(self, bot_token: str, max_age: int = 300) -> None:
        self._bot_token = bot_token
        self._max_age = max_age

    def validate_and_parse(self, init_data_raw: str) -> tuple[TelegramUserData, str | None]:
        """Validate signature, check freshness, extract user data.

        Args:
            init_data_raw: Raw URL-encoded initData string.

        Returns:
            Tuple of (TelegramUserData, start_param | None).

        Raises:
            InvalidInitDataError: HMAC signature mismatch.
            InitDataExpiredError: auth_date older than max_age.
            InitDataMissingUserError: No user in initData.
        """
        # Step 1: Validate HMAC-SHA256 signature via aiogram
        try:
            parsed = safe_parse_webapp_init_data(
                token=self._bot_token,
                init_data=init_data_raw,
            )
        except ValueError:
            raise InvalidInitDataError()

        # Step 2: Check freshness (aiogram does NOT do this)
        if parsed.auth_date is not None:
            age = int(time.time()) - int(parsed.auth_date.timestamp())
            if age > self._max_age:
                raise InitDataExpiredError(age_seconds=age, max_seconds=self._max_age)
        else:
            raise InvalidInitDataError()

        # Step 3: Ensure user object exists
        if parsed.user is None:
            raise InitDataMissingUserError()

        user = parsed.user
        telegram_user_data = TelegramUserData(
            telegram_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            language_code=user.language_code,
            is_premium=user.is_premium or False,
            photo_url=user.photo_url,
            allows_write_to_pm=user.allows_write_to_pm or False,
        )

        return telegram_user_data, parsed.start_param
```

### 4.3. Repository Implementation

**Файл:** `src/modules/identity/infrastructure/repositories/telegram_credentials_repo.py`

```python
class TelegramCredentialsRepository(ITelegramCredentialsRepository):
    """SQLAlchemy implementation of ITelegramCredentialsRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, credentials: TelegramCredentials) -> TelegramCredentials:
        model = TelegramCredentialsModel(
            identity_id=credentials.identity_id,
            telegram_id=credentials.telegram_id,
            first_name=credentials.first_name,
            last_name=credentials.last_name,
            username=credentials.username,
            language_code=credentials.language_code,
            is_premium=credentials.is_premium,
            photo_url=credentials.photo_url,
            allows_write_to_pm=credentials.allows_write_to_pm,
        )
        self._session.add(model)
        await self._session.flush()
        return credentials

    async def get_by_telegram_id(
        self, telegram_id: int
    ) -> tuple[Identity, TelegramCredentials] | None:
        stmt = (
            select(IdentityModel, TelegramCredentialsModel)
            .join(TelegramCredentialsModel,
                  IdentityModel.id == TelegramCredentialsModel.identity_id)
            .where(TelegramCredentialsModel.telegram_id == telegram_id)
        )
        row = (await self._session.execute(stmt)).one_or_none()
        if row is None:
            return None
        identity_model, creds_model = row
        return (
            self._map_identity(identity_model),
            self._map_credentials(creds_model),
        )

    async def update(self, credentials: TelegramCredentials) -> None:
        stmt = (
            sa_update(TelegramCredentialsModel)
            .where(TelegramCredentialsModel.identity_id == credentials.identity_id)
            .values(
                first_name=credentials.first_name,
                last_name=credentials.last_name,
                username=credentials.username,
                language_code=credentials.language_code,
                is_premium=credentials.is_premium,
                photo_url=credentials.photo_url,
                allows_write_to_pm=credentials.allows_write_to_pm,
            )
        )
        await self._session.execute(stmt)

    # ... mapper methods (аналогично существующим в IdentityRepository)
```

---

## 5. Application Layer (Command)

### 5.1. LoginTelegramCommand

**Файл:** `src/modules/identity/application/commands/login_telegram.py`

```python
@dataclass(frozen=True)
class LoginTelegramCommand:
    """Command to authenticate via Telegram Mini App initData.

    Attributes:
        init_data_raw: Raw URL-encoded initData string from Authorization header.
        ip_address: Client IP for session audit trail.
        user_agent: Client User-Agent header.
    """
    init_data_raw: str
    ip_address: str
    user_agent: str


@dataclass(frozen=True)
class LoginTelegramResult:
    """Result of successful Telegram authentication.

    Attributes:
        access_token: Short-lived JWT (15 min).
        refresh_token: Opaque refresh token for rotation.
        identity_id: The authenticated identity UUID.
        is_new_user: True if this was the first login (identity just created).
    """
    access_token: str
    refresh_token: str
    identity_id: uuid.UUID
    is_new_user: bool
```

### 5.2. LoginTelegramHandler

```python
class LoginTelegramHandler:
    """Handles Telegram Mini App authentication.

    Flow:
    1. Validate initData (HMAC-SHA256 + freshness)
    2. Lookup by telegram_id
    3. If new → create Identity (TELEGRAM) + TelegramCredentials + Customer
    4. If existing → sync profile data
    5. Create session + token pair
    """

    def __init__(
        self,
        telegram_validator: ITelegramInitDataValidator,
        telegram_creds_repo: ITelegramCredentialsRepository,
        identity_repo: IIdentityRepository,
        customer_repo: ICustomerRepository,
        session_repo: ISessionRepository,
        role_repo: IRoleRepository,
        uow: IUnitOfWork,
        token_provider: ITokenProvider,
        logger: ILogger,
        max_sessions: int = 5,
        refresh_token_days: int = 7,  # ← PDR: 7 дней для Telegram
    ) -> None:
        self._validator = telegram_validator
        self._telegram_creds_repo = telegram_creds_repo
        self._identity_repo = identity_repo
        self._customer_repo = customer_repo
        self._session_repo = session_repo
        self._role_repo = role_repo
        self._uow = uow
        self._token_provider = token_provider
        self._logger = logger.bind(handler="LoginTelegramHandler")
        self._max_sessions = max_sessions
        self._refresh_token_days = refresh_token_days

    async def handle(self, command: LoginTelegramCommand) -> LoginTelegramResult:
        # ── Step 1: Validate initData ──────────────────────────────────
        telegram_user, start_param = self._validator.validate_and_parse(
            command.init_data_raw
        )

        async with self._uow:
            # ── Step 2: Lookup existing identity ───────────────────────
            result = await self._telegram_creds_repo.get_by_telegram_id(
                telegram_user.telegram_id
            )

            is_new_user = result is None

            if is_new_user:
                # ── Step 3a: Auto-provision new user ───────────────────
                identity, credentials = await self._provision_new_user(
                    telegram_user, start_param
                )
            else:
                # ── Step 3b: Sync profile for existing user ────────────
                identity, credentials = result
                identity.ensure_active()
                await self._sync_profile(identity, credentials, telegram_user)

            # ── Step 4: Enforce session limit ──────────────────────────
            active_count = await self._session_repo.count_active(identity.id)
            if active_count >= self._max_sessions:
                # For Telegram: evict oldest session instead of rejecting
                # (UX: user just opened the app, shouldn't see an error)
                await self._evict_oldest_session(identity.id)

            # ── Step 5: Create session + tokens ────────────────────────
            raw_refresh, _ = self._token_provider.create_refresh_token()
            role_ids = await self._role_repo.get_identity_role_ids(identity.id)

            session = Session.create(
                identity_id=identity.id,
                refresh_token=raw_refresh,
                ip_address=command.ip_address,
                user_agent=command.user_agent,
                role_ids=role_ids,
                expires_days=self._refresh_token_days,
            )
            await self._session_repo.add(session)
            await self._session_repo.add_session_roles(session.id, role_ids)

            access_token = self._token_provider.create_access_token(
                payload_data={
                    "sub": str(identity.id),
                    "sid": str(session.id),
                },
            )

            await self._uow.commit()

        self._logger.info(
            "telegram.login.success",
            identity_id=str(identity.id),
            telegram_id=telegram_user.telegram_id,
            is_new_user=is_new_user,
            ip=command.ip_address,
        )

        return LoginTelegramResult(
            access_token=access_token,
            refresh_token=raw_refresh,
            identity_id=identity.id,
            is_new_user=is_new_user,
        )

    async def _provision_new_user(
        self,
        data: TelegramUserData,
        start_param: str | None,
    ) -> tuple[Identity, TelegramCredentials]:
        """Create Identity + TelegramCredentials + Customer atomically."""
        # Create Identity
        identity = Identity.register_telegram()
        identity = await self._identity_repo.add(identity)

        # Create TelegramCredentials
        now = datetime.now(UTC)
        credentials = TelegramCredentials(
            identity_id=identity.id,
            telegram_id=data.telegram_id,
            first_name=data.first_name,
            last_name=data.last_name,
            username=data.username,
            language_code=data.language_code,
            is_premium=data.is_premium,
            photo_url=data.photo_url,
            allows_write_to_pm=data.allows_write_to_pm,
            created_at=now,
            updated_at=now,
        )
        await self._telegram_creds_repo.add(credentials)

        # Create Customer profile
        customer = Customer(
            id=identity.id,
            first_name=data.first_name,
            last_name=data.last_name or "",
            phone=None,
            referral_code=self._generate_referral_code(),
            referred_by=await self._resolve_referrer(start_param),
        )
        await self._customer_repo.add(customer)

        # Assign default customer role
        default_role = await self._role_repo.get_by_name("customer")
        if default_role:
            await self._role_repo.assign_to_identity(identity.id, default_role.id)

        # Domain event
        identity.add_domain_event(
            TelegramIdentityCreatedEvent(
                identity_id=identity.id,
                telegram_id=data.telegram_id,
                start_param=start_param,
                aggregate_id=str(identity.id),
            )
        )

        self._logger.info(
            "telegram.user.provisioned",
            identity_id=str(identity.id),
            telegram_id=data.telegram_id,
            referred_by=start_param,
        )

        return identity, credentials

    async def _sync_profile(
        self,
        identity: Identity,
        credentials: TelegramCredentials,
        data: TelegramUserData,
    ) -> None:
        """Update profile if Telegram data changed since last login."""
        changed = credentials.update_profile(data)
        if changed:
            await self._telegram_creds_repo.update(credentials)
            # Optionally sync Customer.first_name/last_name too
            self._logger.info(
                "telegram.profile.synced",
                identity_id=str(identity.id),
                telegram_id=data.telegram_id,
            )

    async def _evict_oldest_session(self, identity_id: uuid.UUID) -> None:
        """Revoke the oldest active session to make room for a new one."""
        # Implementation: SELECT oldest active session, revoke it
        # This is a Telegram-specific UX decision
        pass

    def _generate_referral_code(self) -> str:
        """Generate a unique 8-char referral code."""
        return secrets.token_urlsafe(6)  # ~8 chars

    async def _resolve_referrer(self, start_param: str | None) -> uuid.UUID | None:
        """Resolve start_param to a customer ID (referral tracking)."""
        if not start_param:
            return None
        # Lookup customer by referral_code
        customer = await self._customer_repo.get_by_referral_code(start_param)
        return customer.id if customer else None
```

---

## 6. Presentation Layer

### 6.1. Schemas

**Файл:** `src/modules/identity/presentation/schemas.py` (добавить)

```python
class TelegramTokenResponse(CamelModel):
    """Response for Telegram authentication.

    Extends TokenResponse with is_new_user flag for frontend
    to decide whether to show onboarding.
    """
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    is_new_user: bool
```

### 6.2. Router

**Файл:** `src/modules/identity/presentation/router_auth.py` (добавить endpoint)

```python
@auth_router.post(
    "/telegram",
    response_model=TelegramTokenResponse,
    summary="Authenticate via Telegram Mini App",
    description=(
        "Validates Telegram initData (HMAC-SHA256), creates or updates "
        "the user profile, and returns a JWT token pair."
    ),
    responses={
        401: {"description": "Invalid or expired initData"},
    },
)
async def login_telegram(
    request: Request,
    handler: FromDishka[LoginTelegramHandler],
) -> TelegramTokenResponse:
    """Authenticate using Telegram Mini App initData.

    The initData must be sent in the Authorization header:
        Authorization: tma <raw initData string>

    Args:
        request: FastAPI request (for extracting initData from header).
        handler: The login-telegram command handler.

    Returns:
        Access/refresh token pair with is_new_user flag.
    """
    # Extract initData from Authorization header
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("tma "):
        raise UnauthorizedError(
            message="Missing or invalid Authorization header. Expected: tma <initData>",
            error_code="INVALID_AUTH_SCHEME",
        )
    init_data_raw = auth_header[4:]  # Strip "tma " prefix

    command = LoginTelegramCommand(
        init_data_raw=init_data_raw,
        ip_address=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent", ""),
    )
    result = await handler.handle(command)

    return TelegramTokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        is_new_user=result.is_new_user,
    )
```

### 6.3. HTTP Error Mapping

**Файл:** `src/api/exceptions/handlers.py` (добавить маппинг)

```python
# Domain exceptions → HTTP status codes
_EXCEPTION_MAP = {
    # ... existing mappings ...
    InvalidInitDataError: 401,
    InitDataExpiredError: 401,
    InitDataMissingUserError: 401,
}
```

---

## 7. Configuration

### 7.1. Settings

**Файл:** `src/bootstrap/config.py` (добавить)

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # -- Telegram Mini App Auth -----------------------------------------
    TELEGRAM_INIT_DATA_MAX_AGE: int = 300  # 5 minutes (seconds)
    TELEGRAM_REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # PDR: 7 days for Telegram sessions
```

### 7.2. DI Provider

**Файл:** `src/modules/identity/infrastructure/provider.py` (добавить)

```python
class IdentityProvider(Provider):
    # ... existing providers ...

    @provide(scope=Scope.REQUEST)
    def telegram_validator(self, config: Settings) -> ITelegramInitDataValidator:
        return TelegramInitDataValidator(
            bot_token=config.BOT_TOKEN.get_secret_value(),
            max_age=config.TELEGRAM_INIT_DATA_MAX_AGE,
        )

    @provide(scope=Scope.REQUEST)
    def telegram_creds_repo(self, session: AsyncSession) -> ITelegramCredentialsRepository:
        return TelegramCredentialsRepository(session)

    @provide(scope=Scope.REQUEST)
    def login_telegram_handler(
        self,
        telegram_validator: ITelegramInitDataValidator,
        telegram_creds_repo: ITelegramCredentialsRepository,
        identity_repo: IIdentityRepository,
        customer_repo: ICustomerRepository,
        session_repo: ISessionRepository,
        role_repo: IRoleRepository,
        uow: IUnitOfWork,
        token_provider: ITokenProvider,
        logger: ILogger,
        config: Settings,
    ) -> LoginTelegramHandler:
        return LoginTelegramHandler(
            telegram_validator=telegram_validator,
            telegram_creds_repo=telegram_creds_repo,
            identity_repo=identity_repo,
            customer_repo=customer_repo,
            session_repo=session_repo,
            role_repo=role_repo,
            uow=uow,
            token_provider=token_provider,
            logger=logger,
            max_sessions=config.MAX_ACTIVE_SESSIONS_PER_IDENTITY,
            refresh_token_days=config.TELEGRAM_REFRESH_TOKEN_EXPIRE_DAYS,
        )
```

---

## 8. Database Migration

**Файл:** `alembic/versions/2026/03/20_0001_add_telegram_credentials.py`

```python
"""Add telegram_credentials table and TELEGRAM identity type.

Revision ID: <auto>
Revises: <previous>
"""

def upgrade() -> None:
    op.create_table(
        "telegram_credentials",
        sa.Column("identity_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("identities.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("first_name", sa.String(100), server_default="", nullable=False),
        sa.Column("last_name", sa.String(100), nullable=True),
        sa.Column("username", sa.String(100), nullable=True),
        sa.Column("language_code", sa.String(10), nullable=True),
        sa.Column("is_premium", sa.Boolean(), server_default=sa.text("false"),
                  nullable=False),
        sa.Column("photo_url", sa.String(512), nullable=True),
        sa.Column("allows_write_to_pm", sa.Boolean(),
                  server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        comment="Telegram auth credentials (Shared PK 1:1 with identities)",
    )
    op.create_index(
        "ix_telegram_credentials_telegram_id",
        "telegram_credentials",
        ["telegram_id"],
        unique=True,
    )

def downgrade() -> None:
    op.drop_table("telegram_credentials")
```

---

## 9. API Contract

### 9.1. POST /api/v1/auth/telegram

**Первичная авторизация через Telegram Mini App.**

**Request:**

```http
POST /api/v1/auth/telegram HTTP/1.1
Authorization: tma query_id=AAH...&user=%7B%22id%22%3A123...%7D&auth_date=1711929600&hash=abc123...
Content-Length: 0
```

**Response 200:**

```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIs...",
  "refreshToken": "dGhpcyBpcyBhIHNlY3Vy...",
  "tokenType": "bearer",
  "isNewUser": true
}
```

**Response 401:**

```json
{
  "errorCode": "INVALID_INIT_DATA",
  "message": "Invalid or tampered Telegram initData",
  "details": {}
}
```

### 9.2. POST /api/v1/auth/refresh (без изменений)

Существующий endpoint полностью совместим. Telegram-сессии используют тот же refresh flow.

### 9.3. POST /api/v1/auth/logout (без изменений)

Существующий endpoint полностью совместим.

---

## 10. Поток авторизации (Sequence Diagram)

```
┌──────────┐     ┌──────────┐     ┌───────────────┐     ┌────────┐
│ Telegram │     │ Frontend │     │   Backend     │     │   DB   │
│  Client  │     │ (React)  │     │  (FastAPI)    │     │ (PG)   │
└────┬─────┘     └────┬─────┘     └──────┬────────┘     └───┬────┘
     │                │                   │                  │
     │ User opens     │                   │                  │
     │ Mini App       │                   │                  │
     │───────────────>│                   │                  │
     │ initData       │                   │                  │
     │ (HMAC signed)  │                   │                  │
     │                │                   │                  │
     │                │ POST /auth/telegram                  │
     │                │ Authorization: tma <initData>        │
     │                │──────────────────>│                  │
     │                │                   │                  │
     │                │                   │ 1. HMAC-SHA256   │
     │                │                   │    validate      │
     │                │                   │ 2. auth_date ≤5m │
     │                │                   │ 3. parse user    │
     │                │                   │                  │
     │                │                   │ SELECT BY        │
     │                │                   │ telegram_id      │
     │                │                   │─────────────────>│
     │                │                   │                  │
     │                │                   │ [if new user]    │
     │                │                   │ INSERT identity  │
     │                │                   │ INSERT tg_creds  │
     │                │                   │ INSERT customer  │
     │                │                   │─────────────────>│
     │                │                   │                  │
     │                │                   │ [if existing]    │
     │                │                   │ UPDATE tg_creds  │
     │                │                   │─────────────────>│
     │                │                   │                  │
     │                │                   │ INSERT session   │
     │                │                   │─────────────────>│
     │                │                   │                  │
     │                │  200 OK           │                  │
     │                │  {accessToken,    │                  │
     │                │   refreshToken,   │                  │
     │                │   isNewUser}      │                  │
     │                │<──────────────────│                  │
     │                │                   │                  │
     │                │ Store tokens      │                  │
     │                │ in-memory         │                  │
     │                │                   │                  │
     │                │ GET /api/v1/...   │                  │
     │                │ Authorization:    │                  │
     │                │ Bearer <JWT>      │                  │
     │                │──────────────────>│                  │
```

---

## 11. Безопасность

### 11.1. Threat Model

| Угроза                  | Вектор                                        | Защита                                                                  |
| ----------------------- | --------------------------------------------- | ----------------------------------------------------------------------- |
| **Replay Attack**       | Перехват initData и повторная отправка        | `auth_date` freshness check (≤ 5 мин)                                   |
| **initData Forgery**    | Подделка initData без bot_token               | HMAC-SHA256 валидация с серверным bot_token                             |
| **Token Theft**         | XSS/MITM кража access_token                   | Short TTL (15 мин), tokens в in-memory (не localStorage)                |
| **Refresh Token Reuse** | Повторное использование старого refresh token | Reuse detection → revoke ALL sessions                                   |
| **Session Hijacking**   | Кража refresh_token                           | SHA-256 hash в БД, ротация при каждом refresh                           |
| **Enumeration**         | Перебор telegram_id                           | Единый 401 для всех ошибок валидации                                    |
| **Bot Token Leak**      | Утечка bot_token из initData                  | bot_token никогда не передаётся клиенту, используется только на сервере |
| **Timing Attack**       | Измерение времени сравнения хешей             | `hmac.compare_digest()` (constant-time comparison)                      |

### 11.2. Параметры токенов

| Параметр               | Значение | Обоснование                                     |
| ---------------------- | -------- | ----------------------------------------------- |
| Access Token TTL       | 15 минут | Существующий `ACCESS_TOKEN_EXPIRE_MINUTES`      |
| Access Token Algorithm | HS256    | Существующий `ALGORITHM`                        |
| Refresh Token TTL      | 7 дней   | `TELEGRAM_REFRESH_TOKEN_EXPIRE_DAYS` (PDR)      |
| initData Max Age       | 5 минут  | `TELEGRAM_INIT_DATA_MAX_AGE` (PDR)              |
| Max Sessions           | 5        | `MAX_ACTIVE_SESSIONS_PER_IDENTITY` (с eviction) |

### 11.3. Принципы

| Принцип                    | Реализация в данной SPEC                                |
| -------------------------- | ------------------------------------------------------- |
| **Zero Trust**             | initData валидируется на каждый `/auth/telegram` запрос |
| **Defense in Depth**       | HMAC-SHA256 (Telegram) → JWT (наш) → Session в БД       |
| **Least Privilege**        | Access Token: только `sub` + `sid`, без PII             |
| **Fail Secure**            | Любая ошибка валидации → 401 (не 500, не пропуск)       |
| **Separation of Concerns** | `TelegramCredentials` изолирован от `LocalCredentials`  |

---

## 12. Мониторинг и логирование

### 12.1. Structured Log Events

| Event                       | Level   | Поля                                              | Описание                 |
| --------------------------- | ------- | ------------------------------------------------- | ------------------------ |
| `telegram.login.success`    | INFO    | `identity_id`, `telegram_id`, `is_new_user`, `ip` | Успешная авторизация     |
| `telegram.login.failed`     | WARNING | `reason`, `ip`, `user_agent`                      | Невалидный initData      |
| `telegram.user.provisioned` | INFO    | `identity_id`, `telegram_id`, `referred_by`       | Новый пользователь       |
| `telegram.profile.synced`   | INFO    | `identity_id`, `telegram_id`                      | Обновление профиля       |
| `telegram.initdata.expired` | WARNING | `age_seconds`, `max_seconds`, `ip`                | Просроченный initData    |
| `telegram.session.evicted`  | INFO    | `identity_id`, `evicted_session_id`               | Вытеснение старой сессии |

### 12.2. Метрики (для будущего Prometheus/Sentry)

| Метрика                              | Тип       | Описание                                 |
| ------------------------------------ | --------- | ---------------------------------------- |
| `auth_telegram_total`                | Counter   | Общее число попыток Telegram-авторизации |
| `auth_telegram_success`              | Counter   | Успешные авторизации                     |
| `auth_telegram_new_users`            | Counter   | Новые пользователи через Telegram        |
| `auth_telegram_duration_ms`          | Histogram | Время обработки `/auth/telegram`         |
| `auth_telegram_initdata_age_seconds` | Histogram | Возраст initData при обращении           |

---

## 13. Тестирование

### 13.1. Unit Tests

| Тест                                       | Файл                                  | Описание                   |
| ------------------------------------------ | ------------------------------------- | -------------------------- |
| `test_telegram_user_data_frozen`           | `tests/unit/identity/domain/`         | Value object immutability  |
| `test_telegram_credentials_update_profile` | `tests/unit/identity/domain/`         | Profile diff detection     |
| `test_identity_register_telegram`          | `tests/unit/identity/domain/`         | Factory method             |
| `test_init_data_validation_valid`          | `tests/unit/infrastructure/security/` | Happy path HMAC            |
| `test_init_data_validation_invalid_hash`   | `tests/unit/infrastructure/security/` | Signature mismatch → error |
| `test_init_data_validation_expired`        | `tests/unit/infrastructure/security/` | auth_date too old          |
| `test_init_data_validation_missing_user`   | `tests/unit/infrastructure/security/` | No user object             |

### 13.2. Integration Tests

| Тест                                       | Описание                                            |
| ------------------------------------------ | --------------------------------------------------- |
| `test_login_telegram_new_user`             | initData → 200 + is_new_user=true + DB records      |
| `test_login_telegram_existing_user`        | initData → 200 + is_new_user=false + profile synced |
| `test_login_telegram_invalid_signature`    | Bad hash → 401                                      |
| `test_login_telegram_expired`              | Old auth_date → 401                                 |
| `test_login_telegram_session_eviction`     | 6th session → oldest evicted                        |
| `test_login_telegram_deactivated_identity` | Deactivated → 401                                   |
| `test_login_telegram_referral`             | start_param → referred_by set                       |
| `test_refresh_token_after_telegram_login`  | Telegram tokens work with standard refresh          |
| `test_logout_after_telegram_login`         | Standard logout works for Telegram sessions         |

### 13.3. Architecture Tests

| Тест                                             | Описание                        |
| ------------------------------------------------ | ------------------------------- |
| `test_telegram_domain_no_infrastructure_imports` | Domain layer purity             |
| `test_telegram_credentials_shared_pk_pattern`    | Follows Identity 1:1 convention |

---

## 14. Порядок реализации (Micro-Tasks)

| #   | Задача                                                   | Зависимости | Оценка |
| --- | -------------------------------------------------------- | ----------- | ------ |
| 1   | Value Objects: `TelegramUserData`, extend `IdentityType` | —           | S      |
| 2   | Domain: `TelegramCredentials` entity                     | #1          | S      |
| 3   | Domain: events, exceptions                               | #1          | S      |
| 4   | Domain: `ITelegramCredentialsRepository` interface       | #2          | S      |
| 5   | Infrastructure: `TelegramCredentialsModel` (ORM)         | #2          | S      |
| 6   | Migration: `telegram_credentials` table                  | #5          | S      |
| 7   | Infrastructure: `TelegramInitDataValidator`              | #1, #3      | M      |
| 8   | Infrastructure: `TelegramCredentialsRepository`          | #4, #5      | M      |
| 9   | Application: `LoginTelegramHandler`                      | #7, #8      | L      |
| 10  | Presentation: schema + router endpoint                   | #9          | M      |
| 11  | DI: `IdentityProvider` wiring                            | #7, #8, #9  | S      |
| 12  | Config: new settings                                     | —           | S      |
| 13  | Exception handlers: error mapping                        | #3          | S      |
| 14  | Unit tests                                               | #1-#8       | M      |
| 15  | Integration tests                                        | #9-#13      | L      |

**S** = small (< 1ч), **M** = medium (1-3ч), **L** = large (3-6ч)

---

## 15. Совместимость и обратная совместимость

### 15.1. Что НЕ меняется

- Существующие endpoints (`/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`) — без изменений
- JWT формат (HS256, `sub` + `sid` + `jti`) — идентичен
- `AuthContext`, `get_auth_context()`, `RequirePermission` — работают без изменений
- Все защищённые endpoints — Telegram-пользователи используют тот же `Authorization: Bearer` как и email-пользователи
- Session / RBAC / Permission resolver — полностью совместимы

### 15.2. Что добавляется

- Новый `IdentityType.TELEGRAM` (VARCHAR enum → без миграции данных)
- Новая таблица `telegram_credentials`
- Новый endpoint `POST /auth/telegram`
- Новые настройки в `.env` (с defaults → не ломает существующие деплои)

### 15.3. Связь с Bot (aiogram)

Bot и Web App используют один `BOT_TOKEN`. Пользователь, авторизованный через Mini App, известен боту по `telegram_id`:

```python
# В боте: найти customer по telegram_id
customer = await telegram_creds_repo.get_by_telegram_id(message.from_user.id)
```

---

## 16. Acceptance Criteria (из PDR)

| #   | Критерий                                        | Как проверяется                                  |
| --- | ----------------------------------------------- | ------------------------------------------------ |
| 1   | Открытие Mini App → контент < 2 сек             | Integration test: `/auth/telegram` < 300ms       |
| 2   | Невалидный initData → 401, не 500               | Unit test: `InvalidInitDataError` → 401          |
| 3   | Просроченный Access Token → авто-обновление     | Frontend concern (Axios interceptor)             |
| 4   | Reuse refresh token → все сессии инвалидированы | Integration test: existing `RefreshTokenHandler` |
| 5   | Повторное открытие → мгновенная авторизация     | Frontend concern (сохранённые токены в памяти)   |
| 6   | 1000 одновременных авторизаций/сек              | Load test: `/auth/telegram` endpoint             |
| 7   | Нет токенов в localStorage                      | Frontend audit (вне scope данной SPEC)           |
| 8   | OpenAPI документация                            | FastAPI автогенерация + `summary`/`description`  |

---

## 17. Зависимости

| Компонент           | Технология                                          |   Уже в проекте?   |
| ------------------- | --------------------------------------------------- | :----------------: |
| initData Validation | `aiogram.utils.web_app.safe_parse_webapp_init_data` | Да (aiogram 3.26+) |
| JWT                 | PyJWT + HS256                                       |         Да         |
| Refresh Token       | secrets + SHA-256                                   |         Да         |
| Session Management  | `SessionModel` + `Session` entity                   |         Да         |
| RBAC                | Existing permission resolver                        |         Да         |
| PostgreSQL          | asyncpg + SQLAlchemy 2.x                            |         Да         |
| Redis               | Reuse detection cache                               |         Да         |
| DI                  | Dishka                                              |         Да         |

**Новых зависимостей не требуется.**

---

## 18. Открытые вопросы

| #   | Вопрос                                                                                                      | Влияние           | Предложение                                         |
| --- | ----------------------------------------------------------------------------------------------------------- | ----------------- | --------------------------------------------------- |
| 1   | Нужен ли отдельный `TELEGRAM_REFRESH_TOKEN_EXPIRE_DAYS` или использовать общий `REFRESH_TOKEN_EXPIRE_DAYS`? | Config complexity | Отдельный: Telegram UX ≠ Staff UX                   |
| 2   | Eviction strategy при max sessions: oldest vs LRU?                                                          | UX                | Oldest — проще, предсказуемо                        |
| 3   | Синхронизировать ли `Customer.first_name/last_name` при profile sync?                                       | Data consistency  | Да, если customer.first_name не был изменён вручную |
| 4   | `photo_url` — кешировать в S3 или хранить URL от Telegram?                                                  | CDN/latency       | URL от Telegram (v1), S3 cache (v2)                 |
| 5   | Rate limiting на `/auth/telegram`?                                                                          | DDoS protection   | Да, через existing throttling middleware            |

---

_Документ подлежит ревью от Security Lead перед началом реализации._
