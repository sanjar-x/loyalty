# Design: Telegram Mini App Authorization

**Date:** 2026-03-20
**Status:** Approved
**Basis:** PDR "Backend Authorization" v1.0 + Deep Review findings
**Scope:** `src/modules/identity/` + `src/infrastructure/security/` + `src/modules/user/` (consumer only)

---

## 1. Summary

Add Telegram Mini App authentication to the existing Identity module. Users opening the Mini App are authenticated instantly via Telegram's cryptographically signed `initData`. The system auto-provisions new users on first open and syncs profile data on subsequent opens.

**Key architectural decisions:**
- **Event-driven Customer creation** — `LoginTelegramHandler` emits `TelegramIdentityCreatedEvent`, a consumer in the User module creates the `Customer`. No cross-module coupling.
- **Session eviction** — when session limit is reached, the oldest session is revoked (not rejected). Telegram UX must be frictionless.
- **No new dependencies** — aiogram 3.26+ already provides `safe_parse_webapp_init_data`.

---

## 2. Domain Layer

### 2.1 Value Objects

**File:** `src/modules/identity/domain/value_objects.py`

Extend `IdentityType` enum:

```python
class IdentityType(str, enum.Enum):
    LOCAL = "LOCAL"
    OIDC = "OIDC"
    TELEGRAM = "TELEGRAM"
```

New frozen VO (standard `@dataclass`, like `PermissionCode`):

```python
@dataclass(frozen=True, slots=True)
class TelegramUserData:
    """Immutable snapshot of Telegram user data from initData.

    start_param included here (not as separate return value) to match
    the convention of IOIDCProvider.validate_token() -> OIDCUserInfo.
    """
    telegram_id: int
    first_name: str
    last_name: str | None
    username: str | None
    language_code: str | None
    is_premium: bool
    photo_url: str | None
    allows_write_to_pm: bool
    start_param: str | None
```

### 2.2 Entity: TelegramCredentials

**File:** `src/modules/identity/domain/entities.py`

Uses `from attr import dataclass` (same as `LocalCredentials`, `Session` — owned entity, not AggregateRoot):

```python
@dataclass
class TelegramCredentials:
    """Telegram-specific credentials linked to an Identity.

    Analogous to LocalCredentials but stores telegram_id and profile
    fields from WebAppUser instead of email/password.
    Relationship to Identity: 1:1 (Shared PK pattern).
    """
    identity_id: uuid.UUID
    telegram_id: int
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
        """Update profile fields from new initData.

        Does NOT overwrite photo_url with None (Telegram privacy
        settings may hide it even when the user has a photo).

        Returns:
            True if at least one field changed.
        """
        changed = False
        for field in ("first_name", "last_name", "username",
                      "language_code", "is_premium", "allows_write_to_pm"):
            new_val = getattr(data, field)
            if getattr(self, field) != new_val:
                setattr(self, field, new_val)
                changed = True
        if data.photo_url is not None and self.photo_url != data.photo_url:
            self.photo_url = data.photo_url
            changed = True
        if changed:
            self.updated_at = datetime.now(UTC)
        return changed
```

No separate factory method — handler calls `Identity.register(IdentityType.TELEGRAM, AccountType.CUSTOMER)` directly (YAGNI — one call site doesn't warrant a convenience method).

### 2.3 Domain Event

**File:** `src/modules/identity/domain/events.py`

Standard `@dataclass` (from `dataclasses`), inherits `DomainEvent`, with required `aggregate_type` + `event_type` + `__post_init__`:

```python
@dataclass
class TelegramIdentityCreatedEvent(DomainEvent):
    """Emitted when a new Identity is created via Telegram Mini App.

    Consumed by User module to create Customer with referral data.
    """
    identity_id: uuid.UUID | None = None
    telegram_id: int = 0
    start_param: str | None = None
    account_type: str = "CUSTOMER"
    aggregate_type: str = "Identity"
    event_type: str = "telegram_identity_created"

    def __post_init__(self) -> None:
        if self.identity_id is None:
            raise ValueError("identity_id is required")
        if not self.aggregate_id:
            self.aggregate_id = str(self.identity_id)
```

No separate `TelegramProfileUpdatedEvent` — YAGNI, structured log is sufficient.

### 2.4 Domain Exceptions

**File:** `src/modules/identity/domain/exceptions.py`

Inherit from `UnauthorizedError` (401 auto-mapped via class hierarchy — no changes to `api/exceptions/handlers.py`):

```python
class InvalidInitDataError(UnauthorizedError):
    """initData HMAC-SHA256 signature verification failed."""
    def __init__(self) -> None:
        super().__init__(
            message="Invalid or tampered Telegram initData",
            error_code="INVALID_INIT_DATA",
        )

class InitDataExpiredError(UnauthorizedError):
    """initData auth_date exceeds maximum allowed age."""
    def __init__(self, age_seconds: int, max_seconds: int) -> None:
        super().__init__(
            message="Telegram initData expired",
            error_code="INIT_DATA_EXPIRED",
            details={"age_seconds": age_seconds, "max_seconds": max_seconds},
        )

class InitDataMissingUserError(UnauthorizedError):
    """initData does not contain user object."""
    def __init__(self) -> None:
        super().__init__(
            message="initData does not contain user data",
            error_code="INIT_DATA_MISSING_USER",
        )
```

### 2.5 Repository & Validator Interfaces

**File:** `src/modules/identity/domain/interfaces.py` (identity-specific, not shared)

```python
class ITelegramCredentialsRepository(ABC):
    """Repository contract for TelegramCredentials persistence."""

    @abstractmethod
    async def add(self, credentials: TelegramCredentials) -> TelegramCredentials:
        """Persist new Telegram credentials."""

    @abstractmethod
    async def get_by_telegram_id(
        self, telegram_id: int,
    ) -> tuple[Identity, TelegramCredentials] | None:
        """Find Identity + TelegramCredentials by Telegram user ID."""

    @abstractmethod
    async def update(self, credentials: TelegramCredentials) -> None:
        """Update Telegram credentials (profile sync)."""


class ITelegramInitDataValidator(ABC):
    """Contract for Telegram initData validation."""

    @abstractmethod
    def validate_and_parse(self, init_data_raw: str) -> TelegramUserData:
        """Validate HMAC-SHA256 signature, check freshness, parse user.

        Raises:
            InvalidInitDataError: Signature mismatch.
            InitDataExpiredError: auth_date too old.
            InitDataMissingUserError: No user object.
        """
```

### 2.6 Session Repository Extension

**File:** `src/modules/identity/domain/interfaces.py` — add to existing `ISessionRepository`:

```python
@abstractmethod
async def revoke_oldest_active(self, identity_id: uuid.UUID) -> uuid.UUID | None:
    """Revoke the oldest active session for an identity.

    Used by Telegram login to make room when session limit is reached
    (eviction instead of rejection for frictionless UX).

    Returns:
        The revoked session's UUID for cache invalidation, or None.
    """
```

---

## 3. Infrastructure Layer

### 3.1 ORM Model

**File:** `src/modules/identity/infrastructure/models.py`

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
        comment="PK + FK -> identities (Shared PK 1:1)",
    )
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False,
        comment="Telegram user ID (up to 52 significant bits)",
    )
    first_name: Mapped[str] = mapped_column(
        String(100), server_default="", nullable=False,
    )
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    username: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Telegram username without @",
    )
    language_code: Mapped[str | None] = mapped_column(
        String(10), nullable=True, comment="IETF language tag from Telegram",
    )
    is_premium: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False,
        comment="Telegram Premium subscription status",
    )
    photo_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="Telegram profile photo URL",
    )
    allows_write_to_pm: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False,
        comment="Whether user allows bot to send messages",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False,
    )

    identity: Mapped[IdentityModel] = relationship(
        back_populates="telegram_credentials",
    )
```

Add to `IdentityModel`:

```python
telegram_credentials: Mapped[TelegramCredentialsModel | None] = relationship(
    back_populates="identity", uselist=False, cascade="all, delete-orphan",
)
```

### 3.2 initData Validator

**File:** `src/infrastructure/security/telegram.py`

```python
class TelegramInitDataValidator(ITelegramInitDataValidator):
    """Validates Telegram Mini App initData using HMAC-SHA256.

    Uses aiogram's safe_parse_webapp_init_data for cryptographic
    verification, then applies additional business rules:
    - auth_date freshness check (aiogram does NOT do this)
    - user object presence check
    """

    def __init__(self, bot_token: str, max_age: int = 300) -> None:
        self._bot_token = bot_token
        self._max_age = max_age

    def validate_and_parse(self, init_data_raw: str) -> TelegramUserData:
        # 1. HMAC-SHA256 validation via aiogram
        try:
            parsed = safe_parse_webapp_init_data(
                token=self._bot_token, init_data=init_data_raw,
            )
        except ValueError:
            raise InvalidInitDataError()

        # 2. Freshness check
        # auth_date is datetime in aiogram (pydantic coerces Unix timestamp)
        age = int((datetime.now(UTC) - parsed.auth_date).total_seconds())
        if age < 0:
            # Future-dated auth_date — reject (clock skew or tampering)
            raise InitDataExpiredError(age_seconds=age, max_seconds=self._max_age)
        if age > self._max_age:
            raise InitDataExpiredError(age_seconds=age, max_seconds=self._max_age)

        # 3. User must exist
        if parsed.user is None:
            raise InitDataMissingUserError()

        user = parsed.user
        return TelegramUserData(
            telegram_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            language_code=user.language_code,
            is_premium=user.is_premium or False,
            photo_url=user.photo_url,
            allows_write_to_pm=user.allows_write_to_pm or False,
            start_param=parsed.start_param,
        )
```

### 3.3 Repository Implementation

**File:** `src/modules/identity/infrastructure/repositories/telegram_credentials_repo.py`

Data Mapper pattern (same as `IdentityRepository`):

```python
class TelegramCredentialsRepository(ITelegramCredentialsRepository):
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
        self, telegram_id: int,
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
            self._to_identity_domain(identity_model),
            self._to_credentials_domain(creds_model),
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

    # Private mapper methods follow existing IdentityRepository pattern
```

### 3.4 Session Repository Extension

Add to existing `SessionRepository`:

```python
async def revoke_oldest_active(self, identity_id: uuid.UUID) -> uuid.UUID | None:
    stmt = (
        select(SessionModel.id)
        .where(
            SessionModel.identity_id == identity_id,
            SessionModel.is_revoked == False,
            SessionModel.expires_at > func.now(),
        )
        .order_by(SessionModel.created_at.asc())
        .limit(1)
    )
    session_id = (await self._session.execute(stmt)).scalar_one_or_none()
    if session_id is None:
        return None
    await self._session.execute(
        sa_update(SessionModel)
        .where(SessionModel.id == session_id)
        .values(is_revoked=True)
    )
    return session_id
```

### 3.5 Database Migration

**File:** `alembic/versions/2026/03/20_xxxx_add_telegram_credentials.py`

- `CREATE TABLE telegram_credentials` with all columns from 3.1
- Unique index on `telegram_id`
- No changes to existing tables (`IdentityType` is VARCHAR, not native enum)

### 3.6 Configuration

**File:** `src/bootstrap/config.py` — add to `Settings`:

```python
TELEGRAM_INIT_DATA_MAX_AGE: int = 300
TELEGRAM_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
```

Update `.env.example` with commented defaults.

---

## 4. Application Layer

### 4.1 Command & Result

**File:** `src/modules/identity/application/commands/login_telegram.py`

```python
@dataclass(frozen=True)
class LoginTelegramCommand:
    init_data_raw: str
    ip_address: str
    user_agent: str

@dataclass(frozen=True)
class LoginTelegramResult:
    access_token: str
    refresh_token: str
    identity_id: uuid.UUID
    is_new_user: bool
```

### 4.2 Handler

Follows `LoginOIDCHandler` pattern exactly:

```python
class LoginTelegramHandler:
    def __init__(
        self,
        telegram_validator: ITelegramInitDataValidator,
        telegram_creds_repo: ITelegramCredentialsRepository,
        identity_repo: IIdentityRepository,
        session_repo: ISessionRepository,
        role_repo: IRoleRepository,
        uow: IUnitOfWork,
        token_provider: ITokenProvider,
        permission_resolver: IPermissionResolver,
        logger: ILogger,
        max_sessions: int = 5,
        refresh_token_days: int = 7,
    ) -> None:
        self._validator = telegram_validator
        self._telegram_creds_repo = telegram_creds_repo
        self._identity_repo = identity_repo
        self._session_repo = session_repo
        self._role_repo = role_repo
        self._uow = uow
        self._token_provider = token_provider
        self._permission_resolver = permission_resolver
        self._logger = logger.bind(handler="LoginTelegramHandler")
        self._max_sessions = max_sessions
        self._refresh_token_days = refresh_token_days

    async def handle(self, command: LoginTelegramCommand) -> LoginTelegramResult:
        # 1. Validate initData (outside UoW — no DB needed)
        telegram_user = self._validator.validate_and_parse(command.init_data_raw)

        async with self._uow:
            # 2. Lookup by telegram_id
            result = await self._telegram_creds_repo.get_by_telegram_id(
                telegram_user.telegram_id
            )
            is_new_user = result is None

            if is_new_user:
                identity = await self._provision_new_identity(telegram_user)
            else:
                identity, credentials = result
                identity.ensure_active()
                if credentials.update_profile(telegram_user):
                    await self._telegram_creds_repo.update(credentials)
                    self._logger.info(
                        "telegram.profile.synced",
                        identity_id=str(identity.id),
                        telegram_id=telegram_user.telegram_id,
                    )

            # 3. Session limit — evict oldest if needed
            # Note: race condition between count_active() and revoke_oldest_active()
            # is low-risk for Telegram (single-user, sequential app opens).
            # If strict enforcement is needed later, use SELECT ... FOR UPDATE.
            active_count = await self._session_repo.count_active(identity.id)
            if active_count >= self._max_sessions:
                evicted_id = await self._session_repo.revoke_oldest_active(
                    identity.id
                )
                if evicted_id:
                    await self._permission_resolver.invalidate(evicted_id)
                    self._logger.info(
                        "telegram.session.evicted",
                        identity_id=str(identity.id),
                        evicted_session_id=str(evicted_id),
                    )

            # 4. Create session + tokens
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

            # 5. Register aggregate for outbox (only new users have events)
            if is_new_user:
                self._uow.register_aggregate(identity)
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

    async def _provision_new_identity(
        self, data: TelegramUserData,
    ) -> Identity:
        """Create Identity + TelegramCredentials + default role atomically."""
        identity = Identity.register(IdentityType.TELEGRAM, AccountType.CUSTOMER)
        await self._identity_repo.add(identity)

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

        customer_role = await self._role_repo.get_by_name("customer")
        if customer_role:
            await self._role_repo.assign_to_identity(identity.id, customer_role.id)

        # Event-driven: Consumer in User module creates Customer
        identity.add_domain_event(
            TelegramIdentityCreatedEvent(
                identity_id=identity.id,
                telegram_id=data.telegram_id,
                start_param=data.start_param,
                aggregate_id=str(identity.id),
            )
        )

        self._logger.info(
            "telegram.user.provisioned",
            identity_id=str(identity.id),
            telegram_id=data.telegram_id,
            start_param=data.start_param,
        )

        return identity
```

### 4.3 Event Consumer (User module)

**File:** `src/modules/user/application/consumers/identity_events.py` — add to existing file

Follows the exact pattern of `create_user_on_identity_registered`: functional `@broker.task` + `@inject`, `FromDishka` dependencies, idempotency check, `register_aggregate()`, `generate_referral_code()`.

```python
@broker.task(
    queue="iam_events",
    exchange="taskiq_rpc_exchange",
    routing_key="user.telegram_identity_created",
    max_retries=3,
    retry_on_error=True,
    timeout=30,
)
@inject
async def create_customer_on_telegram_identity_created(
    identity_id: str,
    telegram_id: int,
    customer_repo: FromDishka[ICustomerRepository],
    uow: FromDishka[IUnitOfWork],
    start_param: str | None = None,
    account_type: str = "CUSTOMER",
) -> dict:
    """Create a Customer when a Telegram identity is provisioned.

    Follows the same pattern as create_user_on_identity_registered:
    - Idempotency check (skip if customer already exists)
    - generate_referral_code() for consistent format
    - register_aggregate() for outbox events
    - Referral resolution via start_param
    """
    identity_uuid = uuid.UUID(identity_id)

    # Idempotency: skip if customer already exists (retry safety)
    existing = await customer_repo.get(identity_uuid)
    if existing:
        logger.info("customer.already_exists", identity_id=identity_id)
        return {"status": "skipped", "reason": "already_exists"}

    # Resolve referral
    referred_by: uuid.UUID | None = None
    if start_param:
        referrer = await customer_repo.get_by_referral_code(start_param)
        referred_by = referrer.id if referrer else None

    customer = Customer.create_from_identity(
        identity_id=identity_uuid,
        referral_code=generate_referral_code(),
        referred_by=referred_by,
    )

    async with uow:
        await customer_repo.add(customer)
        uow.register_aggregate(customer)
        await uow.commit()

    logger.info(
        "customer.created_from_telegram",
        identity_id=identity_id,
        telegram_id=telegram_id,
        referred_by=str(referred_by) if referred_by else None,
    )
    return {"status": "success", "type": "customer"}
```

---

## 5. Presentation Layer

### 5.1 Schema

**File:** `src/modules/identity/presentation/schemas.py`

```python
class TelegramTokenResponse(CamelModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    is_new_user: bool
```

### 5.2 Router Endpoint

**File:** `src/modules/identity/presentation/router_auth.py`

```python
@auth_router.post(
    "/telegram",
    response_model=TelegramTokenResponse,
    summary="Authenticate via Telegram Mini App",
)
async def login_telegram(
    request: Request,
    handler: FromDishka[LoginTelegramHandler],
) -> TelegramTokenResponse:
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("tma "):
        raise UnauthorizedError(
            message="Expected Authorization: tma <initData>",
            error_code="INVALID_AUTH_SCHEME",
        )
    init_data_raw = auth_header[4:]

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

### 5.3 DI Provider

**File:** `src/modules/identity/infrastructure/provider.py`

```python
# Attribute-style (like existing repos)
telegram_creds_repo = provide(
    TelegramCredentialsRepository, scope=Scope.REQUEST,
    provides=ITelegramCredentialsRepository,
)

# Factory methods (need config values)
@provide(scope=Scope.REQUEST)
def telegram_validator(self) -> ITelegramInitDataValidator:
    return TelegramInitDataValidator(
        bot_token=settings.BOT_TOKEN.get_secret_value(),
        max_age=settings.TELEGRAM_INIT_DATA_MAX_AGE,
    )

@provide(scope=Scope.REQUEST)
def login_telegram_handler(
    self,
    telegram_validator: ITelegramInitDataValidator,
    telegram_creds_repo: ITelegramCredentialsRepository,
    identity_repo: IIdentityRepository,
    session_repo: ISessionRepository,
    role_repo: IRoleRepository,
    uow: IUnitOfWork,
    token_provider: ITokenProvider,
    permission_resolver: IPermissionResolver,
    logger: ILogger,
) -> LoginTelegramHandler:
    return LoginTelegramHandler(
        telegram_validator=telegram_validator,
        telegram_creds_repo=telegram_creds_repo,
        identity_repo=identity_repo,
        session_repo=session_repo,
        role_repo=role_repo,
        uow=uow,
        token_provider=token_provider,
        permission_resolver=permission_resolver,
        logger=logger,
        max_sessions=settings.MAX_ACTIVE_SESSIONS_PER_IDENTITY,
        refresh_token_days=settings.TELEGRAM_REFRESH_TOKEN_EXPIRE_DAYS,
    )
```

---

## 6. What Does NOT Change

- `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/logout/all` — untouched
- JWT format (HS256, `sub` + `sid` + `jti`) — identical for Telegram sessions
- `AuthContext`, `get_auth_context()`, `RequirePermission` — work without changes
- All protected endpoints — Telegram users use same `Authorization: Bearer <JWT>`
- Session / RBAC / Permission resolver — fully compatible
- `api/exceptions/handlers.py` — no changes (hierarchy-based auto-mapping)
- `api/router.py` — `auth_router` already included, new endpoint appears automatically

---

## 7. API Contract

### POST /api/v1/auth/telegram

**Request:**
```http
POST /api/v1/auth/telegram HTTP/1.1
Authorization: tma query_id=AAH...&user=%7B%22id%22%3A123...%7D&auth_date=1711929600&hash=abc...
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

**Error responses:**
| Code | error_code | When |
|------|-----------|------|
| 401 | `INVALID_AUTH_SCHEME` | Missing `Authorization: tma` header |
| 401 | `INVALID_INIT_DATA` | HMAC signature mismatch |
| 401 | `INIT_DATA_EXPIRED` | `auth_date` older than 5 minutes |
| 401 | `INIT_DATA_MISSING_USER` | No `user` in initData |
| 403 | `IDENTITY_DEACTIVATED` | Identity was deactivated |

---

## 8. Database Migration

**Table:** `telegram_credentials`

| Column | Type | Constraints |
|--------|------|-------------|
| `identity_id` | UUID | PK, FK → identities(id) CASCADE |
| `telegram_id` | BIGINT | UNIQUE, NOT NULL |
| `first_name` | VARCHAR(100) | NOT NULL, DEFAULT '' |
| `last_name` | VARCHAR(100) | NULLABLE |
| `username` | VARCHAR(100) | NULLABLE |
| `language_code` | VARCHAR(10) | NULLABLE |
| `is_premium` | BOOLEAN | NOT NULL, DEFAULT false |
| `photo_url` | VARCHAR(512) | NULLABLE |
| `allows_write_to_pm` | BOOLEAN | NOT NULL, DEFAULT false |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Indexes:** `ix_telegram_credentials_telegram_id` (unique)

No changes to existing tables. `IdentityType` stored as VARCHAR — `TELEGRAM` value requires no data migration.

---

## 9. Testing Strategy

### 9.1 Unit Tests (domain, no I/O)

| Test | Validates |
|------|-----------|
| `test_telegram_user_data_immutable` | frozen=True enforcement |
| `test_telegram_credentials_update_profile_detects_changes` | Returns True on change |
| `test_telegram_credentials_update_profile_no_changes` | Returns False when same |
| `test_telegram_credentials_photo_url_not_erased_by_none` | Privacy-safe photo handling |
| `test_identity_register_telegram_type` | Correct type + account_type |
| `test_telegram_event_requires_identity_id` | ValueError if None |
| `test_telegram_event_sets_aggregate_id` | Auto-set from identity_id |
| `test_valid_init_data_parses` | Happy path (mock aiogram) |
| `test_invalid_signature_raises` | InvalidInitDataError |
| `test_expired_auth_date_raises` | InitDataExpiredError with details |
| `test_missing_user_raises` | InitDataMissingUserError |
| `test_start_param_extracted` | Included in TelegramUserData |
| `test_future_auth_date_raises` | Negative age (clock skew) rejected |

### 9.2 Integration Tests (real DB)

| Test | Scenario |
|------|----------|
| `test_login_telegram_new_user` | 200, isNewUser=true, records in DB |
| `test_login_telegram_existing_user` | 200, isNewUser=false, profile synced |
| `test_login_telegram_invalid_signature_401` | 401 INVALID_INIT_DATA |
| `test_login_telegram_expired_401` | 401 INIT_DATA_EXPIRED |
| `test_login_telegram_missing_tma_header_401` | 401 INVALID_AUTH_SCHEME |
| `test_login_telegram_deactivated_403` | 403 IDENTITY_DEACTIVATED |
| `test_login_telegram_session_eviction` | 6th login evicts oldest |
| `test_refresh_after_telegram_login` | Standard refresh works |
| `test_logout_after_telegram_login` | Standard logout works |
| `test_telegram_referral_event` | Event contains start_param |

### 9.3 Architecture Tests

| Test | Validates |
|------|-----------|
| `test_telegram_domain_no_infrastructure_imports` | Domain purity |
| `test_telegram_credentials_shared_pk_pattern` | FK → identities (1:1) |

---

## 10. Implementation Order

| # | Task | Size |
|---|------|------|
| 1 | Value objects: `TelegramUserData`, extend `IdentityType` | S |
| 2 | Entity: `TelegramCredentials` | S |
| 3 | Event: `TelegramIdentityCreatedEvent` | S |
| 4 | Exceptions: 3 new exception classes | S |
| 5 | Interfaces: `ITelegramCredentialsRepository`, `ITelegramInitDataValidator`, `ISessionRepository.revoke_oldest_active` | S |
| 6 | ORM: `TelegramCredentialsModel` + IdentityModel relationship | S |
| 7 | Migration: `telegram_credentials` table | S |
| 8 | Validator: `TelegramInitDataValidator` | M |
| 9 | Repository: `TelegramCredentialsRepository` | M |
| 10 | Session repo: `revoke_oldest_active` implementation | S |
| 11 | Handler: `LoginTelegramHandler` | L |
| 12 | Consumer: `create_customer_on_telegram_identity_created` (add to existing identity_events.py) | M |
| 13 | Presentation: schema + router endpoint | M |
| 14 | DI: provider wiring | S |
| 15 | Config: new settings + .env.example | S |
| 16 | Unit tests | M |
| 17 | Integration tests | L |

S = <1h, M = 1-3h, L = 3-6h

---

## 11. Corrections vs Original SPEC

| Issue | SPEC (was) | Design (now) |
|-------|-----------|--------------|
| `@dataclass` vs `attr.dataclass` | Standard `@dataclass` for entity | `attr.dataclass` (matches codebase) |
| Domain events | `@dataclass(frozen=True)`, no `DomainEvent` base | `@dataclass`, inherits `DomainEvent`, has `__post_init__` |
| Exceptions | `DomainException` base (doesn't exist) | Inherits `UnauthorizedError` (auto 401) |
| Exception handler mapping | `_EXCEPTION_MAP` dict | No changes needed (hierarchy-based) |
| `register_aggregate()` | Missing | Called for new users before commit |
| Customer creation | Direct `ICustomerRepository` in handler | Event-driven consumer (bounded context isolation) |
| Validator return type | `tuple[TelegramUserData, str \| None]` | `TelegramUserData` (start_param inside) |
| Validator interface location | `shared/interfaces/security.py` | `identity/domain/interfaces.py` |
| Session limit | `pass` placeholder | `revoke_oldest_active()` + cache invalidation |
| `photo_url` sync | Blind overwrite | Don't erase with None (privacy settings) |
| `auth_date` type | `int(time.time())` | `datetime.now(UTC) - parsed.auth_date` (aiogram returns datetime) |
| `Identity.register_telegram()` | Defined but only one call site | Removed — call `Identity.register(TELEGRAM, CUSTOMER)` directly (YAGNI) |
| Consumer pattern | Class-based with `__init__` + `handle()` | Functional `@broker.task` + `@inject` + `FromDishka` (matches existing consumers) |
| Consumer idempotency | Missing | Added `customer_repo.get()` check before create |
| Consumer `register_aggregate` | Missing | Added before `uow.commit()` |
| Consumer referral code | `secrets.token_urlsafe(6)` | `generate_referral_code()` from domain services |
| Future `auth_date` | Accepted (negative age passes check) | Rejected — `age < 0` raises `InitDataExpiredError` |
| Session eviction race | Not documented | Documented as known low-risk limitation |
