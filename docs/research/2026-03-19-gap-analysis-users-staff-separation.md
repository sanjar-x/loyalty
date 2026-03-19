# Gap Analysis: Разделение Users / Staff

> **Дата:** 2026-03-19
> **Входные документы:**
> - `2026-03-19-backend-users-staff-current-state-analysis.md` — текущее состояние бэкенда
> - `2026-03-19-users-staff-separation-deep-research.md` — исследование рынка и best practices
>
> **Методология:** Каждый industry standard сопоставляется с фактическим состоянием кода.
> Severity: 🔴 Critical · 🟠 Major · 🟡 Minor

---

## Executive Summary

Проанализировано **42 аспекта** по 8 категориям. Результат:

| Severity | Кол-во | Описание |
|----------|--------|----------|
| 🔴 Critical | 7 | Архитектурные пробелы, блокирующие бизнес-функционал |
| 🟠 Major | 9 | Несоответствия best practices, требующие доработки |
| 🟡 Minor | 6 | Улучшения, повышающие качество |
| ✅ OK | 20 | Соответствует или превосходит industry standard |

**Ключевой вывод:** Фундамент (Identity BC, RBAC, CQRS, events) — **на уровне enterprise**. Критические gaps сосредоточены в трёх областях: (1) отсутствие доменного разделения Customer/Staff, (2) отсутствие Staff invitation flow, (3) Staff-фронт полностью на моках.

---

## 1. Доменная модель: разделение типов пользователей

### GAP-1.1 🔴 Нет дискриминатора типа аккаунта в Identity

| Аспект | Детали |
|--------|--------|
| **Industry standard** | Shopify, Medusa, Azure AD B2C — явное разделение Staff/Customer. Saleor использует `is_staff` (Django), что [считается антипаттерном](https://forum.djangoproject.com/t/understanding-of-user-is-staff-field/35838). Okta — `user_type` назначается при создании и **immutable**. |
| **Наш текущий код** | `Identity` entity (`src/modules/identity/domain/entities.py:30`) имеет `type: IdentityType` — но это тип **аутентификации** (LOCAL/OIDC), не тип аккаунта. Нет поля `account_type` или `user_category`. |
| **SQL** | Таблица `identities` не содержит колонку для разделения. Единственный способ отличить staff от customer — JOIN через `identity_roles → roles WHERE name IN ('admin', 'content_manager', ...)` — хрупкий, зависит от seed data. |
| **Impact** | Невозможно: раздельные списки, раздельные API, разные session policies, GDPR-compliant data segregation. |
| **Рекомендация** | Добавить `AccountType` (CUSTOMER / STAFF) в `Identity` entity + колонку `account_type` в таблицу `identities`. Immutable после создания (как у Okta). |
| **Effort** | 2 дня |
| **Файлы** | `identity/domain/value_objects.py`, `identity/domain/entities.py`, `identity/infrastructure/models.py`, migration |

### GAP-1.2 🔴 Единая таблица User для всех типов аккаунтов

| Аспект | Детали |
|--------|--------|
| **Industry standard** | Medusa — **отдельные модули** User (admin) и Customer. Sylius (PHP) — отдельные entities `AdminUser` и `ShopUser`. Azure AD — **отдельные directories** для B2B и B2C. Рекомендация из research: **Separate Tables** pattern. |
| **Наш текущий код** | Один `User` aggregate (`src/modules/user/domain/entities.py:19`) с полями `first_name, last_name, phone, profile_email` — одинаковый для всех. |
| **Impact** | Невозможно добавить type-specific поля: `referral_code`, `loyalty_tier` (customer) или `department`, `position`, `invited_by` (staff) без nullable-bloat. Нарушает SRP. |
| **Рекомендация** | Разделить `User` на два aggregate: `Customer` (с referral-полями) и `StaffMember` (с invitation-полями). Обе таблицы с FK → `identities.id`. |
| **Effort** | 3 дня |
| **Файлы** | `user/domain/entities.py` → split, `user/infrastructure/models.py` → 2 ORM models, 2 repositories, migration |

### GAP-1.3 🟠 Регистрация не различает типы аккаунтов

| Аспект | Детали |
|--------|--------|
| **Industry standard** | Shopify — Staff приглашаются, Customer регистрируются сами. Stripe — Team Members добавляются через Settings > Team. Auth0 — Organization Members получают invite, End Users регистрируются через Universal Login. |
| **Наш текущий код** | `RegisterHandler` (`identity/application/commands/register.py`) — единый flow, **всем** назначает роль `customer`. Нет отдельного пути для staff. |
| **Impact** | Сотрудник вынужден регистрироваться как клиент, затем админ вручную назначает staff-роли. Нет audit trail «кто пригласил». |
| **Рекомендация** | `RegisterHandler` → явно ставить `account_type=CUSTOMER`. Новый `AcceptStaffInvitationHandler` → создаёт Identity с `account_type=STAFF`. |
| **Effort** | 1 день (часть GAP-2.1) |

### GAP-1.4 ✅ Shared Primary Key (Identity ↔ User) — соответствует

| Аспект | Детали |
|--------|--------|
| **Industry standard** | Azure AD B2C — единый identity provider, раздельные профили. Medusa — User.id привязан к auth identity. |
| **Наш текущий код** | `users.id = identities.id` (FK + CASCADE) — правильная реализация shared PK. |
| **Вердикт** | ✅ Паттерн корректен. При разделении на Customer/StaffMember — обе таблицы сохранят shared PK с `identities.id`. |

### GAP-1.5 ✅ Cross-module communication через events — соответствует

| Аспект | Детали |
|--------|--------|
| **Industry standard** | DDD: bounded contexts общаются через domain events. |
| **Наш текущий код** | `IdentityRegisteredEvent` → `CreateUserHandler` (via Outbox + TaskIQ). Идемпотентно. |
| **Вердикт** | ✅ При разделении: `IdentityRegisteredEvent` → если `account_type=CUSTOMER` → `CreateCustomerHandler`; если `STAFF` → `CreateStaffMemberHandler`. Паттерн масштабируется. |

---

## 2. Staff Invitation Flow

### GAP-2.1 🔴 Отсутствует backend для приглашения сотрудников

| Аспект | Детали |
|--------|--------|
| **Industry standard** | Stripe — invite по email, expire 10 дней, pre-assigned roles. Shopify — invite с permissions, expire 7 дней. GitHub — org invite, 7 дней. Все используют: CSPRNG token → SHA-256 hash → DB → email → accept → assign roles. |
| **Наш текущий код** | **Нет** entity `StaffInvitation`. **Нет** таблицы `staff_invitations`. **Нет** endpoints для invite/accept/revoke. |
| **Frontend** | Staff page (`frontend/src/app/admin/settings/staff/page.jsx`) генерирует фейковые токены через `crypto.getRandomValues()` на клиенте. URL hardcoded: `https://invite.admin.loyaltymarket.ru/{random}`. |
| **Impact** | Невозможно пригласить сотрудника через систему. Нет audit trail. Нет secure token flow. |
| **Рекомендация** | Реализовать полный invitation flow по research spec: `StaffInvitation` entity + repo + `InviteStaffCommand` + `AcceptStaffInvitationCommand` + `RevokeStaffInvitationCommand`. Token: `secrets.token_urlsafe(32)` → SHA-256 → DB. TTL: 72 часа. |
| **Effort** | 4 дня |
| **Новые файлы** | entity, repo interface, repo impl, ORM model, 3 command handlers, migration, router, schemas |

### GAP-2.2 🟠 Нет email-уведомления при приглашении

| Аспект | Детали |
|--------|--------|
| **Industry standard** | Все платформы (Stripe, Shopify, Auth0, GitHub) отправляют email с invite link. |
| **Наш текущий код** | Нет email-сервиса в проекте. Нет bounded context для notifications. |
| **Рекомендация** | Phase 1: возвращать invite link в API response (админ копирует и отправляет вручную). Phase 2: интегрировать email-сервис. |
| **Effort** | Phase 1: 0 (часть GAP-2.1). Phase 2: 3 дня (отдельная задача). |

### GAP-2.3 🟡 Нет автоматического expire приглашений

| Аспект | Детали |
|--------|--------|
| **Industry standard** | Stripe — auto-expire через 10 дней. Shopify — auto-expire 7 дней. |
| **Наш текущий код** | Нет invitation entity → нет expiry logic. |
| **Рекомендация** | Проверка `expires_at` при accept (synchronous). Фоновый cron для массового expire — could have (не критично, т.к. проверка при accept достаточна). |
| **Effort** | 0 (часть GAP-2.1 — проверка в `StaffInvitation.accept()`) |

---

## 3. API и Presentation Layer

### GAP-3.1 🔴 Единый endpoint `/admin/identities` для всех типов

| Аспект | Детали |
|--------|--------|
| **Industry standard** | Medusa — `/admin/users` (staff) и `/store/customers` (customers). Saleor — отдельные GraphQL queries `staffUsers` и `customers`. Shopify — разные API endpoints. |
| **Наш текущий код** | Один `GET /api/v1/admin/identities` (`identity/presentation/router_admin.py`). SQL query (`list_identities.py`) делает `LEFT JOIN identities + local_credentials + users` без фильтра по типу. Возвращает ALL. |
| **Impact** | Админ видит всех в одном списке. Фронт не может показать раздельно «клиенты» и «сотрудники». |
| **Рекомендация** | Новые endpoints: `GET /admin/staff` (ListStaffQuery) и `GET /admin/customers` (ListCustomersQuery). Старый `/admin/identities` — deprecated, добавить опциональный фильтр `account_type`. |
| **Effort** | 2 дня |
| **Файлы** | Новые query handlers, новые роутеры, новые schemas |

### GAP-3.2 🟠 Конфликт путей `/users/me` между двумя модулями

| Аспект | Детали |
|--------|--------|
| **Industry standard** | Один bounded context владеет одним URL path prefix. |
| **Наш текущий код** | `router_account.py` (identity) → `DELETE /users/me`, `GET /users/me/sessions`. `router.py` (user) → `GET /users/me`, `PATCH /users/me`. Два модуля на одном prefix — architectural smell. |
| **Рекомендация** | При переходе к Customer/Staff — переименовать: identity account → `/account/me/...`, customer profile → `/profile/me/...`, или объединить в один router. |
| **Effort** | 1 день |

### GAP-3.3 🟠 Нет пермиссии `staff:manage`

| Аспект | Детали |
|--------|--------|
| **Industry standard** | Stripe — отдельная роль `IAM Admin` для управления team members. Shopify — отдельный permission для staff management. |
| **Наш текущий код** | 13 permissions в seed. `identities:manage` покрывает и customers, и staff — нет granularity. Нет `staff:manage`, `staff:invite`, `customers:manage`. |
| **Рекомендация** | Добавить: `staff:manage` (CRUD staff), `staff:invite` (создание приглашений), `customers:read` (просмотр клиентов), `customers:manage` (деактивация клиентов). |
| **Effort** | 0.5 дня |
| **Файлы** | `scripts/seed_dev.sql`, migration для новых permissions |

### GAP-3.4 ✅ CamelCase serialization — соответствует

Все Pydantic schemas наследуют `CamelModel` → автоматический snake_case → camelCase.

### GAP-3.5 ✅ Error responses — единый формат

Все ошибки возвращают `{message, error_code, details}` — консистентно.

---

## 4. RBAC и Permission Model

### GAP-4.1 🔴 Роль `super_admin` в коде, но не в seed data

| Аспект | Детали |
|--------|--------|
| **Industry standard** | Stripe — `Super Administrator` создаётся автоматически для владельца аккаунта. Все enterprise: системные роли должны быть в seed/migration. |
| **Наш текущий код** | `AdminDeactivateIdentityHandler` проверяет `role.name == "super_admin"` и `count_identities_with_role("super_admin")` — **last admin protection**. Но в `seed_dev.sql` нет роли `super_admin` — есть только `admin`. |
| **Impact** | Last admin protection **не работает**. Можно деактивировать единственного admin без предупреждения. |
| **Рекомендация** | Решить: (A) переименовать seed role `admin` → `super_admin`, или (B) изменить код handler'а на `admin`. Вариант B проще и не ломает существующие данные. |
| **Effort** | 0.5 дня |
| **Файлы** | `identity/application/commands/deactivate_identity.py` или `scripts/seed_dev.sql` |

### GAP-4.2 🟠 Нет Static Separation of Duties (SoD) для Customer/Staff ролей

| Аспект | Детали |
|--------|--------|
| **Industry standard** | NIST RBAC Level 3 — Static SoD: запрет на конфликтующие роли. Research рекомендует: Customer НЕ МОЖЕТ иметь staff-роли, Staff НЕ МОЖЕТ иметь роль `customer`. |
| **Наш текущий код** | `AssignRoleHandler` не проверяет совместимость ролей. Можно назначить `admin` роль identity, у которого уже есть `customer` role — создаётся «гибрид». |
| **Рекомендация** | При добавлении `AccountType`: `AssignRoleHandler` → проверять, что назначаемая роль совместима с `account_type`. Staff-роли только для `STAFF`, `customer` роль только для `CUSTOMER`. |
| **Effort** | 0.5 дня (часть GAP-1.1) |

### GAP-4.3 ✅ Session-Role Activation (NIST Dynamic RBAC) — превосходит

| Аспект | Детали |
|--------|--------|
| **Industry standard** | Большинство платформ используют Identity-Based permissions. NIST Dynamic RBAC (session-level activation) — enterprise-grade. |
| **Наш текущий код** | `session_roles` table + recursive CTE через `role_hierarchy` + Redis cache-aside (TTL=300s). При `assign_role` → пропагация в все активные `session_roles`. |
| **Вердикт** | ✅ **Превосходит** industry standard. Это enterprise-level реализация, которую используют единицы. |

### GAP-4.4 ✅ Role Hierarchy — соответствует

Role hierarchy через `role_hierarchy` table + recursive CTE. `admin` наследует все дочерние роли.

### GAP-4.5 ✅ Privilege Escalation Prevention — соответствует

`SetRolePermissionsHandler` проверяет, что admin не может назначить permissions, которых нет у него самого.

---

## 5. Security

### GAP-5.1 🟠 Нет разных session policies для Staff/Customer

| Аспект | Детали |
|--------|--------|
| **Industry standard** | OWASP рекомендует: Staff — idle timeout 15-30 мин, absolute 8 часов, concurrent 1-3. Customer — idle 30-60 мин, absolute 30 дней, unlimited concurrent. Research: Stripe требует 2FA для admin ops. |
| **Наш текущий код** | Единые настройки для всех: `ACCESS_TOKEN_EXPIRE_MINUTES=15`, `REFRESH_TOKEN_EXPIRE_DAYS=30`, `MAX_ACTIVE_SESSIONS_PER_IDENTITY=5`. Нет различий по типу. |
| **Рекомендация** | После добавления `AccountType`: разные `max_sessions`, `refresh_ttl`, `access_ttl` в зависимости от типа. Config: `STAFF_MAX_SESSIONS=3`, `STAFF_REFRESH_TOKEN_DAYS=7`. |
| **Effort** | 1 день |
| **Файлы** | `bootstrap/config.py`, `identity/application/commands/login.py`, `infrastructure/security/jwt.py` |

### GAP-5.2 🟡 Нет audit logging для Staff-действий

| Аспект | Детали |
|--------|--------|
| **Industry standard** | WorkOS — dedicated Audit Logs API. NIST SP 800-92 — structured audit events. Research: логировать все CRUD операции staff, доступ к PII, role changes. |
| **Наш текущий код** | structlog с access logging middleware (`src/api/middlewares/`). Но нет structured audit events с `actor_id`, `action`, `target_type`, `target_id`. |
| **Рекомендация** | Phase 2 задача. Добавить `AuditLogEntry` entity или structured log events в command handlers. |
| **Effort** | 3 дня (отдельная задача) |

### GAP-5.3 🟡 Нет password reset flow

| Аспект | Детали |
|--------|--------|
| **Industry standard** | Все платформы имеют password reset. OWASP — обязательный функционал. |
| **Наш текущий код** | Нет endpoint, нет token generation, нет email sending. |
| **Рекомендация** | Отдельная задача, не блокирует User/Staff separation. |
| **Effort** | 2 дня |

### GAP-5.4 🟡 Нет email verification при регистрации

| Аспект | Детали |
|--------|--------|
| **Industry standard** | Auth0, Clerk, Firebase — email verification по умолчанию. |
| **Наш текущий код** | `RegisterHandler` создаёт Identity сразу, без подтверждения email. |
| **Рекомендация** | Отдельная задача, не блокирует User/Staff separation. |
| **Effort** | 2 дня |

### GAP-5.5 ✅ JWT + Refresh Token Rotation — превосходит

SHA-256 hashing, constant-time comparison (`hmac.compare_digest`), reuse detection → session revocation. Enterprise-grade.

### GAP-5.6 ✅ Argon2id password hashing — превосходит

С auto-rehash bcrypt → argon2id при login. Best practice.

---

## 6. Referral System

### GAP-6.1 🔴 Отсутствует реферальная система

| Аспект | Детали |
|--------|--------|
| **Industry standard** | Loyalty-платформы (Open Loyalty, Voucherify) — referral как core feature. Research: `referral_code` (8 char, CSPRNG, исключить O/0/I/1/L), `referred_by`, `referral_tier`, tracking table. |
| **Наш текущий код** | **Нет** referral кода в User entity. **Нет** таблицы referrals. Frontend имеет mock data (`src/data/referrals.js`) и страницу настроек рефералов (`/admin/settings/referrals`), но backend пуст. Frontend User mock ожидает `source` field — его нет в backend. |
| **Impact** | Ключевой бизнес-функционал loyalty-платформы отсутствует. |
| **Рекомендация** | При создании `Customer` aggregate → добавить `referral_code` (auto-generated), `referred_by_customer_id`. Отдельная таблица `referrals` для tracking. Это customer-only функционал (staff не участвует). |
| **Effort** | 5 дней (отдельный feature, Phase 3) |

### GAP-6.2 🟠 Нет domain events для referral tracking

| Аспект | Детали |
|--------|--------|
| **Industry standard** | Research: `CustomerRegistered` → `GenerateReferralCode`, `OrderCompleted` → `CheckReferralCompletion` → `CreditReferralReward`. |
| **Наш текущий код** | `IdentityRegisteredEvent` существует, но не содержит referral context. Нет `OrderCompleted` event (order module не реализован). |
| **Рекомендация** | При разделении: `IdentityRegisteredEvent` → if CUSTOMER → `CreateCustomerHandler` → auto-generate `referral_code`. Referral tracking через отдельные events позже. |
| **Effort** | Включено в GAP-6.1 |

---

## 7. Event-Driven Integration

### GAP-7.1 🟠 `IdentityReactivatedEvent` не имеет consumer

| Аспект | Детали |
|--------|--------|
| **Industry standard** | Все domain events должны обрабатываться. Orphan events — architectural smell. |
| **Наш текущий код** | `ReactivateIdentityHandler` эмитит `IdentityReactivatedEvent`, но **нет consumer**. Если user был anonymized (GDPR), реактивация identity не восстанавливает PII данные в User. |
| **Impact** | Реактивированный пользователь имеет `first_name="[DELETED]"`, `last_name="[DELETED]"`, `phone=None`. |
| **Рекомендация** | Добавить consumer: `handle_identity_reactivated` → (A) логировать для audit, (B) отправить уведомление админу что PII утрачено. Восстановление PII невозможно (GDPR right to erasure). |
| **Effort** | 0.5 дня |
| **Файлы** | `user/application/consumers/identity_events.py` |

### GAP-7.2 ✅ Transactional Outbox — enterprise-grade

Domain events → `outbox_messages` атомарно с бизнес-данными → TaskIQ relay. Идемпотентные consumers.

### GAP-7.3 ✅ Consumer idempotency — соответствует

`create_user_on_identity_registered` проверяет существование User перед созданием.

---

## 8. Frontend Integration

### GAP-8.1 🔴 Staff страница полностью на моках

| Аспект | Детали |
|--------|--------|
| **Industry standard** | Все management pages — real API. |
| **Наш текущий код** | `frontend/src/data/staff.js` — 3 hardcoded записи. `frontend/src/services/staff.js` — `getStaff()` возвращает mock. UI генерирует invite links на клиенте (`crypto.getRandomValues`). Roles hardcoded: "Администратор", "Контент-менеджер". |
| **Impact** | Staff management не функционален. |
| **Рекомендация** | После backend API → переключить на `GET /api/admin/staff`, `POST /api/admin/staff/invitations`. Добавить BFF routes. |
| **Effort** | 3 дня (frontend) |

### GAP-8.2 🟠 Frontend Users data model не совпадает с backend

| Аспект | Детали |
|--------|--------|
| **Наш текущий код** | Frontend mock `users.js` ожидает: `handle`, `userId`, `source`, `followers.value`, `orders.value` — **ничего из этого нет в backend** User entity. |
| **Impact** | Frontend Users page при переключении с моков на реальный API потеряет большинство полей. |
| **Рекомендация** | При создании `Customer` aggregate — рассмотреть добавление `source` (referral tracking). `orders` и `followers` — данные из других bounded contexts, получать через separate API calls или denormalized read models. |
| **Effort** | 2 дня (frontend + backend read models) |

### GAP-8.3 🟡 Нет BFF routes для Roles management

| Аспект | Детали |
|--------|--------|
| **Наш текущий код** | Frontend Roles page (`/admin/settings/roles/page.jsx`) существует, BFF routes для roles существуют (`frontend/src/app/api/admin/roles/`). |
| **Вердикт** | ✅ Частично реализовано. При добавлении staff-specific permissions — обновить UI. |

### GAP-8.4 ✅ BFF для Identity management — работает

`frontend/src/app/api/admin/identities/` — полный набор BFF routes (list, detail, deactivate, reactivate, assign/revoke roles).

---

## 9. Тестовое покрытие

### GAP-9.1 🟠 Нет unit-тестов для критических admin handlers

| Аспект | Детали |
|--------|--------|
| **Не покрыто** | `AdminDeactivateIdentityHandler` (self-deactivation guard, last admin protection), `ReactivateIdentityHandler`, `UpdateRoleHandler` (system role protection), `SetRolePermissionsHandler` (privilege escalation prevention). |
| **Impact** | При рефакторинге для User/Staff separation — нет safety net. |
| **Рекомендация** | Написать unit-тесты ДО рефакторинга. |
| **Effort** | 2 дня |

### GAP-9.2 🟡 Нет тестов для TaskIQ consumers

| Аспект | Детали |
|--------|--------|
| **Не покрыто** | `create_user_on_identity_registered`, `anonymize_user_on_identity_deactivated`, `invalidate_permissions_cache_on_role_change`. |
| **Рекомендация** | Покрыть при добавлении новых consumers для Customer/Staff. |
| **Effort** | 1 день |

### GAP-9.3 ✅ Architecture boundary tests — enterprise-grade

7 правил в `tests/architecture/test_boundaries.py` — domain purity, cross-module isolation, layer dependencies. При добавлении новых modules — тесты автоматически защищают boundaries.

---

## 10. Сводная Decision Matrix

### 10.1 Architectural Decision: как разделять?

| Паттерн | Shopify | Medusa | Saleor | Azure AD | Наша рек-ция | Score |
|---------|---------|--------|--------|----------|-------------|-------|
| **Separate Tables** (Customer/StaffMember) | ✅ | ✅ | ❌ | ✅ | ✅ | 4/5 |
| **Single Table + Discriminator** (`is_staff`) | ❌ | ❌ | ✅ | ❌ | ❌ | 1/5 |
| **Organization Model** | ❌ | ❌ | ❌ | Частично | ❌ | 0/5 |

**Решение:** Separate Tables + AccountType discriminator в Identity.

### 10.2 Что реализовано vs что нужно

| Компонент | Текущее | Целевое | Gap |
|-----------|---------|---------|-----|
| Identity BC (auth) | ✅ Enterprise | ✅ + AccountType | 🟠 Малый |
| RBAC (roles/permissions) | ✅ NIST Dynamic | ✅ + SoD + staff:manage | 🟠 Малый |
| Session management | ✅ Refresh rotation | ✅ + type-specific policies | 🟠 Средний |
| User Profile | ⚠️ Единый User | Customer + StaffMember | 🔴 Большой |
| Staff Invitation | ❌ Отсутствует | Full invite flow | 🔴 Большой |
| Referral System | ❌ Отсутствует | Codes + tracking + rewards | 🔴 Большой |
| Admin API | ⚠️ Единый endpoint | Раздельные staff/customers | 🔴 Средний |
| Frontend Staff | ❌ Моки | Real API | 🔴 Большой |
| Frontend Users | ⚠️ Real API, но показывает всех | Только customers | 🟠 Малый |
| Event consumers | ✅ 3 из 4 | ✅ + type-aware routing | 🟠 Малый |
| Audit logging | ⚠️ Access logs | Structured audit events | 🟡 Средний |
| Tests | ⚠️ Gaps в admin handlers | Full coverage | 🟠 Средний |

---

## 11. Рекомендуемый порядок устранения gaps

### Phase 0: Подготовка (2 дня)

| # | Gap | Задача | Effort |
|---|-----|--------|--------|
| 0.1 | GAP-4.1 | Исправить `super_admin` → `admin` в `AdminDeactivateIdentityHandler` | 0.5 дня |
| 0.2 | GAP-9.1 | Написать unit-тесты для admin handlers (до рефакторинга) | 1.5 дня |

### Phase 1: Domain Separation — Backend Core (5 дней)

| # | Gap | Задача | Effort |
|---|-----|--------|--------|
| 1.1 | GAP-1.1 | `AccountType` VO + field в Identity + migration + backfill | 2 дня |
| 1.2 | GAP-1.2 | Split User → Customer + StaffMember (entities, repos, ORM, migration) | 2 дня |
| 1.3 | GAP-1.3 | `RegisterHandler` → `CUSTOMER`, event routing по account_type | 0.5 дня |
| 1.4 | GAP-3.3 | Новые permissions: `staff:manage`, `staff:invite`, `customers:read` | 0.5 дня |

### Phase 2: Staff Invitation Flow (4 дня)

| # | Gap | Задача | Effort |
|---|-----|--------|--------|
| 2.1 | GAP-2.1 | `StaffInvitation` entity + repo + migration | 1.5 дня |
| 2.2 | GAP-2.1 | `InviteStaff`, `AcceptInvitation`, `RevokeInvitation` commands | 1.5 дня |
| 2.3 | GAP-2.1 | Invitation endpoints + schemas | 1 день |

### Phase 3: API Separation (3 дня)

| # | Gap | Задача | Effort |
|---|-----|--------|--------|
| 3.1 | GAP-3.1 | `ListStaffQuery` + `ListCustomersQuery` + handlers | 1.5 дня |
| 3.2 | GAP-3.1 | Staff/Customer admin routers + schemas | 1 день |
| 3.3 | GAP-3.2 | Resolve `/users/me` path conflict | 0.5 дня |

### Phase 4: Frontend Integration (5 дней)

| # | Gap | Задача | Effort |
|---|-----|--------|--------|
| 4.1 | GAP-8.1 | Staff page → real API (list, search, filters) | 2 дня |
| 4.2 | GAP-8.1 | Staff invite modal → real API | 1 день |
| 4.3 | GAP-8.2 | Users page → `/admin/customers` endpoint | 1 день |
| 4.4 | — | Invite acceptance page (`/invite/{token}`) | 1 день |

### Phase 5: Referral System (5 дней, отдельный feature)

| # | Gap | Задача | Effort |
|---|-----|--------|--------|
| 5.1 | GAP-6.1 | `referral_code` в Customer, generation logic | 1 день |
| 5.2 | GAP-6.1 | `referrals` table + tracking entity | 2 дня |
| 5.3 | GAP-6.1 | Referral rewards logic | 2 дня |

### Phase 6: Security Hardening (2 дня, параллельно)

| # | Gap | Задача | Effort |
|---|-----|--------|--------|
| 6.1 | GAP-5.1 | Type-specific session policies | 1 день |
| 6.2 | GAP-4.2 | Static SoD в `AssignRoleHandler` | 0.5 дня |
| 6.3 | GAP-7.1 | Consumer для `IdentityReactivatedEvent` | 0.5 дня |

### Deferred (не блокирует separation)

| Gap | Задача | Приоритет |
|-----|--------|-----------|
| GAP-5.2 | Audit logging | P2 |
| GAP-5.3 | Password reset flow | P2 |
| GAP-5.4 | Email verification | P3 |
| GAP-2.2 | Email notification service | P3 |

---

## 12. Итого: Effort Summary

| Phase | Effort | Opus Calls (feature pipeline) |
|-------|--------|-------------------------------|
| Phase 0: Подготовка | 2 дня | hotfix mode (0) |
| Phase 1: Domain Separation | 5 дней | task mode per MT (~10) |
| Phase 2: Staff Invitation | 4 дня | task mode per MT (~8) |
| Phase 3: API Separation | 3 дня | task mode per MT (~6) |
| Phase 4: Frontend | 5 дней | manual (frontend) |
| Phase 5: Referral | 5 дней | feature pipeline (~20) |
| Phase 6: Security | 2 дня | task mode (~4) |
| **Total** | **~26 дней** | **~48 Opus calls** |

**Phases 1-3 (Backend core)** = 12 дней — это MVP для User/Staff separation.
**Phase 4 (Frontend)** = 5 дней — делает separation видимым для пользователя.
**Phase 5-6** — можно отложить на следующий sprint.
