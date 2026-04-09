# 1. Структура папок: глубокое исследование организации Next.js 15+ проекта

> Расширенное исследование на основе официальной документации Next.js, реальных open-source
> enterprise-проектов (Cal.com, Makerkit, Blazity), рекомендаций Vercel и консенсуса сообщества 2025-2026.

---

## 1.1 Корневой уровень проекта

### Полная структура с объяснением каждого элемента

```
my-app/
├── src/                        # Весь исходный код приложения
│   ├── app/                    # Next.js App Router (файловая маршрутизация)
│   ├── components/             # Переиспользуемые UI-компоненты
│   ├── features/               # Бизнес-фичи (feature modules)
│   ├── lib/                    # Утилиты, клиенты API, хелперы
│   ├── hooks/                  # Глобальные кастомные React-хуки
│   ├── actions/                # Server Actions (глобальные)
│   ├── services/               # Серверная бизнес-логика, работа с БД
│   ├── schemas/                # Zod-схемы валидации
│   ├── types/                  # Глобальные TypeScript-типы
│   ├── utils/                  # Чистые утилитарные функции
│   ├── config/                 # Конфигурация приложения (env, feature flags)
│   ├── constants/              # Константы и перечисления
│   ├── stores/                 # Zustand/Jotai stores (клиентский стейт)
│   └── middleware.ts           # Next.js Middleware (авторизация, i18n, redirects)
│
├── public/                     # Статические файлы (favicon, robots.txt, images)
│   ├── favicon.ico
│   ├── robots.txt
│   ├── sitemap.xml
│   └── images/
│       └── og-default.png
│
├── tests/                      # E2E-тесты (Playwright)
│   ├── e2e/
│   │   ├── auth.spec.ts
│   │   └── dashboard.spec.ts
│   └── fixtures/
│       └── test-data.ts
│
├── next.config.ts              # Конфигурация Next.js
├── tsconfig.json               # TypeScript конфигурация
├── eslint.config.mjs           # ESLint flat config
├── postcss.config.mjs          # PostCSS (для Tailwind CSS)
├── tailwind.config.ts          # Tailwind CSS конфигурация
├── vitest.config.ts            # Vitest конфигурация (unit-тесты)
├── playwright.config.ts        # Playwright конфигурация (E2E)
├── .env.example                # Шаблон переменных окружения
├── .env.local                  # Локальные переменные (в .gitignore!)
├── .prettierrc                 # Prettier конфигурация
├── .gitignore
├── package.json
└── pnpm-lock.yaml              # Lock-файл (pnpm -- стандарт enterprise 2025)
```

### Дебаты: `src/` vs корневая `app/`

Одна из самых обсуждаемых тем в сообществе Next.js -- нужна ли директория `src/`.

**Официальная позиция Next.js:** поддерживает оба подхода. Документация говорит:

> "Next.js supports the common pattern of placing application code under the src folder,
> which separates application code from project configuration files."

Примечательно, что `create-next-app` **чередует** значение по умолчанию при запросе "Use src/ directory?" между
Yes и No в разных версиях. Это подтверждает отсутствие жесткого официального предпочтения.

**Консенсус сообщества 2025-2026: `src/` рекомендуется для enterprise.** Причины:

| Аспект                     | С `src/`                      | Без `src/` (корневая `app/`)     |
| -------------------------- | ----------------------------- | -------------------------------- |
| **Чистота корня**          | Конфиг-файлы отделены от кода | 15+ конфиг-файлов смешаны с app/ |
| **IDE-навигация**          | Один корень для поиска кода   | Нужно фильтровать конфиги        |
| **Git diff**               | Изменения кода сгруппированы  | Смешаны с конфигурационными      |
| **Монорепо-совместимость** | Легко выделить в пакет        | Требует рефакторинга             |
| **Middleware**             | `src/middleware.ts`           | `middleware.ts` в корне          |
| **Использование в 2025**   | ~70% enterprise-проектов      | ~30%, чаще для мелких проектов   |

**Правило:** если в корне проекта больше 10 конфигурационных файлов (а в enterprise-проекте их всегда
больше) -- `src/` практически обязателен для сохранения навигируемости.

**Важно о `middleware.ts`:** файл middleware должен располагаться на том же уровне, что и
директория `app/`. Если используете `src/app/`, то middleware -- это `src/middleware.ts`.
Если `app/` в корне -- то `middleware.ts` в корне. Смешивать нельзя.

### Что живет в корне, а что в `src/`

**Всегда в корне проекта (НЕ в src/):**

- `public/` -- статические файлы
- `tests/` или `e2e/` -- E2E-тесты Playwright (см. секцию про колокацию)
- Все конфигурационные файлы: `next.config.ts`, `tsconfig.json`, `eslint.config.mjs`, и т.д.
- `.env*` файлы
- `package.json`, lock-файлы

**Всегда внутри `src/`:**

- `app/` -- маршруты Next.js
- `components/`, `features/`, `lib/`, `hooks/` и вся бизнес-логика
- `middleware.ts`

### Описание каждой директории внутри `src/`

| Директория    | Назначение                                                                  | Почему выделена отдельно                |
| ------------- | --------------------------------------------------------------------------- | --------------------------------------- |
| `app/`        | Файловый роутер Next.js: layouts, pages, loading, error                     | Конвенция Next.js, не менять            |
| `components/` | Переиспользуемые UI-компоненты без бизнес-логики                            | Shared UI, не привязан к фиче           |
| `features/`   | Бизнес-фичи: auth, billing, users -- со своими компонентами, хуками, типами | Инкапсуляция домена                     |
| `lib/`        | Инициализация клиентов (Prisma, Redis, Supabase), обертки над API           | Инфраструктурный код                    |
| `hooks/`      | Глобальные React-хуки: `useMediaQuery`, `useDebounce`, `useLocalStorage`    | Не привязаны к конкретной фиче          |
| `actions/`    | Server Actions общего назначения (не привязанные к одной фиче)              | Серверная логика с `"use server"`       |
| `services/`   | Серверная бизнес-логика, DAL (Data Access Layer), работа с БД               | Server-only, не импортировать на клиент |
| `schemas/`    | Zod-схемы валидации форм и API                                              | Используются и на сервере, и на клиенте |
| `types/`      | Глобальные TypeScript-типы и интерфейсы                                     | Shared между клиентом и сервером        |
| `utils/`      | Чистые функции: `formatDate()`, `cn()`, `slugify()`                         | Без side-effects, легко тестировать     |
| `config/`     | Типизированный доступ к env-переменным, feature flags                       | Единая точка конфигурации               |
| `constants/`  | Магические значения: роли, статусы, лимиты                                  | Убирает magic numbers из кода           |
| `stores/`     | Zustand/Jotai stores для клиентского состояния                              | Клиентский стейт отдельно от серверного |

---

## 1.2 Детальная структура `src/app/`

### Полная структура с каждым типом файла

```
src/app/
├── layout.tsx                  # Корневой layout (обязательный)
│                               #   - <html>, <body>, шрифты, метаданные
│                               #   - Providers: Theme, QueryClient, Toaster
├── page.tsx                    # Главная страница (/)
├── not-found.tsx               # Глобальная 404 страница
├── error.tsx                   # Глобальный Error Boundary (client component)
├── global-error.tsx            # Error Boundary для root layout
├── loading.tsx                 # Глобальный loading (Suspense fallback)
├── globals.css                 # Глобальные стили + Tailwind directives
├── manifest.ts                 # PWA Web App Manifest (опционально)
├── sitemap.ts                  # Динамическая sitemap генерация
├── robots.ts                   # Динамические правила robots.txt
├── opengraph-image.tsx         # OG-изображение по умолчанию (ImageResponse)
│
├── (marketing)/                # === Route Group: публичные страницы ===
│   ├── layout.tsx              # Layout: Header + Footer, без sidebar
│   ├── page.tsx                # / (маркетинговый лендинг)
│   ├── about/
│   │   └── page.tsx            # /about
│   ├── pricing/
│   │   ├── page.tsx            # /pricing
│   │   └── _components/        # Приватная папка: компоненты только для pricing
│   │       ├── pricing-card.tsx
│   │       └── pricing-toggle.tsx
│   ├── blog/
│   │   ├── page.tsx            # /blog (список статей)
│   │   └── [slug]/
│   │       ├── page.tsx        # /blog/:slug (статья)
│   │       └── opengraph-image.tsx  # OG-изображение для каждой статьи
│   └── contact/
│       ├── page.tsx            # /contact
│       └── _actions/           # Server Actions для контактной формы
│           └── submit-contact.ts
│
├── (dashboard)/                # === Route Group: панель управления ===
│   ├── layout.tsx              # Layout: Sidebar + Topbar + main content area
│   ├── dashboard/
│   │   ├── page.tsx            # /dashboard
│   │   ├── loading.tsx         # Skeleton для dashboard
│   │   ├── error.tsx           # Error boundary для dashboard
│   │   ├── @analytics/         # Parallel Route: виджет аналитики
│   │   │   ├── page.tsx
│   │   │   ├── loading.tsx     # Свой loading для аналитики
│   │   │   └── default.tsx     # Fallback при soft navigation
│   │   └── @notifications/     # Parallel Route: уведомления
│   │       ├── page.tsx
│   │       └── default.tsx
│   ├── settings/
│   │   ├── page.tsx            # /settings (редирект на /settings/profile)
│   │   ├── layout.tsx          # Вложенный layout: табы настроек
│   │   ├── profile/
│   │   │   └── page.tsx        # /settings/profile
│   │   ├── billing/
│   │   │   └── page.tsx        # /settings/billing
│   │   └── team/
│   │       └── page.tsx        # /settings/team
│   └── users/
│       ├── page.tsx            # /users (таблица пользователей)
│       ├── loading.tsx         # Skeleton с data-table shimmer
│       ├── [id]/
│       │   ├── page.tsx        # /users/:id (профиль пользователя)
│       │   ├── edit/
│       │   │   └── page.tsx    # /users/:id/edit
│       │   └── not-found.tsx   # 404 для конкретного пользователя
│       └── _components/        # Компоненты, специфичные для users
│           ├── user-table.tsx
│           ├── user-filters.tsx
│           └── columns.tsx     # Определение колонок data-table
│
├── (auth)/                     # === Route Group: аутентификация ===
│   ├── layout.tsx              # Минимальный layout: центрированная карточка
│   ├── login/
│   │   └── page.tsx            # /login
│   ├── register/
│   │   └── page.tsx            # /register
│   ├── forgot-password/
│   │   └── page.tsx            # /forgot-password
│   ├── verify-email/
│   │   └── page.tsx            # /verify-email
│   └── _components/            # Общие компоненты auth-группы
│       ├── auth-card.tsx
│       ├── social-buttons.tsx
│       └── oauth-callback.tsx
│
└── api/                        # === Route Handlers (REST API) ===
    ├── webhooks/
    │   ├── stripe/
    │   │   └── route.ts        # POST /api/webhooks/stripe
    │   └── clerk/
    │       └── route.ts        # POST /api/webhooks/clerk
    ├── upload/
    │   └── route.ts            # POST /api/upload
    └── health/
        └── route.ts            # GET /api/health (Kubernetes readiness probe)
```

### Приватные папки (`_folder`) -- ключевая конвенция App Router

Папки с префиксом `_` (underscore) **исключаются из файловой маршрутизации**. Это официальная
конвенция Next.js для колокации (colocation) -- размещения связанных файлов рядом с маршрутами.

```
# Эти файлы НЕ станут маршрутами:
src/app/(dashboard)/users/_components/user-table.tsx    # Не роут
src/app/(dashboard)/users/_lib/format-user.ts           # Не роут
src/app/(dashboard)/users/_actions/update-user.ts       # Не роут

# А эти -- СТАНУТ:
src/app/(dashboard)/users/page.tsx                      # /users
src/app/(dashboard)/users/[id]/page.tsx                 # /users/:id
```

**Когда использовать `_components/` внутри `app/`:**

- Компонент используется **только на этой странице** или в этой route group
- Это presentation-логика, специфичная для маршрута (колонки таблицы, фильтры)
- Хотите держать связанный код рядом, а не в глобальном `src/components/`

**Когда НЕ использовать:**

- Компонент переиспользуется в 2+ местах -- переместите в `src/components/`
- Компонент содержит бизнес-логику -- переместите в `src/features/`

### Server Actions: колокация внутри `app/` vs `src/actions/`

Server Actions в Next.js 15+ могут располагаться **где угодно**, если содержат директиву `"use server"`.
Два основных подхода:

**Подход 1: Колокация с маршрутом (рекомендуется для route-specific actions)**

```
src/app/(dashboard)/users/
├── page.tsx
├── _actions/
│   ├── create-user.ts          # "use server" -- создание пользователя
│   └── delete-user.ts          # "use server" -- удаление пользователя
└── _components/
    └── user-form.tsx           # Импортирует из ../_actions/create-user
```

**Подход 2: Централизованный `src/actions/` (для shared actions)**

```
src/actions/
├── auth.ts                     # login(), logout(), refreshToken()
├── upload.ts                   # uploadFile(), deleteFile()
└── notifications.ts            # markAsRead(), sendNotification()
```

**Консенсус 2025:** гибридный подход. Route-specific actions живут в `_actions/` внутри маршрута,
shared actions -- в `src/actions/`. Это соответствует рекомендации из GitHub Discussion #55908:
"Colocating Server Actions with their routes improves organization compared to centralizing all actions."

### Файловые конвенции App Router -- полный справочник

| Файл                  | Назначение                                     | Server/Client            |
| --------------------- | ---------------------------------------------- | ------------------------ |
| `layout.tsx`          | Общий UI для сегмента и дочерних маршрутов     | Server (по умолчанию)    |
| `page.tsx`            | UI маршрута, делает маршрут публично доступным | Server (по умолчанию)    |
| `loading.tsx`         | Suspense fallback для сегмента                 | Server                   |
| `error.tsx`           | Error Boundary для сегмента                    | **Client** (обязательно) |
| `global-error.tsx`    | Error Boundary для root layout                 | **Client** (обязательно) |
| `not-found.tsx`       | 404 страница для сегмента                      | Server                   |
| `route.ts`            | API endpoint (Route Handler)                   | Server                   |
| `template.tsx`        | Как layout, но пересоздается при навигации     | Server                   |
| `default.tsx`         | Fallback для Parallel Routes                   | Server                   |
| `opengraph-image.tsx` | OG-изображение (ImageResponse API)             | Server                   |
| `sitemap.ts`          | Динамическая sitemap                           | Server                   |
| `robots.ts`           | Динамические правила robots.txt                | Server                   |
| `manifest.ts`         | PWA Web App Manifest                           | Server                   |
| `middleware.ts`       | Перехват запросов (на уровне `src/`)           | Edge Runtime             |

---

## 1.3 Структура компонентов

### Детальная иерархия `src/components/`

```
src/components/
│
├── ui/                         # === Базовые UI-примитивы ===
│   │                           # Стиль: shadcn/ui (копируемые компоненты)
│   │                           # Правило: НЕТ бизнес-логики, только визуал
│   ├── button.tsx              # <Button variant="destructive" size="sm" />
│   ├── button.test.tsx         # Тест рядом с компонентом (колокация)
│   ├── input.tsx               # <Input type="email" placeholder="..." />
│   ├── textarea.tsx            # <Textarea rows={4} />
│   ├── label.tsx               # <Label htmlFor="email">Email</Label>
│   ├── select.tsx              # <Select> с <SelectTrigger>, <SelectContent>
│   ├── checkbox.tsx            # <Checkbox checked={...} onCheckedChange={...} />
│   ├── switch.tsx              # <Switch> для toggle
│   ├── dialog.tsx              # <Dialog> модальное окно
│   ├── sheet.tsx               # <Sheet> боковая панель
│   ├── dropdown-menu.tsx       # <DropdownMenu> контекстное меню
│   ├── popover.tsx             # <Popover> всплывающее окно
│   ├── tooltip.tsx             # <Tooltip> подсказка
│   ├── avatar.tsx              # <Avatar> с fallback инициалов
│   ├── badge.tsx               # <Badge variant="success">Active</Badge>
│   ├── card.tsx                # <Card> с <CardHeader>, <CardContent>
│   ├── separator.tsx           # <Separator> визуальный разделитель
│   ├── skeleton.tsx            # <Skeleton> плейсхолдер загрузки
│   ├── spinner.tsx             # <Spinner> индикатор загрузки
│   ├── data-table.tsx          # <DataTable> обертка над TanStack Table
│   ├── data-table-pagination.tsx
│   ├── data-table-toolbar.tsx
│   ├── form.tsx                # Обертка React Hook Form + shadcn
│   ├── sonner.tsx              # Toast-уведомления (Sonner)
│   └── calendar.tsx            # Календарь (date-picker)
│
├── layout/                     # === Компоненты лейаута ===
│   │                           # Определяют каркас страниц
│   ├── header.tsx              # Шапка сайта: навигация, лого, user menu
│   ├── header.test.tsx
│   ├── sidebar.tsx             # Боковая панель (dashboard layout)
│   ├── sidebar-nav.tsx         # Навигационные ссылки sidebar
│   ├── footer.tsx              # Подвал сайта
│   ├── mobile-nav.tsx          # Мобильная навигация (Sheet)
│   ├── breadcrumbs.tsx         # Хлебные крошки
│   └── theme-toggle.tsx        # Переключатель dark/light mode
│
├── shared/                     # === Составные компоненты общего назначения ===
│   │                           # Комбинируют UI-примитивы, но НЕ содержат бизнес-логики
│   ├── page-header.tsx         # Заголовок страницы + описание + actions
│   ├── empty-state.tsx         # Пустое состояние: иконка + текст + CTA
│   ├── error-boundary.tsx      # React Error Boundary (client component)
│   ├── confirm-dialog.tsx      # Диалог подтверждения действия
│   ├── file-upload.tsx         # Загрузка файлов с drag-and-drop
│   ├── search-input.tsx        # Поле поиска с debounce
│   ├── copy-button.tsx         # Кнопка "Скопировать" с toast
│   ├── status-badge.tsx        # Бейдж статуса: active/inactive/pending
│   └── loading-overlay.tsx     # Оверлей загрузки для секций
│
└── providers/                  # === Провайдеры (Client Components) ===
    │                           # "use client" -- оборачивают приложение
    ├── theme-provider.tsx      # next-themes ThemeProvider
    ├── query-provider.tsx      # TanStack Query QueryClientProvider
    ├── toast-provider.tsx      # Sonner Toaster
    └── analytics-provider.tsx  # PostHog / Vercel Analytics
```

### Почему именно такое разделение на `ui/`, `layout/`, `shared/`, `providers/`

**`ui/`** -- это ваш **design system**. Компоненты в `ui/` не знают о бизнес-логике приложения.
Они стилизованы, доступны (a11y), типизированы и могут быть перенесены в любой проект.
shadcn/ui по умолчанию устанавливает свои компоненты в `components/ui/` -- это стало
де-факто стандартом в экосистеме Next.js 2025.

**`layout/`** -- структурные компоненты, которые определяют **каркас страницы**. Они знают
о навигации и расположении элементов, но не о конкретных данных. Отличие от `ui/`:
кнопка -- это `ui/`, а sidebar с навигационными ссылками -- это `layout/`.

**`shared/`** -- **составные компоненты**, которые комбинируют несколько `ui/`-примитивов
в повторяемый паттерн. Например, `confirm-dialog.tsx` = `Dialog` + `Button` + текст.
Они не содержат бизнес-данных, но имеют определенный UX-паттерн.

**`providers/`** -- Client Components с `"use client"`, которые оборачивают дерево компонентов.
Выделены отдельно, потому что все они -- Client Components, и их набор стабилен.

### Правило зависимостей компонентов

```
providers/ --> может использовать: ui/, shared/
shared/    --> может использовать: ui/
layout/    --> может использовать: ui/, shared/
ui/        --> НЕ импортирует из layout/, shared/, providers/
```

Это правило можно enforced через `eslint-plugin-boundaries` (см. основной документ, секция 4.3).

---

## 1.4 Структура features (бизнес-фичи)

### Детальная структура feature-модуля

```
src/features/
│
├── auth/                       # === Фича: Аутентификация ===
│   ├── components/             # UI-компоненты фичи
│   │   ├── login-form.tsx      # Форма логина
│   │   ├── login-form.test.tsx # Тест формы (колокация)
│   │   ├── register-form.tsx   # Форма регистрации
│   │   ├── user-menu.tsx       # Выпадающее меню пользователя
│   │   ├── social-login.tsx    # Кнопки OAuth (Google, GitHub)
│   │   └── password-input.tsx  # Input с toggle видимости пароля
│   ├── hooks/                  # React-хуки фичи
│   │   ├── use-auth.ts         # useAuth() -- текущий пользователь, logout
│   │   ├── use-session.ts      # useSession() -- статус сессии
│   │   └── use-permissions.ts  # usePermissions() -- проверка прав
│   ├── actions/                # Server Actions фичи
│   │   ├── login.ts            # "use server" -- логин
│   │   ├── register.ts         # "use server" -- регистрация
│   │   ├── logout.ts           # "use server" -- выход
│   │   └── reset-password.ts   # "use server" -- сброс пароля
│   ├── schemas/                # Zod-схемы фичи
│   │   ├── login.schema.ts     # loginSchema = z.object({ email, password })
│   │   └── register.schema.ts  # registerSchema с подтверждением пароля
│   ├── services/               # Серверная бизнес-логика
│   │   ├── auth.service.ts     # createSession(), verifyToken()
│   │   └── email.service.ts    # sendVerificationEmail()
│   ├── types/                  # TypeScript-типы фичи
│   │   └── auth.types.ts       # User, Session, AuthState, LoginPayload
│   └── utils/                  # Утилиты фичи
│       ├── token.ts            # generateToken(), parseToken()
│       └── password.ts         # hashPassword(), comparePassword()
│
├── billing/                    # === Фича: Биллинг ===
│   ├── components/
│   │   ├── pricing-table.tsx   # Таблица тарифов
│   │   ├── subscription-card.tsx
│   │   ├── payment-form.tsx    # Форма оплаты (Stripe Elements)
│   │   ├── invoice-list.tsx    # Список счетов
│   │   └── usage-meter.tsx     # Индикатор использования
│   ├── hooks/
│   │   ├── use-subscription.ts # Текущая подписка пользователя
│   │   └── use-usage.ts       # Использование ресурсов
│   ├── actions/
│   │   ├── create-checkout.ts  # "use server" -- создание Stripe Checkout
│   │   ├── cancel-subscription.ts
│   │   └── update-plan.ts
│   ├── schemas/
│   │   └── billing.schema.ts   # Валидация платежных данных
│   ├── services/
│   │   ├── stripe.service.ts   # Обертка над Stripe SDK
│   │   └── webhook.service.ts  # Обработка Stripe webhooks
│   ├── types/
│   │   └── billing.types.ts    # Plan, Subscription, Invoice, Usage
│   └── constants/
│       └── plans.ts            # PLANS = [{ id: "free", ... }, { id: "pro", ... }]
│
├── users/                      # === Фича: Управление пользователями ===
│   ├── components/
│   │   ├── user-profile.tsx
│   │   ├── user-avatar.tsx
│   │   ├── user-settings-form.tsx
│   │   └── team-members-list.tsx
│   ├── hooks/
│   │   └── use-user.ts         # useUser(id) -- данные пользователя
│   ├── actions/
│   │   ├── update-profile.ts
│   │   └── invite-member.ts
│   ├── schemas/
│   │   ├── profile.schema.ts
│   │   └── invite.schema.ts
│   ├── services/
│   │   └── user.service.ts     # CRUD операции с пользователями
│   └── types/
│       └── user.types.ts       # UserProfile, UserRole, TeamMember
│
└── notifications/              # === Фича: Уведомления ===
    ├── components/
    │   ├── notification-bell.tsx
    │   ├── notification-list.tsx
    │   └── notification-item.tsx
    ├── hooks/
    │   └── use-notifications.ts
    ├── actions/
    │   └── mark-as-read.ts
    ├── services/
    │   └── notification.service.ts
    └── types/
        └── notification.types.ts
```

### Принцип: каждая фича -- мини-приложение

Каждая директория в `src/features/` -- это **самодостаточный модуль**. Он содержит все, что нужно
для работы фичи: от UI до серверной логики. Правила:

1. **Фича НЕ импортирует из другой фичи напрямую.** Если `billing` нужен `useAuth` из `auth`,
   сделайте хук глобальным (`src/hooks/use-auth.ts`) или используйте провайдер.

2. **Фича МОЖЕТ импортировать из глобальных слоев:**
   `src/components/ui/*`, `src/lib/*`, `src/hooks/*`, `src/types/*`, `src/utils/*`, `src/config/*`

3. **Маршрут (`src/app/`) импортирует из фичи, не наоборот:**

   ```typescript
   // src/app/(dashboard)/settings/billing/page.tsx
   import { PricingTable } from '@/features/billing/components/pricing-table';
   import { SubscriptionCard } from '@/features/billing/components/subscription-card';
   ```

4. **Компонент страницы -- тонкий клей:**
   Файл `page.tsx` в `src/app/` должен быть **тонким**: получить данные, передать в компоненты из features.
   Вся логика -- в features.

### Когда создавать новую фичу vs добавлять в существующую

| Сигнал                                    | Действие                               |
| ----------------------------------------- | -------------------------------------- |
| Новый бизнес-домен (платежи, уведомления) | Новая фича                             |
| Новый компонент для существующего домена  | Добавить в существующую фичу           |
| Компонент используется в 3+ фичах         | Переместить в `src/components/shared/` |
| Хук используется в 2+ фичах               | Переместить в `src/hooks/`             |
| Action используется в 2+ фичах            | Переместить в `src/actions/`           |

---

## 1.5 Организация Zod-схем (`src/schemas/` и `features/*/schemas/`)

### Почему отдельная директория для схем

Zod-схемы -- это **единый источник правды (Single Source of Truth)** для валидации данных.
Ключевое преимущество: одну схему можно использовать **и на клиенте (формы), и на сервере (actions/API)**,
исключая дублирование правил валидации.

```
src/schemas/                    # Глобальные схемы (не привязаны к фиче)
├── env.ts                      # Валидация переменных окружения при старте
├── common.ts                   # Переиспользуемые фрагменты: email, phone, url
└── pagination.ts               # Схема пагинации: { page, limit, sortBy, order }
```

### Пример: схема + Server Action + форма

```typescript
// src/features/auth/schemas/login.schema.ts
import { z } from 'zod';

export const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

export type LoginInput = z.infer<typeof loginSchema>;
```

```typescript
// src/features/auth/actions/login.ts
'use server';

import { loginSchema } from '../schemas/login.schema';

export async function loginAction(formData: FormData) {
  const parsed = loginSchema.safeParse({
    email: formData.get('email'),
    password: formData.get('password'),
  });

  if (!parsed.success) {
    return { error: parsed.error.flatten().fieldErrors };
  }
  // ... логика аутентификации
}
```

```typescript
// src/features/auth/components/login-form.tsx
'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { loginSchema, type LoginInput } from '../schemas/login.schema';
import { loginAction } from '../actions/login';

export function LoginForm() {
  const form = useForm<LoginInput>({
    resolver: zodResolver(loginSchema), // Та же схема на клиенте
  });
  // ...
}
```

**Главный принцип:** схема определяется **один раз** и используется в трех местах:

1. Server Action -- серверная валидация
2. React Hook Form -- клиентская валидация
3. TypeScript -- типизация через `z.infer<>`

### Валидация переменных окружения

Паттерн из T3 App и Makerkit -- валидация `process.env` при старте приложения:

```typescript
// src/schemas/env.ts
import { z } from 'zod';

const envSchema = z.object({
  DATABASE_URL: z.string().url(),
  NEXTAUTH_SECRET: z.string().min(32),
  STRIPE_SECRET_KEY: z.string().startsWith('sk_'),
  NEXT_PUBLIC_APP_URL: z.string().url(),
});

export const env = envSchema.parse(process.env);
// Если переменная отсутствует -- приложение упадет при старте, а не в runtime
```

---

## 1.6 Конвенции именования файлов

### kebab-case vs PascalCase -- окончательный ответ

**Консенсус 2025: kebab-case для файлов, PascalCase для экспортируемых компонентов.**

```
# Файлы -- kebab-case:
src/components/ui/button.tsx
src/components/ui/data-table.tsx
src/features/auth/components/login-form.tsx
src/hooks/use-media-query.ts
src/lib/supabase-client.ts

# Экспортируемые компоненты -- PascalCase:
export function Button() { ... }
export function DataTable() { ... }
export function LoginForm() { ... }
export function useMediaQuery() { ... }  // хуки -- camelCase с use-
```

**Почему kebab-case для файлов:**

| Причина                   | Объяснение                                                                                                                                                                                 |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Кросс-платформенность** | Linux (case-sensitive) и macOS/Windows (case-insensitive) одинаково работают с `user-profile.tsx`. Но `UserProfile.tsx` и `userprofile.tsx` -- разные файлы на Linux и одинаковые на macOS |
| **URL-совместимость**     | Next.js App Router использует имя папки как URL-сегмент. `/UserProfile` -- нестандартный URL                                                                                               |
| **Конвенция Next.js**     | Все файлы-конвенции App Router в kebab-case: `layout.tsx`, `not-found.tsx`, `loading.tsx`, `global-error.tsx`                                                                              |
| **shadcn/ui стандарт**    | shadcn/ui устанавливает компоненты как `button.tsx`, `data-table.tsx` -- это де-факто стандарт экосистемы                                                                                  |
| **Сортировка в IDE**      | `user-avatar.tsx`, `user-menu.tsx`, `user-profile.tsx` группируются рядом                                                                                                                  |

### Полная таблица конвенций именования

| Тип файла       | Конвенция                | Пример                               |
| --------------- | ------------------------ | ------------------------------------ |
| React-компонент | `kebab-case.tsx`         | `pricing-card.tsx`                   |
| React-хук       | `use-kebab-case.ts`      | `use-media-query.ts`                 |
| Server Action   | `kebab-case.ts`          | `create-checkout.ts`                 |
| Zod-схема       | `kebab-case.schema.ts`   | `login.schema.ts`                    |
| Сервис          | `kebab-case.service.ts`  | `stripe.service.ts`                  |
| Типы            | `kebab-case.types.ts`    | `billing.types.ts`                   |
| Утилита         | `kebab-case.ts`          | `format-date.ts`                     |
| Константы       | `kebab-case.ts`          | `http-status.ts`                     |
| Тест (unit)     | `kebab-case.test.ts(x)`  | `button.test.tsx`                    |
| Тест (E2E)      | `kebab-case.spec.ts`     | `auth.spec.ts`                       |
| Storybook       | `kebab-case.stories.tsx` | `button.stories.tsx`                 |
| CSS Module      | `kebab-case.module.css`  | `sidebar.module.css`                 |
| Конфиг Next.js  | `lowercase`              | `layout.tsx`, `page.tsx`, `route.ts` |

### Именование папок

| Тип папки             | Конвенция        | Пример                               |
| --------------------- | ---------------- | ------------------------------------ |
| Маршрут (URL-сегмент) | `kebab-case`     | `forgot-password/`, `user-settings/` |
| Route Group           | `(kebab-case)`   | `(marketing)/`, `(dashboard)/`       |
| Динамический сегмент  | `[camelCase]`    | `[userId]/`, `[slug]/`               |
| Catch-all сегмент     | `[...camelCase]` | `[...segments]/`                     |
| Parallel Route        | `@camelCase`     | `@analytics/`, `@notifications/`     |
| Приватная папка       | `_kebab-case`    | `_components/`, `_lib/`, `_actions/` |
| Обычная папка         | `kebab-case`     | `components/`, `features/`, `hooks/` |

---

## 1.7 Паттерны колокации: тесты рядом с кодом vs отдельная директория

### Два подхода к организации тестов

**Подход 1: Колокация (тесты рядом с компонентами)**

```
src/components/ui/
├── button.tsx
├── button.test.tsx             # Unit-тест рядом
├── button.stories.tsx          # Storybook рядом
├── input.tsx
├── input.test.tsx
└── input.stories.tsx

src/features/auth/
├── components/
│   ├── login-form.tsx
│   └── login-form.test.tsx
├── hooks/
│   ├── use-auth.ts
│   └── use-auth.test.ts
├── services/
│   ├── auth.service.ts
│   └── auth.service.test.ts
└── utils/
    ├── token.ts
    └── token.test.ts
```

**Подход 2: Отдельная директория `__tests__/`**

```
src/components/ui/
├── __tests__/
│   ├── button.test.tsx
│   └── input.test.tsx
├── button.tsx
└── input.tsx

# Или полностью отдельная корневая папка:
tests/
├── unit/
│   ├── components/
│   │   ├── button.test.tsx
│   │   └── input.test.tsx
│   └── features/
│       └── auth/
│           └── login-form.test.tsx
└── e2e/
    ├── auth.spec.ts
    └── dashboard.spec.ts
```

### Рекомендация 2025-2026: гибридный подход

| Тип тестов                 | Расположение                             | Обоснование                                                |
| -------------------------- | ---------------------------------------- | ---------------------------------------------------------- |
| **Unit-тесты** (Vitest)    | Рядом с файлом: `button.test.tsx`        | Легко найти, легко удалить вместе с компонентом            |
| **E2E-тесты** (Playwright) | `tests/e2e/` в корне проекта             | Тестируют пользовательские сценарии, а не отдельные модули |
| **Integration-тесты**      | `tests/integration/` или рядом с feature | Зависит от масштаба тестируемого модуля                    |
| **Test fixtures/mocks**    | `tests/fixtures/` или `tests/mocks/`     | Общие тестовые данные                                      |

**Почему колокация unit-тестов побеждает:**

1. **Удаление компонента = удаление теста.** Не нужно искать тест в другой папке.
2. **Code review.** Изменение компонента и теста видны в одном PR-diff.
3. **Навигация в IDE.** Файлы рядом в дереве -- переключение одним кликом.
4. **"Из глаз -- из ума".** Тесты в отдельной папке чаще забываются и устаревают.
5. **Next.js App Router поддерживает это:** файлы `.test.tsx` внутри `app/` **не становятся маршрутами**
   (только `page.tsx`, `route.ts`, `layout.tsx` и т.д. являются конвенциями маршрутизации).

**Конфигурация Vitest для колокации:**

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{ts,tsx}'], // Тесты внутри src/
    exclude: ['tests/e2e/**'], // E2E отдельно
    setupFiles: ['./tests/setup.ts'],
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
});
```

### Колокация в App Router: что безопасно размещать рядом

В App Router **только файлы-конвенции** (page.tsx, layout.tsx, route.ts и т.д.) обрабатываются
как маршруты. Все остальные файлы **безопасно колоцировать**:

```
src/app/(dashboard)/users/
├── page.tsx                    # --> маршрут /users
├── loading.tsx                 # --> Suspense fallback
├── user-table.tsx              # Безопасно! НЕ маршрут
├── user-table.test.tsx         # Безопасно! НЕ маршрут
├── columns.tsx                 # Безопасно! НЕ маршрут
└── utils.ts                    # Безопасно! НЕ маршрут
```

Однако для ясности рекомендуется использовать приватные папки `_components/`, `_lib/`,
чтобы **визуально** отделить конвенции от вспомогательных файлов.

---

## 1.8 Примеры из реальных enterprise-проектов

### Cal.com -- Turborepo monorepo

**Стек:** Turborepo, Next.js App Router, Prisma, tRPC, Vitest, Playwright.

```
cal.com/
├── apps/
│   ├── web/                    # Основное Next.js приложение
│   │   ├── app/                # App Router (без src/)
│   │   ├── components/         # Компоненты app-уровня
│   │   ├── lib/                # App-specific утилиты
│   │   └── middleware.ts
│   ├── api/                    # Standalone API (v2)
│   └── ai/                     # Cal.ai приложение
├── packages/
│   ├── ui/                     # @calcom/ui -- Design System
│   ├── features/               # Бизнес-фичи как пакет
│   ├── lib/                    # @calcom/lib -- общие утилиты
│   ├── prisma/                 # Схема БД + Prisma клиент
│   ├── trpc/                   # tRPC-роутеры
│   ├── emails/                 # React Email шаблоны
│   ├── types/                  # Общие TypeScript типы
│   ├── config/                 # ESLint, Prettier конфигурации
│   ├── tsconfig/               # Shared TypeScript конфигурации
│   └── ee/                     # Enterprise Edition (платный функционал)
└── turbo.json
```

**Ключевые решения Cal.com:**

- Корневой `app/` без `src/` (исторически -- миграция с Pages Router)
- Фичи вынесены в `packages/features/` -- переиспользуются между apps
- Enterprise-функции изолированы в `packages/ee/`
- Biome вместо ESLint + Prettier (тренд 2025)

### Makerkit -- SaaS Starter Kit (Turborepo)

**Стек:** Turborepo, Next.js 16 App Router, Supabase, Stripe, TanStack.

```
makerkit/
├── apps/
│   ├── web/                    # Основное SaaS-приложение
│   │   ├── app/
│   │   │   ├── (marketing)/    # Публичные страницы
│   │   │   ├── (app)/          # Защищенный dashboard
│   │   │   └── auth/           # Auth flow
│   │   ├── config/             # App-level конфигурация
│   │   └── styles/
│   └── docs/                   # Документация
├── packages/
│   ├── ui/                     # @kit/ui -- shadcn/ui-based design system
│   ├── shared/                 # @kit/shared -- общие утилиты
│   ├── supabase/               # @kit/supabase -- клиент и типы БД
│   ├── billing/                # @kit/billing -- Stripe/Lemon Squeezy
│   ├── email/                  # @kit/email -- React Email
│   ├── monitoring/             # @kit/monitoring -- Sentry/Baselime
│   └── cms/                    # @kit/cms -- Keystatic
└── turbo.json
```

**Ключевые решения Makerkit:**

- Каждый package -- изолированный домен (`billing`, `email`, `monitoring`)
- `_components/` внутри маршрутов для route-specific компонентов
- Правило: "Начни в app, вынеси в package, когда нужен reuse"

### Blazity next-enterprise -- Single App Boilerplate

**Стек:** Next.js 15, Tailwind CSS v4, ESLint 9, Vitest, Playwright, Storybook, OpenTelemetry.

```
next-enterprise/
├── app/                        # App Router (без src/ -- минималистичный подход)
│   ├── layout.tsx
│   ├── page.tsx
│   └── (pages)/
├── components/                 # React-компоненты
│   └── ui/                     # shadcn/ui
├── lib/                        # Утилиты
├── e2e/                        # Playwright E2E-тесты
├── .storybook/                 # Storybook конфигурация
├── .github/                    # CI/CD workflows
└── next.config.ts
```

**Ключевые решения Blazity:**

- **Без `src/`** -- проект не является монорепо, структура минимальна
- Фокус на DevOps: CI/CD, Terraform, Kubernetes health checks, OpenTelemetry
- Conventional Commits + Semantic Release автоматизация
- TypeScript strict mode + `ts-reset` для безопасных типов

### Next.js Boilerplate (nhanluongoe) -- Scalable Starter

**Стек:** Next.js 16, TypeScript, Tailwind CSS, NextAuth, ESLint 9, Husky.

```
nextjs-boilerplate/
├── src/
│   ├── app/                    # App Router
│   │   ├── (public)/           # Публичные маршруты
│   │   └── (protected)/        # Защищенные маршруты
│   ├── components/
│   │   ├── common/             # Общие компоненты
│   │   └── ui/                 # UI-примитивы
│   ├── hooks/
│   ├── lib/
│   ├── services/
│   ├── stores/                 # Zustand stores
│   ├── types/
│   └── utils/
└── tests/
```

### Сводная таблица решений реальных проектов

| Проект          | `src/`        | Feature-based          | Монорепо   | Тесты               |
| --------------- | ------------- | ---------------------- | ---------- | ------------------- |
| **Cal.com**     | Нет           | Да (packages/features) | Turborepo  | Vitest + Playwright |
| **Makerkit**    | Нет (в apps/) | Да (packages/\*)       | Turborepo  | Vitest + Playwright |
| **Blazity**     | Нет           | Нет (layer-based)      | Single app | Vitest + Playwright |
| **nhanluongoe** | Да            | Нет (layer-based)      | Single app | Jest + Playwright   |
| **T3 App**      | Да            | Нет (layer-based)      | Single app | (нет по умолчанию)  |

**Вывод:** монорепо-проекты (Cal.com, Makerkit) обычно НЕ используют `src/` внутри app, потому что
`packages/` уже обеспечивает разделение. Single-app проекты чаще используют `src/` для отделения
кода от конфигурации.

---

## Источники

- [Next.js Official: Project Structure](https://nextjs.org/docs/app/getting-started/project-structure)
- [Next.js Official: src Folder Convention](https://nextjs.org/docs/app/api-reference/file-conventions/src-folder)
- [Next.js Official: Middleware Convention](https://nextjs.org/docs/15/app/api-reference/file-conventions/middleware)
- [Next.js Official: Project Organization & Colocation](https://nextjs.org/docs/13/app/building-your-application/routing/colocation)
- [Makerkit: Next.js 16 App Router Project Structure -- The Definitive Guide](https://makerkit.dev/blog/tutorials/nextjs-app-router-project-structure)
- [Blazity/next-enterprise (GitHub)](https://github.com/Blazity/next-enterprise)
- [Cal.com monorepo (GitHub)](https://github.com/calcom/cal.com)
- [nhanluongoe/nextjs-boilerplate (GitHub)](https://github.com/nhanluongoe/nextjs-boilerplate)
- [arhamkhnz/next-colocation-template (GitHub)](https://github.com/arhamkhnz/next-colocation-template)
- [Next.js Component Naming Conventions (DEV Community)](https://dev.to/vikasparmar/nextjs-component-naming-conventions-best-practices-for-file-and-component-names-39o2)
- [Next.js File Naming Best Practices (Shipixen)](https://shipixen.com/blog/nextjs-file-naming-best-practices)
- [Best Practices for Organizing Your Next.js 15 (DEV Community)](https://dev.to/bajrayejoon/best-practices-for-organizing-your-nextjs-15-2025-53ji)
- [The Battle-Tested NextJS Project Structure (Medium)](https://medium.com/@burpdeepak96/the-battle-tested-nextjs-project-structure-i-use-in-2025-f84c4eb5f426)
- [Inside the App Router: Best Practices 2025 (Medium)](https://medium.com/better-dev-nextjs-react/inside-the-app-router-best-practices-for-next-js-file-and-directory-structure-2025-edition-ed6bc14a8da3)
- [Zod Schema Organization (GitHub Discussion)](https://github.com/colinhacks/zod/discussions/1663)
- [Server Actions Organization (GitHub Discussion #55908)](https://github.com/vercel/next.js/discussions/55908)
- [src/ Folder Debate (GitHub Discussion #41839)](https://github.com/vercel/next.js/discussions/41839)
- [Components in app/ vs src/ (GitHub Discussion #50490)](https://github.com/vercel/next.js/discussions/50490)
- [Sentry: Directory Organisation Best Practices](https://sentry.io/answers/next-js-directory-organisation-best-practices/)
- [Collocation on the Frontend Web (Medium)](https://medium.com/@ebugo/collocation-on-the-frontend-web-why-it-matters-and-how-i-do-it-in-next-js-f362949c93b4)
- [Next.js Naming Conventions (Piyush Gambhir)](https://www.piyushgambhir.com/blogs/next-js-naming-conventions)
