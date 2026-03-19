# Deep Research: User Segmentation — Customers (Referrals) vs Staff

> **Дата:** 2026-03-19
> **Автор:** Architecture Research Agent
> **Контекст:** E-commerce loyalty/marketplace platform — backend на Python/FastAPI, DDD/Clean Architecture/CQRS

---

## Executive Summary

1. **Индустриальный стандарт** — разделение Staff и Customer на уровне данных: Saleor, Medusa, Shopify, Django используют **единую Identity-таблицу** с дискриминатором (`is_staff` / `user_type`), но разный набор профильных данных хранится в отдельных таблицах или контекстах.

2. **Enterprise IAM решения** (Auth0 Organizations, Okta User Types, Azure AD B2B/B2C, Keycloak Realms) подтверждают паттерн: **единая аутентификация + раздельная авторизация и профили**. Azure AD B2C буквально создаёт отдельный directory для customers.

3. **Для нашей архитектуры (DDD + Modular Monolith)** оптимален **гибридный подход**: Identity (bounded context) остаётся единым для аутентификации, а User context разделяется на Customer и Staff через discriminator + раздельные таблицы профильных данных.

4. **Referral-система** — это Customer-only функционал, моделируется как отдельный aggregate внутри User (или нового Referral) bounded context. Рекомендуется **pre-generation** кодов и **materialized path** для дерева рефералов.

5. **Staff Invitation Flow** должен использовать криптографически стойкие токены (CSPRNG, 128+ бит), TTL 72 часа, одноразовое использование, и audit logging каждого шага.

6. **RBAC** уже реализован в нашем Identity module — нужно добавить системные роли `customer` и `staff` с разграничением permissions по user type.

7. **GDPR** требует разные правовые основания для обработки данных staff (legitimate interest) и customers (consent), что подтверждает необходимость логического разделения.

---

## 1. Market Leaders Analysis

### 1.1 Shopify

**Модель разделения:** Полностью раздельные системы.

- **Staff Accounts** — внутренние пользователи магазина (менеджеры, операторы). Управляются через Settings > Users. Имеют granular permissions (orders, products, customers, analytics и т.д.)
- **Customer Accounts** — покупатели. Отдельная система аутентификации, hosted на инфраструктуре Shopify. В 2025-2026 Shopify мигрировал на новую архитектуру Customer Accounts, deprecating legacy систему
- **Collaborator Accounts** — внешние разработчики/агентства с временным доступом

**Ключевые решения:**
- Staff и Customer — это **разные сущности** с разными authentication flows
- Staff приглашаются по email, Customer регистрируются сами
- B2B расширение позволяет Customer-аккаунтам иметь иерархию (company → locations → staff)
- Приглашения Staff expire через определённый период
- Каждый Staff имеет набор permissions, назначаемых при приглашении

**Источники:** [Shopify Staff vs Collaborator](https://www.hulkapps.com/blogs/shopify-hub/navigating-the-flexibility-of-shopify-collaborator-vs-staff-accounts-a-comprehensive-guide), [New Customer Accounts](https://www.revize.app/blog/shopify-new-customer-accounts-migration-guide-deadlines), [Staff Permissions](https://www.saasant.com/blog/staff-user-permission-levels-in-shopify/)

### 1.2 Stripe

**Модель разделения:** Организационная иерархия.

Stripe разделяет пользователей на:
- **Team Members** — сотрудники с доступом к Dashboard
- **Customers** — объекты в API, не имеющие доступа к Dashboard

**Роли Team Members (иерархия):**

| Роль | Описание |
|------|----------|
| **Super Administrator** | Полный доступ, создаётся автоматически для владельца аккаунта |
| **Administrator** | Управление настройками, пользователями, интеграциями |
| **IAM Admin** | Только управление пользователями и ролями |
| **Developer** | Доступ к API ключам и интеграциям |
| **Analyst** | Read/write доступ к данным |
| **Support Specialist** | Работа с поддержкой, без доступа к финансам |
| **Identity** | Только верификация пользователей |
| **Sandbox Administrator** | Управление sandbox-средами |

**Invitation Flow:**
- Приглашение по email через Dashboard (Settings > Team)
- Можно указать несколько email через запятую
- Приглашение **expire через 10 дней**
- Роли назначаются при приглашении
- Поддержка organization-level и account-level ролей
- 2FA обязательна (passkeys, security keys, TOTP, SMS)

**Источники:** [Stripe Roles](https://docs.stripe.com/get-started/account/teams/roles), [Stripe Team Management](https://docs.stripe.com/get-started/account/orgs/team), [New Roles Blog](https://stripe.com/blog/new-roles-and-permissions-in-the-dashboard)

### 1.3 Auth0 / Clerk / WorkOS

#### Auth0 Organizations

Auth0 использует **Organizations** как логические контейнеры для пользователей:

- **End Users** — все пользователи в Auth0 tenant (customers)
- **Organization Members** — пользователи, принадлежащие конкретной организации (staff/partners)
- Два подхода к хранению: **isolated users** (user принадлежит одной org) и **shared users** (user может быть в нескольких orgs)
- Каждая организация может иметь свои authentication methods (SSO, social login и т.д.)

**Источники:** [Auth0 Multi-Tenant Best Practices](https://auth0.com/docs/get-started/auth0-overview/create-tenants/multi-tenant-apps-best-practices), [Auth0 Organizations](https://auth0.com/blog/using-auth0-for-b2b-multi-and-single-tenant-saas-solutions/)

#### Clerk

Clerk разделяет:
- **Application Users** — все зарегистрированные пользователи
- **Organization Members** — пользователи в организациях с ролями

Ключевой паттерн: **authentication (users) отделён от authorization (organization members)**. Роли определяются на уровне приложения, но назначаются на уровне организации. Поддерживается **Personal Account** — workspace пользователя без организации.

**Источники:** [Clerk Organizations](https://clerk.com/docs/guides/organizations/overview), [Clerk RBAC](https://clerk.com/docs/guides/organizations/control-access/roles-and-permissions)

#### WorkOS

WorkOS фокусируется на enterprise features:
- **Domain-Managed Users** — email совпадает с verified domain организации, автоматически становятся members
- **Domain Guest Users** — email не совпадает с verified domain, получают приглашение
- Directory Sync обеспечивает ULM (User Lifecycle Management) — auto-provisioning/de-provisioning через IdP

**Источники:** [WorkOS Directory Sync](https://workos.com/docs/directory-sync), [WorkOS Organizations](https://workos.com/blog/model-your-b2b-saas-with-organizations)

### 1.4 Saleor (Open Source, Python/Django)

**Модель:** Единая таблица User с `is_staff` дискриминатором.

```python
class User(PermissionsMixin, AbstractBaseUser):
    email = EmailField(unique=True)  # USERNAME_FIELD
    first_name = CharField(max_length=256)
    last_name = CharField(max_length=256)
    is_staff = BooleanField(default=False)    # <-- дискриминатор
    is_active = BooleanField(default=True)
    is_confirmed = BooleanField(default=True)
    uuid = UUIDField(unique=True)
    jwt_token_key = CharField()  # для инвалидации JWT
    note = TextField(blank=True)  # заметки staff о customers
    number_of_orders = IntegerField(default=0)  # денормализация
```

**Разделение в UserManager:**
- `customers()` — `is_staff=False` ИЛИ staff с историей заказов
- `staff()` — `is_staff=True`

**Permissions:** через Django Groups + custom `effective_permissions` property, кэширование разрешений, агрегация permissions из user assignments + group membership.

**GraphQL API:** Публичный API для storefront (customers), Admin API для dashboard (staff). Разные endpoints, разные permission requirements.

**Источники:** [Saleor GitHub — account/models.py](https://github.com/saleor/saleor/blob/main/saleor/account/models.py), [Saleor Architecture](https://docs.saleor.io/docs/3.x/overview/architecture)

### 1.5 Medusa.js (Open Source)

**Модель:** Полностью раздельные модули.

- **User Module** — admin users (staff). Роли: `admin`, `member`, `developer`. Пользователи могут приглашать других пользователей
- **Customer Module** — покупатели. Guest и registered customers

**Ключевое:** Роли в Medusa **не обеспечивают ACL** — это metadata, а не enforcement. Реальное разграничение доступа — через разделение API routes (Admin API vs Storefront API).

**Источники:** [Medusa Users](https://docs.medusajs.com/v1/modules/users), [Medusa Customers](https://docs.medusajs.com/v1/modules/customers/overview)

### 1.6 Other Notable Platforms

#### Spree Commerce (Ruby on Rails)

- Два дефолтных Role: `admin` и `user`
- Авторизация через **CanCanCan** library
- Пользователи проверяются через `has_spree_role?` method
- Permission Sets — коллекции разрешений, привязанных к ролям
- Отдельные модули: Admin Panel и Storefront

**Источники:** [Spree Permissions](https://spreecommerce.org/docs/developer/customization/permissions), [Spree Architecture](https://docs.spreecommerce.org/developer/core-concepts/architecture)

#### WooCommerce (WordPress)

Использует WordPress User Roles:
- `administrator`, `shop_manager`, `customer`, `subscriber`
- Capability-based system через `WP_Roles`
- Все пользователи в одной `wp_users` таблице

---

## 2. Architectural Patterns

### 2.1 Single Table Discriminator (STI)

**Описание:** Единая таблица пользователей с полем-дискриминатором (`user_type`, `is_staff`, и т.д.). Все типы пользователей хранятся в одной таблице.

**Реализация:**
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    user_type VARCHAR(20) NOT NULL DEFAULT 'customer',  -- 'customer' | 'staff'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL,
    -- общие поля для всех типов
);
```

**Кто использует:** Django (`is_staff`), Saleor, WooCommerce, WordPress, многие legacy-системы.

**Pros:**
- Простота реализации и миграции
- Единая таблица — простые JOIN'ы
- Один authentication flow
- Легко запросить "все пользователи"

**Cons:**
- Nullable поля (referral_code нужен только customers, department — только staff)
- Нарушение SRP — одна таблица для двух доменных смыслов
- Django's `is_staff` — [«the biggest wart»](https://forum.djangoproject.com/t/understanding-of-user-is-staff-field/35838) в permission системе
- Сложно добавить type-specific бизнес-логику
- Риск data leak между типами

### 2.2 Separate Tables / Bounded Contexts

**Описание:** Разные таблицы/модули для каждого типа пользователя. Общая Identity для аутентификации, раздельные профили.

**Реализация:**
```sql
-- Shared: Identity (authentication)
CREATE TABLE identities (
    id UUID PRIMARY KEY,
    type VARCHAR(20) NOT NULL,  -- 'LOCAL' | 'OIDC'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL
);

-- Customer-specific
CREATE TABLE customers (
    id UUID PRIMARY KEY REFERENCES identities(id),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    phone VARCHAR(50),
    referral_code VARCHAR(20) UNIQUE,
    referred_by UUID REFERENCES customers(id),
    loyalty_tier VARCHAR(20) DEFAULT 'bronze',
    created_at TIMESTAMPTZ NOT NULL
);

-- Staff-specific
CREATE TABLE staff_members (
    id UUID PRIMARY KEY REFERENCES identities(id),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    department VARCHAR(100),
    position VARCHAR(100),
    invited_by UUID REFERENCES staff_members(id),
    invitation_accepted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL
);
```

**Кто использует:** Shopify (полностью раздельные системы), Medusa (отдельные модули), Azure AD B2B/B2C (отдельные directories).

**Pros:**
- Чистое разделение доменов (DDD-friendly)
- Нет nullable полей
- Type-specific бизнес-логика без bloat
- Легко добавлять type-specific функционал
- GDPR compliance — разные правовые основания для разных типов данных

**Cons:**
- Сложнее "показать всех пользователей" (требует JOIN/UNION)
- Два миграционных пути
- Потенциальная десинхронизация данных

### 2.3 Organization/Workspace Model

**Описание:** Пользователи привязаны к организациям. Staff — это members организации, Customers — внешние пользователи.

**Реализация:**
```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE
);

CREATE TABLE organization_memberships (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    organization_id UUID REFERENCES organizations(id),
    role VARCHAR(50) NOT NULL,  -- 'owner', 'admin', 'member'
    invited_by UUID REFERENCES users(id),
    accepted_at TIMESTAMPTZ,
    UNIQUE(user_id, organization_id)
);
```

**Кто использует:** Auth0 Organizations, Clerk, WorkOS, Stripe (account-level roles).

**Pros:**
- Масштабируется для multi-tenant SaaS
- User может быть и customer, и staff (разные orgs)
- Естественная модель для B2B

**Cons:**
- Overengineering для single-tenant e-commerce
- Усложняет простые сценарии
- Дополнительный уровень абстракции

### 2.4 Comparison Matrix

| Критерий | STI (Discriminator) | Separate Tables | Organization Model |
|----------|--------------------|-----------------|--------------------|
| **Сложность реализации** | Низкая | Средняя | Высокая |
| **DDD-совместимость** | Слабая | Отличная | Хорошая |
| **Масштабируемость типов** | Слабая | Хорошая | Отличная |
| **GDPR compliance** | Сложно | Легко | Средне |
| **Query производительность** | Отличная | Хорошая | Средняя |
| **Type-specific логика** | Сложно | Легко | Средне |
| **Multi-tenant** | Не подходит | Не подходит | Идеально |
| **Подходит для нас** | Частично | **Да** | Overengineering |

**Рекомендация для нашей платформы:** Паттерн **Separate Tables / Bounded Contexts** — единый Identity для аутентификации, раздельные Customer и StaffMember для профилей.

---

## 3. Enterprise IAM Solutions

### 3.1 Keycloak

**Модель:** Realms как изолированные пространства.

- **Realm** — изолированное пространство с users, apps, roles, groups. Один user может существовать в разных realms с разными credentials
- **Groups** — коллекции пользователей с общими attributes и role mappings. Поддерживают иерархию
- **Service Accounts** — технические аккаунты для client credentials flow
- **Roles** — Realm Roles (глобальные) и Client Roles (per-application)

**Подход к разделению:**
- Отдельные Realms: максимальная изоляция, но сложнее управлять
- Один Realm + Groups: проще, подходит когда полная изоляция не нужна
- Organizations (новая фича): промежуточный вариант для B2B

**Источники:** [Keycloak Server Admin](https://www.keycloak.org/docs/latest/server_admin/index.html), [Keycloak Realms](https://documentation.cloud-iam.com/resources/keycloak-realm.html)

### 3.2 Azure AD B2B/B2C

**Ключевое архитектурное решение Microsoft — полное разделение:**

| Аспект | Azure AD B2B | Azure AD B2C |
|--------|-------------|-------------|
| **Целевые пользователи** | Партнёры, поставщики, staff | Потребители (customers) |
| **Directory** | Тот же directory, что и сотрудники | **Отдельный B2C directory** |
| **Управление идентичностью** | Внешний user сохраняет свой IdP | B2C управляет identity |
| **Self-service** | Нет (приглашение) | Да (self-registration) |
| **Масштаб** | Тысячи | Миллионы |
| **Кастомизация UI** | Ограниченная | Полная |

**Вывод:** Microsoft считает, что **consumer identity и internal identity — это фундаментально разные вещи**, заслуживающие отдельных directories.

**Источники:** [Azure AD B2C Overview](https://learn.microsoft.com/en-us/azure/active-directory-b2c/overview), [B2B vs B2C](https://kocho.co.uk/blog/azure-ad-b2b-b2c-differences-external-access/)

### 3.3 AWS Cognito

**Два основных подхода:**

**Single User Pool + Groups (рекомендуется):**
```
User Pool
├── Group: Administrators (precedence 1, IAM role: AdminRole)
├── Group: Staff (precedence 2, IAM role: StaffRole)
├── Group: Customers (precedence 3, IAM role: CustomerRole)
└── Group: ReadOnly (precedence 4, IAM role: ReadOnlyRole)
```

- Groups включаются в JWT как `cognito:groups` claim
- Custom attributes: `custom:userType` (staff/customer), `custom:organizationId`
- Lambda triggers для автоматического назначения groups при регистрации

**Multiple User Pools:**
- Полная изоляция конфигураций
- Разные authentication flows
- Увеличивает maintenance overhead

**Рекомендация Cognito:** Single Pool + Groups для большинства случаев, Multiple Pools только при regulatory/compliance requirements.

**Источники:** [Cognito Groups](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-user-groups.html), [Cognito Best Practices](https://reintech.io/blog/structuring-aws-cognito-user-pools)

### 3.4 Okta

**Universal Directory с Custom User Types:**

- До 10 user types в одном Okta org
- Каждый user type — копия base Okta profile с custom attributes
- User type назначается при создании и **не может быть изменён** после
- Groups для управления доступом к applications
- App assignments через group membership

**Источники:** [Okta User Types](https://help.okta.com/en-us/content/topics/users-groups-profiles/usgp-usertypes-about.htm), [Okta Universal Directory](https://developer.okta.com/docs/concepts/universal-directory/)

### 3.5 FusionAuth

- **Tenants** — изолированные namespaces для Users, Applications, Groups
- **Registrations** — связь User ↔ Application (user может быть зарегистрирован в нескольких apps)
- Roles назначаются per-registration (не globally)
- Tenant Manager — UI для management пользователей в отдельном tenant

**Источники:** [FusionAuth Tenants](https://fusionauth.io/docs/get-started/core-concepts/tenants), [FusionAuth Multi-Tenant](https://fusionauth.io/docs/extend/examples/multi-tenant)

### 3.5 Recommendations for Our Stack

Учитывая наш стек (Python/FastAPI, single-tenant e-commerce):

1. **Не нужен** Organization/Workspace model — мы single-tenant
2. **Не нужны** отдельные Realms/Pools — один Identity bounded context достаточен
3. **Нужно:** discriminator в Identity или User + раздельные profile таблицы (как Azure AD B2C разделяет directories, но на уровне таблиц)
4. **RBAC groups** (как в Cognito) уже реализованы через наш Role/Permission model

---

## 4. Referral System Architecture

### 4.1 Industry Standards

Referral-системы в e-commerce делятся на:

- **Single-level** — referrer получает бонус за каждого приведённого customer (Shopify, большинство e-commerce)
- **Multi-level (MLM)** — бонусы распространяются вверх по дереву рефералов (Avon, Amway)
- **Tiered** — размер бонуса зависит от количества рефералов (loyalty tiers)

Для e-commerce/loyalty платформы рекомендуется **single-level с tiered бонусами**.

**API-first платформы для справки:**
- **Open Loyalty** — composable loyalty/referral engine с REST API и webhooks
- **Voucherify** — API-first promotions/referral engine
- **ReferralCandy** — SaaS referral platform

**Источники:** [Open Loyalty Referral](https://www.openloyalty.io/product/referral-program-software), [Voucherify](https://www.openloyalty.io/insider/how-to-integrate-an-api-first-loyalty-engine-with-your-tech-stack)

### 4.2 Database Schema Patterns

**Рекомендуемая схема для нашей платформы:**

```sql
-- Referral code привязан к Customer
CREATE TABLE customers (
    id UUID PRIMARY KEY REFERENCES identities(id),
    referral_code VARCHAR(12) UNIQUE NOT NULL,
    referred_by_customer_id UUID REFERENCES customers(id),
    referral_tier VARCHAR(20) DEFAULT 'bronze',
    total_referrals INTEGER DEFAULT 0,
    total_referral_earnings DECIMAL(12,2) DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL
);

-- Отслеживание рефералов
CREATE TABLE referrals (
    id UUID PRIMARY KEY,
    referrer_id UUID NOT NULL REFERENCES customers(id),
    referee_id UUID NOT NULL REFERENCES customers(id),
    referral_code VARCHAR(12) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending | completed | expired | cancelled
    reward_amount DECIMAL(12,2),
    reward_type VARCHAR(20),  -- points | discount | cashback
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE(referee_id)  -- один customer может быть referred только одним
);

-- Referral rewards (bonus начисления)
CREATE TABLE referral_rewards (
    id UUID PRIMARY KEY,
    referral_id UUID NOT NULL REFERENCES referrals(id),
    recipient_id UUID NOT NULL REFERENCES customers(id),  -- referrer или referee
    reward_type VARCHAR(20) NOT NULL,  -- 'referrer_bonus' | 'referee_welcome'
    amount DECIMAL(12,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending | credited | expired
    credited_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL
);
```

### 4.3 Referral Code Generation

**Два подхода:**

| Подход | Описание | Pros | Cons |
|--------|----------|------|------|
| **Runtime** | Генерация при регистрации | Простота | Contention, collision checks |
| **Pre-generation** | Batch-генерация кодов заранее | Нет collisions, быстрая выдача | Требует отдельную таблицу/очередь |

**Рекомендуемый формат кода:**

```python
import secrets
import string

def generate_referral_code(length: int = 8) -> str:
    """Генерация 8-символьного alphanumeric кода.

    8 символов, case-insensitive (A-Z, 0-9) = 36^8 = ~2.8 trillion комбинаций.
    Исключаем визуально похожие символы: 0, O, 1, I, L.
    """
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # 30 символов
    return "".join(secrets.choice(alphabet) for _ in range(length))
```

**Best practices:**
- Код должен быть **case-insensitive** и **easy to read** (исключить O/0, I/1/L)
- Длина 6-8 символов достаточна (30^8 = 6.5 * 10^11 комбинаций)
- Персонализированные коды (имя пользователя) — опционально для premium tier
- Уникальность обеспечивается UNIQUE constraint в БД
- При collision — retry с новым кодом (вероятность collision < 0.0001% при 1M users)

**Источники:** [Referral Code Architecture](https://medium.com/@siddhusingh/referral-code-generation-architecture-contention-free-scalable-approach-68ea44ee5fb0), [System Design Referral](https://dev.to/vaib215/system-design-of-a-referral-system-4hik)

### 4.4 Referral Tree / Hierarchy

Для single-level referral (рекомендуется) иерархия плоская — `referred_by_customer_id` в таблице customers достаточно.

Если потребуется multi-level (MLM), два подхода:

**Approach 1: Parent ID (Adjacency List)**
```sql
-- Простой, требует recursive queries
SELECT * FROM customers WHERE referred_by_customer_id = :referrer_id;

-- Весь downline через CTE:
WITH RECURSIVE downline AS (
    SELECT id, referral_code, referred_by_customer_id, 1 as level
    FROM customers WHERE referred_by_customer_id = :root_id
    UNION ALL
    SELECT c.id, c.referral_code, c.referred_by_customer_id, d.level + 1
    FROM customers c JOIN downline d ON c.referred_by_customer_id = d.id
    WHERE d.level < 5  -- max 5 levels
)
SELECT * FROM downline;
```

**Approach 2: Materialized Path**
```sql
-- Быстрый read, сложнее write
ALTER TABLE customers ADD COLUMN referral_hierarchy VARCHAR(500);
-- Пример: "root_id.level1_id.level2_id.current_id"

-- Все downline одним запросом:
SELECT * FROM customers
WHERE referral_hierarchy LIKE :prefix || '.%';
```

**Рекомендация:** Для e-commerce начать с **Adjacency List** (проще), перейти на Materialized Path при необходимости multi-level.

**Источники:** [Multi-Level Referral Schema](https://www.coderbased.com/p/sql-db-design-multi-level-referral-system)

### 4.5 Integration with User Segmentation

Referral — это **Customer-only** функционал:
- Staff **не имеют** referral codes
- Staff **не могут** быть referred
- Referral code генерируется при создании Customer profile (не Identity)
- Referral tracking — отдельный aggregate, реагирует на domain events (`CustomerRegistered`, `OrderCompleted`)

**Domain Events flow:**
```
CustomerRegistered → GenerateReferralCode (command)
OrderCompleted → CheckReferralCompletion (command) → CreditReferralReward
```

---

## 5. Staff Invitation Flow

### 5.1 Security Best Practices

Согласно OWASP и enterprise best practices:

1. **Token generation:** CSPRNG с минимум 128 бит entropy (Python: `secrets.token_urlsafe(32)`)
2. **Token storage:** Хранить только **hash** токена (SHA-256), не plain text
3. **TTL:** 72 часа для invitation tokens (Stripe — 10 дней, но для нашего случая 72h достаточно)
4. **One-time use:** Токен аннулируется после первого использования
5. **Revocation:** Admin может отозвать приглашение до его использования
6. **Rate limiting:** Ограничение на количество приглашений (anti-spam)
7. **Encrypted transmission:** Только HTTPS
8. **Audit logging:** Логировать создание, использование и отзыв приглашений

**Источники:** [OWASP Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html), [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)

### 5.2 Token Generation & Validation

```python
import hashlib
import secrets
from datetime import UTC, datetime, timedelta

@dataclass
class StaffInvitation:
    """Domain entity for staff invitation."""

    id: uuid.UUID
    email: str
    token_hash: str  # SHA-256 hash of invitation token
    invited_by: uuid.UUID  # staff member who sent invitation
    role_ids: list[uuid.UUID]  # pre-assigned roles
    status: str  # 'pending' | 'accepted' | 'expired' | 'revoked'
    expires_at: datetime
    accepted_at: datetime | None
    created_at: datetime

    @classmethod
    def create(
        cls,
        email: str,
        invited_by: uuid.UUID,
        role_ids: list[uuid.UUID],
        ttl_hours: int = 72,
    ) -> tuple["StaffInvitation", str]:
        """Create invitation, return (entity, raw_token)."""
        raw_token = secrets.token_urlsafe(32)  # 256 bits
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        now = datetime.now(UTC)

        invitation = cls(
            id=uuid.uuid7(),
            email=email,
            token_hash=token_hash,
            invited_by=invited_by,
            role_ids=role_ids,
            status="pending",
            expires_at=now + timedelta(hours=ttl_hours),
            accepted_at=None,
            created_at=now,
        )
        return invitation, raw_token

    def accept(self) -> None:
        if self.status != "pending":
            raise InvitationNotPendingError()
        if datetime.now(UTC) > self.expires_at:
            self.status = "expired"
            raise InvitationExpiredError()
        self.status = "accepted"
        self.accepted_at = datetime.now(UTC)

    def revoke(self) -> None:
        if self.status != "pending":
            raise InvitationNotPendingError()
        self.status = "revoked"
```

### 5.3 Invitation Lifecycle

```
Admin → POST /api/admin/staff/invite {email, role_ids}
    │
    ├─ Validate: email not already registered
    ├─ Validate: admin has 'staff:invite' permission
    ├─ Create StaffInvitation (status: pending)
    ├─ Send email with invitation link + token
    └─ Audit log: "Staff invitation created"

Invitee → GET /api/staff/invite/accept?token=xxx
    │
    ├─ Hash token, lookup by hash
    ├─ Validate: not expired, status = pending
    ├─ Redirect to registration form (pre-filled email)
    └─ Create Identity + StaffMember profile

    POST /api/staff/invite/complete {token, password, name}
    │
    ├─ Create Identity (type: LOCAL)
    ├─ Create StaffMember profile
    ├─ Assign pre-defined roles
    ├─ Mark invitation accepted
    └─ Audit log: "Staff member joined"
```

### 5.4 Enterprise Examples

| Platform | Invitation TTL | Revocation | Re-invite | Pre-assigned Roles |
|----------|---------------|------------|-----------|-------------------|
| Stripe | 10 days | Yes | Yes | Yes |
| Shopify | 7 days | Yes | Yes | Yes (permissions) |
| Auth0 | Configurable | Yes | Yes | Yes (roles + orgs) |
| Slack | 30 days | Yes | Yes | Yes (channels) |
| GitHub | 7 days | Yes | Yes | Yes (team + role) |

---

## 6. RBAC & Permission Models

### 6.1 NIST RBAC Standard

NIST определяет 4 уровня RBAC:

| Уровень | Описание |
|---------|----------|
| **Core RBAC** | Users, Roles, Permissions, Sessions. Базовое назначение |
| **Hierarchical RBAC** | Role inheritance (senior role наследует permissions junior role) |
| **Static SoD** | Запрет на назначение конфликтующих ролей одному user |
| **Dynamic SoD** | Запрет на активацию конфликтующих ролей в одной session |

Организации обычно начинают с 3 категорий: **Administrators**, **Specialists/Expert Users**, **End Users**.

**Наш текущий RBAC (Identity module)** реализует Core RBAC + элементы Dynamic SoD (activated_roles per session).

**Источники:** [NIST RBAC Model](https://csrc.nist.gov/projects/role-based-access-control), [NIST RBAC Standard Draft](https://csrc.nist.gov/csrc/media/projects/role-based-access-control/documents/rbac-std-draft.pdf)

### 6.2 Multi-Type User RBAC

Для разделения Customer и Staff в RBAC:

```
System Roles (is_system=True, cannot be deleted):
├── customer              → permissions: [orders:create, orders:read_own, ...]
└── staff                 → permissions: [admin:access]
    ├── staff_operator    → permissions: [orders:read, orders:update, ...]
    ├── staff_manager     → permissions: [orders:*, products:*, users:read, ...]
    └── staff_admin       → permissions: [*:*]
```

**Правила:**
- Customer НЕ МОЖЕТ иметь staff-роли (Static SoD)
- Staff МОЖЕТ иметь только staff-роли
- Identity.type или User.user_type определяет допустимый набор ролей
- При создании Customer автоматически назначается системная роль `customer`
- При принятии Staff invitation автоматически назначаются pre-defined roles

### 6.3 Permission Inheritance

В нашей системе permissions уже имеют формат `resource:action`. Для user type separation:

```
# Customer permissions (implicit, через роль customer)
orders:create           # создание заказов
orders:read_own         # просмотр своих заказов
profile:read            # просмотр профиля
profile:update          # обновление профиля
referrals:read          # просмотр рефералов
referrals:share         # шаринг реферального кода

# Staff permissions (через staff-роли)
admin:access            # доступ к admin panel
orders:read             # просмотр всех заказов
orders:update           # обновление заказов
products:create         # создание товаров
products:update         # обновление товаров
users:read              # просмотр пользователей
staff:invite            # приглашение staff
roles:manage            # управление ролями
```

### 6.4 Session-Based vs Identity-Based Permissions

Наша реализация использует **Session-Based** (NIST Dynamic RBAC):
- `Session.activated_roles` — список ролей, активированных для текущей сессии
- Permissions вычисляются на основе activated roles, не всех ролей identity
- Это позволяет "step-up" authentication (активировать admin-роль только после повторной аутентификации)

---

## 7. Security & Compliance

### 7.1 GDPR Considerations

**Ключевое различие правовых оснований:**

| Аспект | Staff (Employees) | Customers |
|--------|-------------------|-----------|
| **Правовое основание** | Legitimate Interest / Contract | Consent |
| **DSAR обязательства** | Да | Да |
| **Right to be forgotten** | Ограниченно (трудовое право) | Полное |
| **Retention period** | Определяется трудовым законодательством | Определяется согласием |
| **Data minimization** | Только для рабочих процессов | Только для заявленных целей |

**Архитектурные импликации:**
- Разделение таблиц Customer и Staff упрощает GDPR compliance
- `User.anonymize()` (уже реализован) — разное поведение для Customer и Staff
- Audit logs для Staff действий должны храниться отдельно и дольше
- Customer data export (DSAR) — только customer-specific данные

**Источники:** [GDPR Employee Data](https://www.dickinson-wright.com/news-alerts/the-gdpr-covers-employee-hr-data-and-tricky), [GDPR HR Guide](https://www.redactable.com/blog/gdpr-for-human-resources-what-to-know-for-employee-data)

### 7.2 Audit Logging

**Рекомендуемая структура audit log:**

```python
@dataclass
class AuditLogEntry:
    id: uuid.UUID
    actor_id: uuid.UUID          # кто выполнил действие
    actor_type: str              # 'staff' | 'system' | 'customer'
    action: str                  # 'staff.invited' | 'order.updated' | ...
    target_type: str             # 'staff_invitation' | 'order' | ...
    target_id: str               # ID целевого объекта
    metadata: dict               # дополнительные данные
    ip_address: str
    user_agent: str
    timestamp: datetime
```

**Что логировать для Staff:**
- Все CRUD операции с бизнес-данными
- Приглашения и управление staff
- Изменения ролей и permissions
- Login/logout/session events
- Доступ к PII данным customers

**Retention:** 90 дней online, 1-3 года архив (SIEM-compatible export).

**Источники:** [WorkOS Audit Logs Guide](https://workos.com/blog/the-developers-guide-to-audit-logs-siem), [Audit Log Best Practices](https://www.fortra.com/blog/audit-log-best-practices-security-compliance)

### 7.3 Session Management

**Различия для Staff и Customer sessions:**

| Параметр | Staff | Customer |
|----------|-------|----------|
| **Idle timeout** | 15-30 min | 30-60 min |
| **Absolute timeout** | 8 hours | 30 days |
| **Refresh token TTL** | 7 days | 30 days |
| **Concurrent sessions** | 1-3 (alert on new) | Unlimited |
| **IP binding** | Recommended | Optional |
| **MFA** | Required for admin ops | Optional |
| **Session monitoring** | Active monitoring | Basic |

**Best practices:**
- Regenerate session ID после login и privilege escalation
- Secure + HttpOnly + SameSite cookies
- Sliding expiry для активных сессий
- Impossible travel detection для Staff
- Force logout on password change

**Источники:** [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), [WorkOS Session Best Practices](https://workos.com/blog/session-management-best-practices)

### 7.4 Data Segregation

**Принцип least privilege:**
- Staff видит только данные, необходимые для их роли
- Customer данные недоступны staff без явного permission
- PII (имя, телефон, адрес) логируется при доступе staff
- Financial данные (платёжные карты) недоступны staff, только через payment provider

---

## 8. Professional Implementations

### 8.1 Django's Approach

**Модель:** `AbstractUser` с `is_staff` boolean flag.

**Pros:**
- Простота — один User model для всего
- Встроенная интеграция с Django Admin
- Широко используется, хорошо протестирована

**Cons:**
- `is_staff` — ["biggest wart"](https://forum.djangoproject.com/t/understanding-of-user-is-staff-field/35838) в Django's permission системе
- Смешивание concerns: аутентификация + авторизация + профиль в одной модели
- [Обсуждение deprecation](https://groups.google.com/g/django-developers/c/J9yttc7WmJU) `is_staff`, `is_superuser`, `is_active`
- Нет type-specific атрибутов без доп. таблиц
- [django-staff package](https://github.com/callowayproject/django-staff) был создан именно для решения проблемы хранения разных данных для staff

### 8.2 Laravel's Multi-Guard

**Модель:** Отдельные Eloquent models + guards для каждого типа пользователя.

```php
// config/auth.php
'guards' => [
    'web' => ['driver' => 'session', 'provider' => 'users'],
    'admin' => ['driver' => 'session', 'provider' => 'admins'],
],
'providers' => [
    'users' => ['driver' => 'eloquent', 'model' => User::class],
    'admins' => ['driver' => 'eloquent', 'model' => Admin::class],
]
```

**Pros:**
- Полная изоляция authentication flows
- Разные таблицы, разные модели
- Middleware per guard для route protection
- Раздельные login/registration pages

**Cons:**
- Дублирование auth логики
- Сложнее shared features (если user может быть и customer, и admin)
- Больше кода для поддержки

**Источники:** [Laravel Multi-Guard](https://medium.com/@koriyapankaj007/creating-multi-auth-in-laravel-11-with-separate-admin-table-and-guards-9c438c11c0e2), [Laravel Guards Tutorial](https://pusher.com/tutorials/multiple-authentication-guards-laravel/)

### 8.3 Modern Python/FastAPI Patterns

**FastAPI Users library:**
- Extensible base User model
- Ready-to-use register/login/password reset routes
- OAuth2 social login support
- Multiple authentication backends (cookie + JWT)
- НО: один User model, разделение через roles/permissions

**Multi-tenant FastAPI (2026):**
- Dependency injection для tenant context
- `tenant_id` resolve в middleware
- Separate service/repository layers per tenant
- Role-based endpoint protection через dependencies

**Рекомендация для нашего стека:**
Наша архитектура (Dishka DI + CQRS + separate bounded contexts) уже лучше, чем FastAPI Users. Нужно расширить User bounded context для поддержки Customer/Staff.

**Источники:** [FastAPI Users](https://github.com/fastapi-users/fastapi-users), [FastAPI Multi-Tenant](https://blog.greeden.me/en/2026/03/10/introduction-to-multi-tenant-design-with-fastapi-practical-patterns-for-tenant-isolation-authorization-database-strategy-and-audit-logs/)

### 8.4 Open-Source E-commerce Solutions Summary

| Platform | Language | Staff/Customer Separation | Approach |
|----------|----------|--------------------------|----------|
| **Saleor** | Python/Django | `is_staff` flag | Single table + discriminator |
| **Medusa** | Node.js | Separate modules | User Module (admin) + Customer Module |
| **Spree** | Ruby/Rails | Roles (`admin`/`user`) | Single table + roles |
| **Sylius** | PHP/Symfony | Separate entities | AdminUser + ShopUser |
| **Bagisto** | PHP/Laravel | Multi-guard | Separate tables + guards |
| **Alokai (Vue Storefront)** | Node.js | API separation | Different API endpoints |

---

## 9. Recommendations for Our Platform

### 9.1 Recommended Architecture

На основе анализа 15+ платформ и enterprise решений, рекомендуется **гибридный подход**:

```
Identity BC (аутентификация — без изменений)
├── Identity (aggregate root) — единая для всех
├── LocalCredentials — email/password
├── Session — с activated_roles
├── Role — с системными ролями customer/staff
└── Permission — resource:action

User BC (расширить текущий)
├── Customer (aggregate root) — NEW
│   ├── profile data (name, phone, email)
│   ├── referral_code
│   ├── referred_by
│   ├── loyalty_tier
│   └── preferences
├── StaffMember (aggregate root) — NEW
│   ├── profile data (name, position)
│   ├── department
│   ├── invited_by
│   └── invitation_accepted_at
└── StaffInvitation (aggregate) — NEW
    ├── email, token_hash
    ├── pre-assigned role_ids
    ├── status lifecycle
    └── expiration

Referral BC (новый bounded context — опционально)
├── ReferralProgram (aggregate root)
├── Referral (entity)
└── ReferralReward (entity)
```

### 9.2 Domain Model Design

**Изменения в Identity BC:**
```python
# value_objects.py — добавить
class UserCategory(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    STAFF = "STAFF"
```

**Новые entities в User BC:**
```python
# Заменяет текущий User aggregate
@dataclass
class Customer(AggregateRoot):
    id: uuid.UUID  # == identity.id
    profile_email: str | None
    first_name: str
    last_name: str
    phone: str | None
    referral_code: str  # auto-generated
    referred_by: uuid.UUID | None  # customer_id
    loyalty_tier: str  # bronze | silver | gold | platinum
    created_at: datetime
    updated_at: datetime

@dataclass
class StaffMember(AggregateRoot):
    id: uuid.UUID  # == identity.id
    first_name: str
    last_name: str
    position: str | None
    department: str | None
    invited_by: uuid.UUID  # staff_member_id
    invitation_accepted_at: datetime
    created_at: datetime
    updated_at: datetime

@dataclass
class StaffInvitation(AggregateRoot):
    id: uuid.UUID
    email: str
    token_hash: str
    invited_by: uuid.UUID
    role_ids: list[uuid.UUID]
    status: str  # pending | accepted | expired | revoked
    expires_at: datetime
    accepted_at: datetime | None
    created_at: datetime
```

### 9.3 Migration Strategy

**Фаза 1: Подготовка (неделя 1)**
1. Добавить `user_category` field в Identity или отдельную mapping-таблицу
2. Создать системные роли `customer` и `staff`
3. Добавить `StaffInvitation` aggregate
4. Миграция текущих User → Customer (все текущие пользователи — customers)

**Фаза 2: Staff (неделя 2)**
1. Реализовать `StaffMember` aggregate + repository
2. Реализовать Staff Invitation flow (command handlers)
3. Добавить admin endpoints для staff management
4. Audit logging для staff actions

**Фаза 3: Referral (неделя 3)**
1. Добавить `referral_code` к Customer
2. Реализовать referral tracking
3. Domain events: `CustomerRegistered` → `GenerateReferralCode`
4. Domain events: `OrderCompleted` → `CheckReferralCompletion`

**Фаза 4: Session Management (неделя 4)**
1. Разные session policies для Customer/Staff
2. Stricter timeouts для Staff
3. Concurrent session limits для Staff
4. MFA support (опционально)

### 9.4 Implementation Priorities

| Приоритет | Задача | Effort | Impact |
|-----------|--------|--------|--------|
| **P0** | Customer/Staff discriminator + system roles | 3 дня | Высокий |
| **P0** | StaffInvitation flow | 3 дня | Высокий |
| **P1** | StaffMember aggregate + admin endpoints | 2 дня | Высокий |
| **P1** | Customer aggregate (refactor User) | 2 дня | Средний |
| **P2** | Referral code generation + tracking | 3 дня | Средний |
| **P2** | Audit logging для Staff | 2 дня | Средний |
| **P3** | Session policy differentiation | 2 дня | Низкий |
| **P3** | Referral rewards system | 3 дня | Низкий |

---

## 10. References & Sources

### Market Leaders
- [Shopify Staff vs Collaborator Accounts](https://www.hulkapps.com/blogs/shopify-hub/navigating-the-flexibility-of-shopify-collaborator-vs-staff-accounts-a-comprehensive-guide)
- [Shopify New Customer Accounts Migration](https://www.revize.app/blog/shopify-new-customer-accounts-migration-guide-deadlines)
- [Shopify Staff Permission Levels](https://www.saasant.com/blog/staff-user-permission-levels-in-shopify/)
- [Stripe User Roles](https://docs.stripe.com/get-started/account/teams/roles)
- [Stripe Team Management](https://docs.stripe.com/get-started/account/orgs/team)
- [Stripe New Roles Blog](https://stripe.com/blog/new-roles-and-permissions-in-the-dashboard)
- [Stripe Invite Team Members](https://support.stripe.com/questions/invite-team-members-or-developers-to-access-your-stripe-account)
- [Saleor GitHub — account/models.py](https://github.com/saleor/saleor/blob/main/saleor/account/models.py)
- [Saleor Architecture](https://docs.saleor.io/docs/3.x/overview/architecture)
- [Medusa Users Module](https://docs.medusajs.com/v1/modules/users)
- [Medusa Customers Module](https://docs.medusajs.com/v1/modules/customers/overview)
- [Medusa Architecture](https://docs.medusajs.com/learn/introduction/architecture)
- [Spree Commerce Permissions](https://spreecommerce.org/docs/developer/customization/permissions)
- [Spree Architecture](https://docs.spreecommerce.org/developer/core-concepts/architecture)

### Auth & IAM
- [Auth0 Multi-Tenant Best Practices](https://auth0.com/docs/get-started/auth0-overview/create-tenants/multi-tenant-apps-best-practices)
- [Auth0 B2B with Organizations](https://auth0.com/blog/using-auth0-for-b2b-multi-and-single-tenant-saas-solutions/)
- [Clerk Organizations](https://clerk.com/docs/guides/organizations/overview)
- [Clerk RBAC](https://clerk.com/docs/guides/organizations/control-access/roles-and-permissions)
- [WorkOS Directory Sync](https://workos.com/docs/directory-sync)
- [WorkOS Organizations](https://workos.com/blog/model-your-b2b-saas-with-organizations)
- [Keycloak Server Admin Guide](https://www.keycloak.org/docs/latest/server_admin/index.html)
- [Keycloak Realms](https://documentation.cloud-iam.com/resources/keycloak-realm.html)
- [Azure AD B2C Overview](https://learn.microsoft.com/en-us/azure/active-directory-b2c/overview)
- [Azure AD B2B vs B2C](https://kocho.co.uk/blog/azure-ad-b2b-b2c-differences-external-access/)
- [AWS Cognito Groups](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-user-groups.html)
- [AWS Cognito Best Practices](https://reintech.io/blog/structuring-aws-cognito-user-pools)
- [Okta User Types](https://help.okta.com/en-us/content/topics/users-groups-profiles/usgp-usertypes-about.htm)
- [Okta Universal Directory](https://developer.okta.com/docs/concepts/universal-directory/)
- [FusionAuth Tenants](https://fusionauth.io/docs/get-started/core-concepts/tenants)
- [FusionAuth Multi-Tenant](https://fusionauth.io/docs/extend/examples/multi-tenant)

### Architecture Patterns
- [DDD Bounded Contexts — Martin Fowler](https://martinfowler.com/bliki/BoundedContext.html)
- [Modeling Shared Entities Across Bounded Contexts](https://dev.to/aws-builders/modeling-shared-entities-across-bounded-contexts-in-domain-driven-design-5hih)
- [DDD vs Clean Architecture — Khalil Stemmler](https://khalilstemmler.com/articles/software-design-architecture/domain-driven-design-vs-clean-architecture/)
- [Django User Model is_staff Discussion](https://forum.djangoproject.com/t/understanding-of-user-is-staff-field/35838)
- [Django is_staff Deprecation Discussion](https://groups.google.com/g/django-developers/c/J9yttc7WmJU)
- [django-staff Package](https://github.com/callowayproject/django-staff)
- [Laravel Multi-Guard Authentication](https://medium.com/@koriyapankaj007/creating-multi-auth-in-laravel-11-with-separate-admin-table-and-guards-9c438c11c0e2)
- [FastAPI Users](https://github.com/fastapi-users/fastapi-users)
- [FastAPI Multi-Tenant Design 2026](https://blog.greeden.me/en/2026/03/10/introduction-to-multi-tenant-design-with-fastapi-practical-patterns-for-tenant-isolation-authorization-database-strategy-and-audit-logs/)

### Referral Systems
- [System Design of a Referral System](https://dev.to/vaib215/system-design-of-a-referral-system-4hik)
- [Multi-Level Referral System DB Design](https://www.coderbased.com/p/sql-db-design-multi-level-referral-system)
- [Referral Code Generation Architecture](https://medium.com/@siddhusingh/referral-code-generation-architecture-contention-free-scalable-approach-68ea44ee5fb0)
- [Open Loyalty Referral Software](https://www.openloyalty.io/product/referral-program-software)
- [Referral Code Best Practices](https://referralrock.com/blog/referral-code-example/)

### Security & Compliance
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [WorkOS Session Management Best Practices](https://workos.com/blog/session-management-best-practices)
- [WorkOS Audit Logs Guide](https://workos.com/blog/the-developers-guide-to-audit-logs-siem)
- [NIST RBAC Model](https://csrc.nist.gov/projects/role-based-access-control)
- [NIST RBAC Standard](https://csrc.nist.gov/csrc/media/projects/role-based-access-control/documents/rbac-std-draft.pdf)
- [GDPR Employee Data](https://www.dickinson-wright.com/news-alerts/the-gdpr-covers-employee-hr-data-and-tricky)
- [GDPR HR Guide](https://www.redactable.com/blog/gdpr-for-human-resources-what-to-know-for-employee-data)
- [Audit Log Best Practices](https://www.fortra.com/blog/audit-log-best-practices-security-compliance)
- [NIST SP 800-92 Log Management](https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-92.pdf)
