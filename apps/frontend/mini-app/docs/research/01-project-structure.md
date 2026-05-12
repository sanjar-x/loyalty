# 1. Структура папок: глубокое исследование организации Next.js 15+ проекта

> **Контекст проекта:** Frontend-only Next.js приложение, часть большой системы с отдельными
> бэкенд-сервисами. Next.js выступает как BFF (Backend for Frontend) / proxy-слой.
> ORM, прямая работа с БД и серверная бизнес-логика — на стороне бэкенд-сервисов.
>
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
│   ├── lib/                    # HTTP-клиенты, хелперы, обёртки
│   ├── hooks/                  # Глобальные кастомные React-хуки
│   ├── actions/                # Server Actions (глобальные)
│   ├── api/                    # API-клиенты для бэкенд-сервисов (BFF)
│   ├── schemas/                # Zod-схемы валидации (формы, запросы)
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
| `lib/`        | HTTP-клиент (fetch-обёртка), утилиты авторизации, хелперы                   | Инфраструктурный код                    |
| `hooks/`      | Глобальные React-хуки: `useMediaQuery`, `useDebounce`, `useLocalStorage`    | Не привязаны к конкретной фиче          |
| `actions/`    | Server Actions общего назначения (не привязанные к одной фиче)              | Серверная логика с `"use server"`       |
| `api/`        | API-клиенты для бэкенд-сервисов (auth, users, billing и т.д.)               | BFF-слой, proxy к бэкенду               |
| `schemas/`    | Zod-схемы валидации форм и запросов к API                                   | Используются и на сервере, и на клиенте |
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
│   ├── actions/                # Server Actions фичи (proxy к бэкенду)
│   │   ├── login.ts            # "use server" -- proxy к auth-сервису
│   │   ├── register.ts         # "use server" -- proxy к auth-сервису
│   │   ├── logout.ts           # "use server" -- очистка сессии
│   │   └── reset-password.ts   # "use server" -- proxy к auth-сервису
│   ├── api/                    # API-клиент для auth-сервиса
│   │   └── auth.client.ts      # login(), register(), getSession() -- fetch к бэкенду
│   ├── schemas/                # Zod-схемы фичи
│   │   ├── login.schema.ts     # loginSchema = z.object({ email, password })
│   │   └── register.schema.ts  # registerSchema с подтверждением пароля
│   ├── types/                  # TypeScript-типы фичи
│   │   └── auth.types.ts       # User, Session, AuthState, LoginPayload
│   └── utils/                  # Утилиты фичи
│       └── token.ts            # parseToken(), isTokenExpired()
│
├── billing/                    # === Фича: Биллинг ===
│   ├── components/
│   │   ├── pricing-table.tsx   # Таблица тарифов
│   │   ├── subscription-card.tsx
│   │   ├── invoice-list.tsx    # Список счетов
│   │   └── usage-meter.tsx     # Индикатор использования
│   ├── hooks/
│   │   ├── use-subscription.ts # Текущая подписка пользователя
│   │   └── use-usage.ts       # Использование ресурсов
│   ├── actions/
│   │   ├── create-checkout.ts  # "use server" -- proxy к billing-сервису
│   │   ├── cancel-subscription.ts
│   │   └── update-plan.ts
│   ├── api/                    # API-клиент для billing-сервиса
│   │   └── billing.client.ts   # getPlans(), createCheckout(), getInvoices()
│   ├── schemas/
│   │   └── billing.schema.ts   # Валидация форм биллинга
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
│   │   ├── update-profile.ts   # "use server" -- proxy к users-сервису
│   │   └── invite-member.ts
│   ├── api/                    # API-клиент для users-сервиса
│   │   └── users.client.ts     # getUser(), updateProfile(), getTeamMembers()
│   ├── schemas/
│   │   ├── profile.schema.ts
│   │   └── invite.schema.ts
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
    │   └── mark-as-read.ts     # "use server" -- proxy к notifications-сервису
    ├── api/
    │   └── notifications.client.ts  # getNotifications(), markAsRead()
    └── types/
        └── notification.types.ts
```

### Принцип: каждая фича -- мини-приложение

Каждая директория в `src/features/` -- это **самодостаточный модуль**. Он содержит все, что нужно
для работы фичи: UI, хуки, API-клиент, Server Actions (proxy к бэкенду), типы. Правила:

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
| API-клиент используется в 2+ фичах        | Переместить в `src/api/`               |

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

  // Proxy к auth-сервису (бизнес-логика на бэкенде)
  const res = await fetch(`${process.env.AUTH_SERVICE_URL}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(parsed.data),
  });

  if (!res.ok) return { error: 'Invalid credentials' };
  // ... установка cookies/токенов
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
  API_BASE_URL: z.string().url(), // URL бэкенд-сервиса
  AUTH_SERVICE_URL: z.string().url(), // URL auth-сервиса
  NEXT_PUBLIC_APP_URL: z.string().url(), // Публичный URL фронтенда
  NEXT_PUBLIC_WS_URL: z.string().url().optional(), // WebSocket URL (если есть)
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
| API-клиент      | `kebab-case.client.ts`   | `auth.client.ts`                     |
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

Примеры enterprise-проектов — см. секцию 6.

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

---

# 2. Архитектурные паттерны фронтенда: глубокое сравнение

> Расширенное исследование архитектурных подходов для Next.js 15+ (App Router).
> **Контекст:** frontend-only приложение, бэкенд — отдельные сервисы, Next.js как BFF/proxy.
> Дата: апрель 2026.

---

## 2.0 Введение: зачем нужна архитектура на фронтенде?

Архитектура фронтенда -- это не про папки. Это про **управление сложностью**: когда кодовая
база переваливает за 100 файлов, отсутствие чётких границ превращает разработку в лотерею --
любое изменение может сломать что угодно. Правильная архитектура обеспечивает:

- **Предсказуемость** -- разработчик знает, где искать код и куда класть новый.
- **Параллельную работу** -- команды не блокируют друг друга.
- **Тестируемость** -- бизнес-логика отделена от фреймворка.
- **Эволюционность** -- систему можно менять по частям, а не переписывать.

В этом разделе сравниваются **пять архитектурных подходов**, применимых к Next.js:

| #   | Подход                         | Ключевая идея                          |
| --- | ------------------------------ | -------------------------------------- |
| 1   | Layer-based (слоёная)          | Разделение по техническому типу        |
| 2   | Feature-based (фиче-модульная) | Разделение по бизнес-домену            |
| 3   | Feature-Sliced Design (FSD)    | Стандартизованные слои + слайсы        |
| 4   | Clean / Hexagonal Architecture | Порты, адаптеры, инверсия зависимостей |
| 5   | Vertical Slice Architecture    | Каждый запрос — самостоятельный срез   |

---

## 2.1 Подход 1: Layer-based (слоёная архитектура)

### Суть

Код группируется по **техническому типу** файла: компоненты, хуки, сервисы, типы --
каждая категория в своей папке.

### Структура

```
src/
├── components/          # Все компоненты приложения
│   ├── Button.tsx
│   ├── LoginForm.tsx
│   ├── UserCard.tsx
│   └── OrderTable.tsx
├── hooks/               # Все хуки
│   ├── useAuth.ts
│   ├── useOrders.ts
│   └── useUsers.ts
├── services/            # Все API-вызовы
│   ├── auth.service.ts
│   ├── orders.service.ts
│   └── users.service.ts
├── types/               # Все типы
│   ├── auth.types.ts
│   ├── order.types.ts
│   └── user.types.ts
├── utils/               # Все утилиты
└── app/                 # Next.js маршруты
```

### Диаграмма зависимостей

```
┌─────────────────────────────────────────────────┐
│                   app/ (routes)                  │
│  Импортирует всё: components, hooks, services    │
└────────────────────┬────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
  ┌───────────┐ ┌─────────┐ ┌──────────┐
  │components/│ │  hooks/  │ │services/ │
  └─────┬─────┘ └────┬────┘ └─────┬────┘
        │             │            │
        └──────┬──────┘            │
               ▼                   ▼
          ┌─────────┐        ┌──────────┐
          │  types/ │◄───────│  utils/  │
          └─────────┘        └──────────┘
```

**Проблема:** зависимости хаотичны. `LoginForm` импортирует `useAuth`, `auth.service`,
`auth.types` -- разработчик прыгает по 4+ папкам для одной фичи.

### Плюсы и минусы

| Плюс                            | Минус                                   |
| ------------------------------- | --------------------------------------- |
| Интуитивно для новичков         | Не масштабируется (50+ файлов = хаос)   |
| Быстрый старт                   | Работа над фичей = прыжки по 4-5 папкам |
| Привычен большинству            | Частые конфликты мержей в команде       |
| Не требует обучения архитектуре | Невозможно определить границы фичи      |
| Хорошо для прототипов           | Нет контроля над зависимостями          |

### Когда использовать

- Прототипы и MVP (< 20 файлов)
- Проекты на одного разработчика
- Внутренние инструменты с коротким жизненным циклом

---

## 2.2 Подход 2: Feature-based (фиче-модульная архитектура)

### Суть

Код группируется по **бизнес-домену**. Каждая фича -- самодостаточный модуль,
содержащий компоненты, хуки, сервисы, типы и тесты. Структура папок
**«кричит»** о назначении приложения (Screaming Architecture по Роберту Мартину),
а не о фреймворке.

### Структура

```
src/
├── features/
│   ├── auth/                    # Всё про аутентификацию
│   │   ├── components/
│   │   │   ├── login-form.tsx
│   │   │   └── user-menu.tsx
│   │   ├── hooks/
│   │   │   └── use-auth.ts
│   │   ├── services/
│   │   │   └── auth.service.ts
│   │   ├── types/
│   │   │   └── auth.types.ts
│   │   └── index.ts             # Public API фичи
│   │
│   ├── orders/                  # Всё про заказы
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── types/
│   │   └── index.ts
│   │
│   └── users/                   # Всё про пользователей
│       ├── components/
│       ├── hooks/
│       ├── services/
│       ├── types/
│       └── index.ts
│
├── components/                  # Общие UI-компоненты (Button, Input)
├── lib/                         # Общие утилиты
├── hooks/                       # Общие хуки (useDebounce, useMediaQuery)
└── app/                         # Next.js маршруты
```

### Диаграмма зависимостей

```
┌────────────────────────────────────────────────────────┐
│                    app/ (routes)                        │
│  Каждая страница импортирует из features/ и components/ │
└───────────┬──────────────┬──────────────┬──────────────┘
            │              │              │
            ▼              ▼              ▼
     ┌─────────────┐ ┌──────────┐ ┌─────────────┐
     │ features/   │ │features/ │ │  features/  │
     │    auth/    │ │  orders/ │ │   users/    │
     │ ┌─────────┐ │ │          │ │             │
     │ │  comps  │ │ │          │ │             │
     │ │  hooks  │ │ │          │ │             │
     │ │  api    │ │ │          │ │             │
     │ │  types  │ │ │          │ │             │
     │ └─────────┘ │ │          │ │             │
     └──────┬──────┘ └─────┬────┘ └──────┬──────┘
            │              │              │
            └──────────────┼──────────────┘
                           ▼
              ┌────────────────────────┐
              │  components/ lib/      │
              │  hooks/ types/ config/ │
              │   (общие ресурсы)      │
              └────────────────────────┘
```

**Правило:** фичи могут импортировать из общих ресурсов, но **не друг из друга**
напрямую (либо через явный public API).

### Плюсы и минусы

| Плюс                                | Минус                                          |
| ----------------------------------- | ---------------------------------------------- |
| Структура отражает бизнес-домен     | Требует дисциплины в определении границ        |
| Фича = зона ответственности команды | Дублирование кода между фичами                 |
| Минимум конфликтов мержей           | Непонятно, куда класть cross-feature логику    |
| Удаление фичи = удаление папки      | Нет стандарта: каждая команда делает по-своему |
| Высокая cohesion внутри фичи        | Требуется onboarding по архитектуре            |

### Пример кода: фича Auth

```typescript
// src/features/auth/types/auth.types.ts
export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user';
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}
```

```typescript
// src/features/auth/api/auth.client.ts  -- API-клиент для auth-сервиса
import type { LoginCredentials, User } from '../types/auth.types';

const AUTH_URL = process.env.AUTH_SERVICE_URL;

export async function login(credentials: LoginCredentials): Promise<User> {
  const response = await fetch(`${AUTH_URL}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(credentials),
  });
  if (!response.ok) throw new Error('Login failed');
  return response.json();
}

export async function logout(token: string): Promise<void> {
  await fetch(`${AUTH_URL}/logout`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function getCurrentUser(token: string): Promise<User | null> {
  const response = await fetch(`${AUTH_URL}/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) return null;
  return response.json();
}
```

```typescript
// src/features/auth/hooks/use-auth.ts
'use client';

import { useState, useEffect } from 'react';
import * as authClient from '../api/auth.client';
import type { AuthState, LoginCredentials } from '../types/auth.types';

export function useAuth(): AuthState & {
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
} {
  const [state, setState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
  });

  useEffect(() => {
    authClient.getCurrentUser().then((user) => {
      setState({ user, isAuthenticated: !!user, isLoading: false });
    });
  }, []);

  return {
    ...state,
    login: async (credentials) => {
      const user = await authClient.login(credentials);
      setState({ user, isAuthenticated: true, isLoading: false });
    },
    logout: async () => {
      await authClient.logout();
      setState({ user: null, isAuthenticated: false, isLoading: false });
    },
  };
}
```

```typescript
// src/features/auth/components/login-form.tsx
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuth } from '../hooks/use-auth';

export function LoginForm() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await login({ email, password });
  };

  return (
    <form onSubmit={handleSubmit}>
      <Input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
      <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
      <Button type="submit">Sign In</Button>
    </form>
  );
}
```

```typescript
// src/features/auth/index.ts  -- Public API
export { LoginForm } from './components/login-form';
export { useAuth } from './hooks/use-auth';
export type { User, LoginCredentials, AuthState } from './types/auth.types';
```

### Когда использовать

- Средние и крупные проекты (30-200+ файлов)
- Команды из 3-10 разработчиков
- Продукты с чётко выделяемыми бизнес-доменами

---

## 2.3 Подход 3: Feature-Sliced Design (FSD)

### Суть

FSD -- это **стандартизованная методология** (не фреймворк), предлагающая фиксированный
набор слоёв с однонаправленными зависимостями. Каждый слой делится на **слайсы**
(по бизнес-домену), а слайсы -- на **сегменты** (по техническому назначению).

### Структура (адаптация для Next.js App Router)

Ключевой конфликт: Next.js использует `app/` для маршрутизации, а FSD использует `app/`
для инициализации. Решение -- разнести их:

```
project-root/
├── app/                         # Next.js App Router (маршруты)
│   ├── layout.tsx               # Оборачивает в FSD-провайдеры из src/app/
│   ├── (auth)/
│   │   └── login/
│   │       └── page.tsx         # Тонкий: реэкспорт из src/pages/
│   └── (dashboard)/
│       └── dashboard/
│           └── page.tsx
│
├── pages/                       # Пустая папка (блокирует Pages Router)
│
└── src/                         # FSD-слои
    ├── app/                     # Слой: инициализация, провайдеры
    │   └── providers/
    │       ├── theme-provider.tsx
    │       └── query-provider.tsx
    │
    ├── pages/                   # Слой: композиция страниц
    │   ├── home/
    │   │   └── ui.tsx
    │   ├── login/
    │   │   └── ui.tsx
    │   └── dashboard/
    │       └── ui.tsx
    │
    ├── widgets/                 # Слой: составные блоки UI
    │   ├── header/
    │   │   ├── ui/
    │   │   │   └── header.tsx
    │   │   └── index.ts
    │   └── sidebar/
    │       ├── ui/
    │       │   └── sidebar.tsx
    │       └── index.ts
    │
    ├── features/                # Слой: пользовательские сценарии
    │   ├── auth/
    │   │   ├── login/
    │   │   │   ├── ui/
    │   │   │   │   └── login-form.tsx
    │   │   │   ├── model/
    │   │   │   │   └── use-login.ts
    │   │   │   ├── api/
    │   │   │   │   └── login.action.ts
    │   │   │   └── index.ts
    │   │   └── logout/
    │   │       ├── ui/
    │   │       │   └── logout-button.tsx
    │   │       └── index.ts
    │   └── cart/
    │       └── add-to-cart/
    │           ├── ui/
    │           ├── model/
    │           ├── api/
    │           └── index.ts
    │
    ├── entities/                # Слой: бизнес-сущности
    │   ├── user/
    │   │   ├── ui/
    │   │   │   └── user-card.tsx
    │   │   ├── model/
    │   │   │   └── user.types.ts
    │   │   ├── api/
    │   │   │   └── user.queries.ts
    │   │   └── index.ts
    │   └── order/
    │       ├── ui/
    │       ├── model/
    │       ├── api/
    │       └── index.ts
    │
    └── shared/                  # Слой: общие ресурсы
        ├── ui/
        │   ├── button.tsx
        │   ├── input.tsx
        │   └── dialog.tsx
        ├── lib/
        │   ├── cn.ts
        │   └── cache-tags.ts
        ├── api/
        │   └── base-client.ts
        └── config/
            └── env.ts
```

### Диаграмма зависимостей (строго однонаправленные)

```
  ┌──────────────────────────────────────────────────────────────┐
  │  app/  (Next.js routes)                                      │
  │  Тонкие файлы: реэкспорт из src/pages/                      │
  └──────────────────────────┬───────────────────────────────────┘
                             ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  src/app/   — провайдеры, инициализация                      │
  └──────────────────────────┬───────────────────────────────────┘
                             ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  src/pages/ — композиция: импорт widgets + features           │
  └──────────┬──────────────────────────────────┬────────────────┘
             ▼                                  ▼
  ┌─────────────────────────┐    ┌──────────────────────────────┐
  │  src/widgets/            │    │  src/features/               │
  │  Импорт: features,       │    │  Импорт: entities, shared    │
  │  entities, shared        │    │  НЕ импортирует widgets!     │
  └──────────┬──────────────┘    └──────────────┬───────────────┘
             │                                  │
             └──────────────┬───────────────────┘
                            ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  src/entities/ — бизнес-сущности, их UI и API                │
  │  Импорт: ТОЛЬКО shared                                       │
  └──────────────────────────┬───────────────────────────────────┘
                             ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  src/shared/ — UI-kit, утилиты, конфиги                      │
  │  Импорт: НИЧЕГО из проекта (только npm-пакеты)               │
  └──────────────────────────────────────────────────────────────┘
```

### Правило зависимостей

> Каждый слой может импортировать **только из слоёв ниже себя**.
> Слайсы внутри одного слоя **не могут** импортировать друг друга.

Нарушение этого правила -- сигнал архитектурной ошибки. Проверяется линтером
`@feature-sliced/eslint-config` или `eslint-plugin-boundaries`.

### Плюсы и минусы

| Плюс                                          | Минус                                    |
| --------------------------------------------- | ---------------------------------------- |
| Стандартизованная структура                   | Конфликт с App Router (нужен workaround) |
| Строгий контроль зависимостей                 | Крутая кривая обучения                   |
| Масштабируется до больших команд              | Overhead для малых проектов              |
| Предсказуемость: знаешь слой = знаешь правила | Больше файлов и папок                    |
| Активное сообщество и тулинг                  | Избыточно для MVP                        |

### Пример: та же фича Auth в FSD

```typescript
// src/entities/user/model/user.types.ts
export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user';
}
```

```typescript
// src/entities/user/api/user.queries.ts
import type { User } from '../model/user.types';

export async function getCurrentUser(): Promise<User | null> {
  const response = await fetch('/api/auth/me');
  if (!response.ok) return null;
  return response.json();
}
```

```typescript
// src/entities/user/index.ts  -- Public API
export type { User } from './model/user.types';
export { getCurrentUser } from './api/user.queries';
export { UserCard } from './ui/user-card';
```

```typescript
// src/features/auth/login/api/login.action.ts
'use server';

import { revalidateTag } from 'next/cache';

interface LoginCredentials {
  email: string;
  password: string;
}

export async function loginAction(credentials: LoginCredentials) {
  const response = await fetch(`${process.env.API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(credentials),
  });

  if (!response.ok) {
    return { error: 'Invalid credentials' };
  }

  revalidateTag('current-user');
  return { success: true };
}
```

```typescript
// src/features/auth/login/ui/login-form.tsx
'use client';

import { useState } from 'react';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { loginAction } from '../api/login.action';

export function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const result = await loginAction({ email, password });
    if (result.error) alert(result.error);
  };

  return (
    <form onSubmit={handleSubmit}>
      <Input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
      <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
      <Button type="submit">Sign In</Button>
    </form>
  );
}
```

```typescript
// src/features/auth/login/index.ts  -- Public API
export { LoginForm } from './ui/login-form';
```

```typescript
// src/pages/login/ui.tsx  -- Композиция страницы
import { LoginForm } from '@/features/auth/login';

export function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center">
      <div className="w-full max-w-md p-6">
        <h1 className="mb-6 text-2xl font-bold">Login</h1>
        <LoginForm />
      </div>
    </main>
  );
}
```

```typescript
// app/(auth)/login/page.tsx  -- Тонкий маршрут
export { LoginPage as default } from '@/pages/login/ui';
```

### Когда использовать

- Крупные проекты (100+ файлов)
- Команды 5+ разработчиков
- Долгоживущие продукты с потребностью в стандартизации
- Команды, готовые инвестировать в onboarding

---

## 2.4 Подход 4: Clean / Hexagonal Architecture

Clean/Hexagonal Architecture — избыточен для frontend-only BFF проекта. Используем Feature-based архитектуру.

---

## 2.5 Подход 5: Vertical Slice Architecture

### Суть

Идея Джимми Богарда: вместо разделения по слоям код организуется вокруг
**конкретных пользовательских запросов**. Каждый «срез» -- это end-to-end
реализация одного действия, от UI до данных. Связность максимальна внутри
среза, минимальна между срезами.

Ключевое отличие от Feature-based: Feature-based группирует по **домену**
(User, Order), Vertical Slice -- по **действию** (CreateOrder, GetUserProfile).

### Структура

```
src/
├── slices/
│   ├── create-order/
│   │   ├── create-order.action.ts    # Server Action
│   │   ├── create-order.form.tsx     # UI компонент
│   │   ├── create-order.schema.ts    # Zod-валидация
│   │   ├── create-order.types.ts     # Типы этого среза
│   │   └── create-order.test.ts      # Тест
│   │
│   ├── get-orders/
│   │   ├── get-orders.query.ts       # Серверный запрос
│   │   ├── get-orders.table.tsx      # UI таблица
│   │   └── get-orders.types.ts
│   │
│   ├── login/
│   │   ├── login.action.ts
│   │   ├── login.form.tsx
│   │   ├── login.schema.ts
│   │   └── login.types.ts
│   │
│   └── get-current-user/
│       ├── get-current-user.query.ts
│       └── get-current-user.types.ts
│
├── shared/                          # Общие ресурсы
│   ├── ui/
│   ├── lib/
│   └── types/
│
└── app/                             # Next.js маршруты
```

### Диаграмма зависимостей

```
┌──────────────────────────────────────────────────────────────┐
│                     app/ (routes)                             │
│  page.tsx импортирует один или несколько slices               │
└──────┬────────────┬────────────┬────────────┬───────────────┘
       │            │            │            │
       ▼            ▼            ▼            ▼
  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐
  │ create- │ │  get-    │ │  login  │ │  get-    │
  │ order   │ │  orders  │ │         │ │  current │
  │         │ │          │ │         │ │  -user   │
  │ action  │ │ query    │ │ action  │ │ query    │
  │ form    │ │ table    │ │ form    │ │          │
  │ schema  │ │ types    │ │ schema  │ │ types    │
  │ types   │ │          │ │ types   │ │          │
  └────┬────┘ └─────┬────┘ └────┬───┘ └────┬─────┘
       │            │            │           │
       └────────────┴────────────┴───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │      shared/         │
              │  ui, lib, types      │
              └──────────────────────┘

Срезы НЕ зависят друг от друга.
Каждый срез -- самодостаточная единица.
```

### Плюсы и минусы

| Плюс                                                 | Минус                                    |
| ---------------------------------------------------- | ---------------------------------------- |
| Максимальная cohesion (всё в одном месте)            | Дублирование типов между срезами         |
| Добавление фичи = добавление папки (no side effects) | Не подходит для shared сущностей (User)  |
| Каждый срез можно тестировать изолированно           | Много мелких папок                       |
| Естественно сочетается с CQRS                        | Плохо масштабируется при сложных доменах |
| Разные паттерны в разных срезах                      | Непривычно для frontend-разработчиков    |

### Пример: та же фича Auth (login) как Vertical Slice

```typescript
// src/slices/login/login.schema.ts
import { z } from 'zod';

export const loginSchema = z.object({
  email: z.string().email('Invalid email'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

export type LoginInput = z.infer<typeof loginSchema>;
```

```typescript
// src/slices/login/login.action.ts
'use server';

import { revalidateTag } from 'next/cache';
import { loginSchema, type LoginInput } from './login.schema';

export async function loginAction(data: LoginInput) {
  const parsed = loginSchema.safeParse(data);
  if (!parsed.success) return { error: parsed.error.flatten() };

  const response = await fetch(`${process.env.API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(parsed.data),
  });

  if (!response.ok) return { error: 'Invalid credentials' };

  revalidateTag('current-user');
  return { success: true };
}
```

```typescript
// src/slices/login/login.form.tsx
'use client';

import { useActionState } from 'react';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { loginAction } from './login.action';

export function LoginForm() {
  const [state, formAction, isPending] = useActionState(loginAction, null);

  return (
    <form action={formAction}>
      <Input name="email" placeholder="Email" />
      <Input name="password" type="password" placeholder="Password" />
      {state?.error && <p className="text-red-500">{String(state.error)}</p>}
      <Button type="submit" disabled={isPending}>
        {isPending ? 'Signing in...' : 'Sign In'}
      </Button>
    </form>
  );
}
```

### Когда использовать

- CRUD-тяжёлые приложения с множеством независимых операций
- Микрофронтенды
- Проекты с CQRS на бэкенде
- Прототипирование, когда нужно быстро добавлять/удалять фичи

---

## 2.6 Сравнительная таблица всех подходов

| Критерий                       | Layer-based |  Feature-based  |       FSD        |   Clean/Hex   | Vertical Slice  |
| ------------------------------ | :---------: | :-------------: | :--------------: | :-----------: | :-------------: |
| **Масштабируемость**           |   Низкая    |     Высокая     |  Очень высокая   |    Высокая    |     Средняя     |
| **Кривая обучения**            |   Нулевая   |     Низкая      |     Средняя      |    Высокая    |     Низкая      |
| **Boilerplate**                | Минимальный |    Умеренный    |  Выше среднего   |    Высокий    |   Минимальный   |
| **Тестируемость**              |   Низкая    |     Средняя     |     Высокая      | Максимальная  |     Высокая     |
| **Командная работа**           |    Плохо    |     Хорошо      |     Отлично      |    Хорошо     |     Хорошо      |
| **Контроль зависимостей**      |     Нет     |    Частичный    |     Строгий      | Строгий (DI)  |    По срезам    |
| **Совместимость с App Router** |   Полная    |     Полная      |   С workaround   |    Полная     |     Полная      |
| **Подходит для**               |     MVP     | Средние проекты | Крупные проекты  | Сложный домен | CRUD-приложения |
| **Размер команды**             |     1-2     |      3-10       |      5-20+       |     5-15      |      3-10       |
| **Стандартизация**             |     Нет     |       Нет       | Да (методология) | Паттерны GoF  |       Нет       |

---

## 2.7 Гибридный подход: рекомендация для enterprise

Для большинства enterprise-проектов на Next.js оптимален **гибридный подход**,
сочетающий лучшие элементы Feature-based и FSD:

```
src/
├── app/                    # Next.js маршруты (тонкие файлы)
├── features/               # Feature-based: бизнес-фичи
│   ├── auth/
│   ├── billing/
│   └── users/
├── components/             # Общие UI-компоненты
│   ├── ui/                 # Атомарные (Button, Input)
│   ├── layout/             # Лейаут (Header, Sidebar)
│   └── shared/             # Составные (PageHeader, ErrorBoundary)
├── api/                    # API-клиенты для бэкенд-сервисов (общие)
├── lib/                    # HTTP-клиент (fetch-обёртка), утилиты
├── hooks/                  # Общие хуки
├── types/                  # Глобальные типы
├── config/                 # Конфигурация (env, endpoints)
└── middleware.ts            # Auth-токены, проксирование, i18n
```

**Почему это работает для frontend-only проекта:**

- `features/` даёт фиче-модульную организацию без overhead FSD
- `api/` -- единый слой взаимодействия с бэкенд-сервисами
- `lib/` -- HTTP-клиент с interceptors (auth headers, error handling)
- Общие ресурсы (`components/`, `hooks/`) -- из layer-based
- App Router используется нативно, без workaround
- Server Actions и Route Handlers работают как BFF/proxy к бэкенду

---

## 2.8 Матрица принятия решений: какой подход выбрать

```
                        Сложность бизнес-логики
                    Низкая ──────────────── Высокая
                    │                           │
Размер    Малый     │  Layer-based    Clean/Hex  │
команды             │  (до 20 файлов) (если DDD) │
  │                 │                           │
  │                 │  Feature-based  Feature-   │
  │       Средний   │  (3-10 чел.)   Sliced     │
  │                 │                Design     │
  │                 │                           │
  │       Крупный   │  Vertical      FSD +      │
  │                 │  Slice (CRUD)  Гибрид     │
                    │                           │
                    └───────────────────────────┘
```

### Алгоритм выбора (Decision Tree)

```
1. Проект < 20 файлов, 1-2 разработчика?
   → Layer-based. Не усложняйте.

2. CRUD-приложение, 50+ экранов, простая логика?
   → Vertical Slice Architecture.

3. 30-100 файлов, 3-5 разработчиков, чёткие домены?
   → Feature-based.

4. 100+ файлов, 5-20 разработчиков, нужна стандартизация?
   → Feature-Sliced Design (или гибрид с FSD-элементами).

5. Сложная бизнес-логика (финтех, медтех, ERP)?
   → Clean/Hexagonal Architecture.

6. Enterprise, 10+ разработчиков, разнородные требования?
   → Гибридный подход (Feature-based + elements FSD).
```

---

## 2.9 Межфичевое взаимодействие (Cross-Feature Communication)

Одна из главных проблем feature-based архитектур -- как фичи общаются друг с другом,
не нарушая границы изоляции. Пять основных паттернов:

### Паттерн 1: Shared Entities (рекомендуется)

Общие бизнес-сущности выносятся в слой `entities/` или `shared/types/`.

```typescript
// src/entities/user/index.ts  -- Общая сущность
export type { User } from './model/user.types';
export { getCurrentUser } from './api/user.queries';

// src/features/auth/ и src/features/billing/ оба импортируют User из entities/
```

```
  features/auth/  ──────►  entities/user/  ◄──────  features/billing/
                               │
                          Общая точка зависимости,
                          а не прямая связь между фичами
```

### Паттерн 2: Event Bus (для слабой связанности)

Фичи общаются через события, не зная друг о друге.

```typescript
// src/lib/event-bus.ts
type EventCallback<T = unknown> = (data: T) => void;

class EventBus {
  private listeners = new Map<string, Set<EventCallback>>();

  on<T>(event: string, callback: EventCallback<T>): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback as EventCallback);

    // Возвращает функцию отписки
    return () => this.listeners.get(event)?.delete(callback as EventCallback);
  }

  emit<T>(event: string, data: T): void {
    this.listeners.get(event)?.forEach((cb) => cb(data));
  }
}

export const eventBus = new EventBus();
```

```typescript
// src/features/auth/hooks/use-auth.ts  -- Отправляет событие
import { eventBus } from '@/lib/event-bus';

// После логина:
eventBus.emit('auth:login', { userId: user.id });
```

```typescript
// src/features/notifications/hooks/use-notifications.ts  -- Слушает событие
import { useEffect } from 'react';
import { eventBus } from '@/lib/event-bus';

export function useNotifications() {
  useEffect(() => {
    const unsubscribe = eventBus.on('auth:login', ({ userId }) => {
      // Загрузить уведомления для пользователя
    });
    return unsubscribe;
  }, []);
}
```

### Паттерн 3: Shared Context Provider (для глобального состояния)

Провайдер контекста в корневом layout обеспечивает доступ к общему состоянию.

```typescript
// src/app/providers/auth-provider.tsx  -- Общий провайдер
'use client';

import { createContext, useContext, useState } from 'react';
import type { User } from '@/types/user';

interface AuthContextValue {
  user: User | null;
  setUser: (user: User | null) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  return (
    <AuthContext.Provider value={{ user, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuthContext must be used within AuthProvider');
  return ctx;
}
```

### Паттерн 4: Server-Side через Cache Tags (Next.js-специфичный)

Фичи инвалидируют кэш друг друга через теги, не импортируя код.

```typescript
// src/features/billing/actions/update-plan.action.ts
'use server';

import { revalidateTag } from 'next/cache';

export async function updatePlanAction(planId: string) {
  await fetch(`${process.env.API_BASE_URL}/billing/plan`, {
    method: 'PUT',
    body: JSON.stringify({ planId }),
  });

  revalidateTag('billing:plan');
  revalidateTag('user:permissions'); // ← Инвалидирует данные другой фичи
}
```

```typescript
// src/features/auth/api/get-permissions.query.ts
import { unstable_cache } from 'next/cache';

export const getPermissions = unstable_cache(
  async (userId: string) => {
    const res = await fetch(`${process.env.API_BASE_URL}/users/${userId}/permissions`);
    return res.json();
  },
  ['user-permissions'],
  { tags: ['user:permissions'] }, // ← Будет инвалидирован billing-фичей
);
```

### Паттерн 5: Composition в маршрутах (самый простой)

Страница (route) собирает фичи вместе, передавая данные через пропсы.

```typescript
// src/app/(dashboard)/dashboard/page.tsx
import { getCurrentUser } from '@/features/auth/api/auth.client';
import { UserStats } from '@/features/users/components/user-stats';
import { RecentOrders } from '@/features/orders/components/recent-orders';
import { BillingAlert } from '@/features/billing/components/billing-alert';

export default async function DashboardPage() {
  const user = await getCurrentUser();
  if (!user) redirect('/login');

  return (
    <div>
      <UserStats userId={user.id} />
      <RecentOrders userId={user.id} />
      <BillingAlert userId={user.id} />
    </div>
  );
}
```

### Сравнение паттернов межфичевого взаимодействия

| Паттерн           | Связанность |  Сложность  | Server/Client |        Рекомендация        |
| ----------------- | :---------: | :---------: | :-----------: | :------------------------: |
| Shared Entities   |   Низкая    |   Низкая    |      Оба      |      Основной подход       |
| Event Bus         | Минимальная |   Средняя   |    Client     | Для уведомлений, аналитики |
| Context Provider  |   Средняя   |   Низкая    |    Client     |  Для auth, theme, locale   |
| Cache Tags        | Минимальная |   Низкая    |    Server     |   Для инвалидации данных   |
| Route Composition |   Нулевая   | Минимальная |    Server     |  Для страниц-агрегаторов   |

---

## 2.10 Миграция архитектуры

Проект greenfield — миграция архитектуры не требуется.

---

## 2.11 Архитектурные решения (ADR): фиксация выбора

Для enterprise-проектов критически важно фиксировать архитектурные решения
в формате **Architectural Decision Records (ADR)**. Это живой документ,
объясняющий **почему** был выбран конкретный подход.

### Шаблон ADR (формат MADR)

```markdown
# ADR-001: Выбор архитектурного подхода для frontend

## Статус

Принято (2026-04-05)

## Контекст

Проект — enterprise SaaS-приложение на Next.js 15+ (App Router).
Команда: 8 frontend-разработчиков, 3 из которых — junior.
Ожидаемый размер: 200+ файлов, 15+ бизнес-фичей.

## Рассмотренные варианты

1. Layer-based — отклонён: не масштабируется для команды 8 человек
2. Feature-Sliced Design — отклонён: конфликт с App Router, высокий порог входа
3. Clean Architecture — отклонён: избыточный boilerplate для frontend
4. **Feature-based (гибрид)** — выбран
5. Vertical Slice — отклонён: плохо подходит для сложного домена

## Решение

Гибридный Feature-based подход:

- `src/features/` для бизнес-фичей
- `src/entities/` для общих бизнес-сущностей (из FSD)
- `src/components/`, `src/lib/`, `src/hooks/` для общих ресурсов
- Контроль границ через `eslint-plugin-boundaries`

## Причины выбора

- Баланс между структурой и простотой
- Низкий порог входа для junior-разработчиков
- Полная совместимость с App Router
- Слой entities решает проблему shared бизнес-логики

## Последствия

- Необходимо документировать границы каждой фичи
- При росте до 20+ фичей рассмотреть переход на полный FSD
- Каждая фича должна иметь index.ts (public API)
```

### Где хранить ADR

```
docs/
└── adr/
    ├── 001-architecture-pattern.md
    ├── 002-state-management.md
    ├── 003-api-layer-design.md
    └── template.md
```

ADR хранятся в репозитории рядом с кодом и версионируются через Git.
Это обеспечивает трассируемость решений и контекст для новых членов команды.

---

## 2.12 Инструменты контроля архитектуры

### eslint-plugin-boundaries

Проверяет правила импортов между архитектурными элементами в реальном времени (в IDE).

```bash
pnpm add -D eslint-plugin-boundaries
```

### dependency-cruiser

Визуализирует зависимости, находит циклы, проверяет архитектурные правила в CI.

```bash
pnpm add -D dependency-cruiser

# Инициализация
npx depcruise --init

# Проверка
npx depcruise --validate .dependency-cruiser.cjs src/

# Визуализация
npx depcruise --output-type dot src/ | dot -T svg > dependency-graph.svg
```

Пример правила для dependency-cruiser:

```javascript
// .dependency-cruiser.cjs
module.exports = {
  forbidden: [
    {
      name: 'no-feature-to-feature',
      comment: 'Features must not depend on other features directly',
      severity: 'error',
      from: { path: '^src/features/([^/]+)/' },
      to: { path: '^src/features/([^/]+)/' },
      // Разрешаем импорт внутри своей фичи
      // но запрещаем из чужой фичи
    },
    {
      name: 'no-circular',
      severity: 'error',
      from: {},
      to: { circular: true },
    },
  ],
};
```

### @feature-sliced/eslint-config

Для проектов на FSD -- проверяет слои, слайсы, public API.

```bash
pnpm add -D @feature-sliced/eslint-config
```

---

## 2.13 Итоговые рекомендации

1. **Не начинайте с Clean Architecture** -- у нас frontend-only проект без серверной бизнес-логики,
   overhead портов и адаптеров не оправдан. Бизнес-логика живёт на бэкенд-сервисах.

2. **Layer-based -- только для прототипов**. При росте до 30+ файлов немедленно
   мигрируйте на Feature-based.

3. **FSD -- отличный выбор**, но требует workaround с App Router и инвестиций
   в обучение. Подходит для команд, готовых к стандартизации.

4. **Гибридный Feature-based -- наш выбор** для frontend-only проекта.
   `features/` для бизнес-фичей + `api/` для клиентов к бэкенд-сервисам + общие слои.

5. **Vertical Slice -- недооценённый подход** для CRUD-тяжёлых приложений.
   Особенно хорош в сочетании с Server Actions Next.js как proxy.

6. **Фиксируйте решения в ADR** -- через 6 месяцев никто не вспомнит, почему
   выбран конкретный подход.

7. **Автоматизируйте контроль** через eslint-plugin-boundaries и dependency-cruiser.
   Архитектура без enforcement деградирует за 2-3 спринта.

---

## Источники

- [Feature-Sliced Design: Usage with Next.js](https://feature-sliced.design/docs/guides/tech/with-nextjs)
- [FSD: The Ultimate Next.js App Router Architecture](https://feature-sliced.design/blog/nextjs-app-router-guide)
- [Clean Architecture vs FSD in Next.js (Medium)](https://medium.com/@metastability/clean-architecture-vs-feature-sliced-design-in-next-js-applications-04df25e62690)
- [Clean Architecture in Next.js — The Guide You Need (Medium)](https://medium.com/@plozovikov/clean-architecture-the-guide-you-need-dd8c179b9f95)
- [Building a Clean Next.js App with Hexagonal Architecture (Medium)](https://medium.com/@martin_42533/building-a-clean-next-js-app-with-hexagonal-architecture-and-redux-7c898ac26e66)
- [Hexagonal Architecture in Front-End (Dimitri Dumont)](https://www.dimitri-dumont.fr/en/blog/hexagonal-architecture-front-end)
- [Domain-Driven Design with React (CSS-Tricks)](https://css-tricks.com/domain-driven-design-with-react/)
- [Clean Architecture Meets DDD in Frontend (Medium)](https://medium.com/@carolsancos/clean-architecture-meets-domain-driven-design-in-the-frontend-world-9c75e5f3e62e)
- [Does DDD Belong on the Frontend? (Khalil Stemmler)](https://khalilstemmler.com/articles/typescript-domain-driven-design/ddd-frontend/)
- [Vertical Slice Architecture (Jimmy Bogard)](https://www.jimmybogard.com/vertical-slice-architecture/)
- [You're Slicing Your Architecture Wrong (DEV Community)](https://dev.to/somedood/youre-slicing-your-architecture-wrong-4ob9)
- [Feature-Driven Architecture with Next.js (DEV Community)](https://dev.to/rufatalv/feature-driven-architecture-with-nextjs-a-better-way-to-structure-your-application-1lph)
- [Screaming Architecture in Front-End (Medium)](https://medium.com/@hrynkevych/screaming-architecture-in-front-end-de72d9ec961c)
- [Screaming Architecture: Evolution of React Folder Structure (DEV Community)](https://dev.to/profydev/screaming-architecture-evolution-of-a-react-folder-structure-4g25)
- [Modularizing React Applications with Established UI Patterns (Martin Fowler)](https://martinfowler.com/articles/modularizing-react-apps.html)
- [Migrating a Legacy React Project to FSD (Medium)](https://medium.com/@O5-25/migrating-a-legacy-react-project-to-feature-sliced-design-benefits-challenges-and-considerations-0aeecbc8b866)
- [EventBus Pattern in React (Medium)](https://medium.com/@ilham.abdillah.alhamdi/eventbus-pattern-in-react-a-lightweight-alternative-to-context-and-redux-cc6e8a1dc9ca)
- [Cross Micro Frontends Communication (DEV Community)](https://dev.to/luistak/cross-micro-frontends-communication-30m3)
- [MADR: Markdown Architectural Decision Records](https://adr.github.io/madr/)
- [ADR GitHub Organization](https://adr.github.io/)
- [eslint-plugin-boundaries (npm)](https://www.npmjs.com/package/eslint-plugin-boundaries)
- [dependency-cruiser (GitHub)](https://github.com/sverweij/dependency-cruiser)
- [Taking Frontend Architecture Serious With Dependency-cruiser (Xebia)](https://xebia.com/blog/taking-frontend-architecture-serious-with-dependency-cruiser/)
- [The Battle-Tested NextJS Project Structure 2025 (Medium)](https://medium.com/@burpdeepak96/the-battle-tested-nextjs-project-structure-i-use-in-2025-f84c4eb5f426)
- [Scalable React Projects with Feature-Based Architecture (DEV Community)](https://dev.to/naserrasouli/scalable-react-projects-with-feature-based-architecture-117c)
- [Build Scalable React with Feature-Based Architecture (adjoe)](https://adjoe.io/company/engineer-blog/moving-to-feature-based-react-architecture/)

---

# 3. Паттерны маршрутизации Next.js App Router (углубленное исследование)

> Детальное руководство по всем паттернам маршрутизации Next.js 15+/16 для enterprise-проектов.
> **Контекст:** frontend-only, Server Actions/Route Handlers используются как BFF-proxy к бэкенд-сервисам.
> Дата: апрель 2026.

---

## 3.1 Route Groups -- организация без влияния на URL

Route Groups (папки в круглых скобках) позволяют логически группировать маршруты,
назначать разные layout-ы и изолировать зоны ответственности в команде --
при этом скобки **не попадают в URL**.

### Типичная структура enterprise-приложения

```
src/app/
├── (marketing)/              # Публичные страницы
│   ├── layout.tsx            # Минимальный layout: header + footer
│   ├── page.tsx              # /
│   ├── about/page.tsx        # /about
│   └── pricing/page.tsx      # /pricing
│
├── (dashboard)/              # Защищенные страницы
│   ├── layout.tsx            # Layout с sidebar + topbar + auth guard
│   ├── dashboard/page.tsx    # /dashboard
│   ├── settings/page.tsx     # /settings
│   └── users/
│       ├── page.tsx          # /users
│       └── [id]/page.tsx     # /users/:id
│
├── (auth)/                   # Аутентификация
│   ├── layout.tsx            # Центрированный layout без навигации
│   ├── login/page.tsx        # /login
│   └── register/page.tsx     # /register
│
└── (api)/                    # API-маршруты (можно группировать отдельно)
    └── api/
        ├── webhooks/route.ts
        └── v1/
            └── users/route.ts
```

### Код layout для каждой группы

**`(marketing)/layout.tsx`** -- публичный layout:

```tsx
// src/app/(marketing)/layout.tsx
import { Header } from '@/components/layout/header';
import { Footer } from '@/components/layout/footer';

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <Header variant="marketing" />
      <main className="flex-1">{children}</main>
      <Footer />
    </div>
  );
}
```

**`(dashboard)/layout.tsx`** -- защищенный layout с sidebar:

```tsx
// src/app/(dashboard)/layout.tsx
import { redirect } from 'next/navigation';
import { auth } from '@/lib/auth';
import { Sidebar } from '@/components/layout/sidebar';
import { Topbar } from '@/components/layout/topbar';

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const session = await auth();
  if (!session) redirect('/login');

  return (
    <div className="flex h-screen">
      <Sidebar user={session.user} />
      <div className="flex flex-1 flex-col">
        <Topbar user={session.user} />
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}
```

**`(auth)/layout.tsx`** -- минимальный layout для аутентификации:

```tsx
// src/app/(auth)/layout.tsx
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="w-full max-w-md">{children}</div>
    </div>
  );
}
```

### Правила и ограничения Route Groups

- Две группы **не могут** генерировать одинаковый URL-сегмент (например, `(marketing)/about` и `(shop)/about` -- конфликт).
- Если нужна **главная страница** (`/`) в нескольких группах -- она должна быть только в одной.
- Route groups можно вкладывать: `(dashboard)/(analytics)/reports/page.tsx`.
- Рекомендация: **не более 3-4 групп** на корневом уровне, иначе навигация по проекту усложняется.

---

## 3.2 Parallel Routes -- независимые секции страницы

Parallel Routes используют конвенцию `@folder` для одновременного рендера нескольких
независимых секций на одной странице. Каждый слот автоматически передается как prop
в родительский `layout.tsx`.

### Файловая структура

```
src/app/(dashboard)/dashboard/
├── layout.tsx              # Собирает слоты: children, analytics, activity
├── page.tsx                # Основной контент (/dashboard)
├── @analytics/
│   ├── page.tsx            # Виджет аналитики
│   ├── loading.tsx         # Скелетон только для аналитики
│   ├── error.tsx           # Ошибка только для аналитики
│   └── default.tsx         # Fallback при навигации в другие суб-маршруты
└── @activity/
    ├── page.tsx            # Лента активности
    ├── loading.tsx         # Скелетон только для ленты
    └── default.tsx         # Fallback
```

### Код layout с параллельными слотами

```tsx
// src/app/(dashboard)/dashboard/layout.tsx
export default function DashboardLayout({
  children,
  analytics,
  activity,
}: {
  children: React.ReactNode;
  analytics: React.ReactNode;
  activity: React.ReactNode;
}) {
  return (
    <div className="space-y-6">
      {/* Основной контент (children = page.tsx) */}
      <section>{children}</section>

      {/* Параллельные секции в grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-lg border bg-white p-4 shadow-sm">{analytics}</div>
        <div className="rounded-lg border bg-white p-4 shadow-sm">{activity}</div>
      </div>
    </div>
  );
}
```

### Код слота `@analytics/page.tsx`

```tsx
// src/app/(dashboard)/dashboard/@analytics/page.tsx
import { getAnalyticsData } from '@/services/analytics.service';
import { AnalyticsChart } from '@/features/analytics/components/analytics-chart';

export default async function AnalyticsSlot() {
  const data = await getAnalyticsData();

  return (
    <div>
      <h3 className="mb-4 text-lg font-semibold">Аналитика</h3>
      <AnalyticsChart data={data} />
    </div>
  );
}
```

### Код `default.tsx` -- обязательный fallback

```tsx
// src/app/(dashboard)/dashboard/@analytics/default.tsx
export default function AnalyticsDefault() {
  // Возвращается при навигации в суб-маршруты, где у слота нет совпадения.
  // Можно вернуть null, скелетон или последнее состояние.
  return null;
}
```

**Важно:** без `default.tsx` Next.js вернет 404 при навигации в суб-маршруты,
если у параллельного слота нет соответствующего сегмента.

### Условный рендеринг через Parallel Routes

Parallel Routes позволяют рендерить разный контент в зависимости от роли пользователя:

```tsx
// src/app/(dashboard)/dashboard/layout.tsx
import { auth } from '@/lib/auth';

export default async function DashboardLayout({
  children,
  admin,
  user,
}: {
  children: React.ReactNode;
  admin: React.ReactNode;
  user: React.ReactNode;
}) {
  const session = await auth();
  const isAdmin = session?.user.role === 'admin';

  return (
    <div>
      {children}
      {isAdmin ? admin : user}
    </div>
  );
}
```

### Независимые loading/error states

Каждый слот стримится на клиент **независимо** -- если аналитика загружается 3 секунды,
а лента активности -- 200мс, пользователь увидит ленту сразу, а для аналитики
будет показан `@analytics/loading.tsx`. Это ключевое преимущество перед обычным
разделением на компоненты.

```tsx
// src/app/(dashboard)/dashboard/@analytics/loading.tsx
export default function AnalyticsLoading() {
  return (
    <div className="animate-pulse space-y-3">
      <div className="h-4 w-1/3 rounded bg-gray-200" />
      <div className="h-48 rounded bg-gray-200" />
    </div>
  );
}
```

```tsx
// src/app/(dashboard)/dashboard/@analytics/error.tsx
'use client';

export default function AnalyticsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="rounded-lg bg-red-50 p-4 text-red-800">
      <p>Не удалось загрузить аналитику</p>
      <button onClick={reset} className="mt-2 text-sm underline">
        Попробовать снова
      </button>
    </div>
  );
}
```

---

## 3.3 Intercepting Routes -- модальные окна с URL

Intercepting Routes позволяют перехватывать навигацию и отображать маршрут в контексте
текущей страницы (обычно как модальное окно), сохраняя при этом реальный URL.
При прямом переходе по ссылке или обновлении страницы отображается полная страница.

### Конвенции перехвата

| Конвенция  | Описание                 | Пример                                                  |
| ---------- | ------------------------ | ------------------------------------------------------- |
| `(.)`      | Тот же уровень (sibling) | `(.)photo` перехватывает `photo` рядом                  |
| `(..)`     | На уровень выше (parent) | `(..)product` перехватывает `product` в родителе        |
| `(..)(..)` | На два уровня выше       | Редко используется                                      |
| `(...)`    | От корня приложения      | `(...)product` перехватывает `/product` из любого места |

**Важно:** конвенция основана на **сегментах маршрута**, а не на файловой системе.
Route groups `(group)` не считаются сегментами.

### Полная реализация модального окна товара

Структура файлов:

```
src/app/
├── layout.tsx                          # Root layout с @modal слотом
├── products/
│   ├── page.tsx                        # Список товаров (/products)
│   └── [id]/
│       └── page.tsx                    # Полная страница товара (/products/123)
├── @modal/
│   ├── default.tsx                     # Пустой fallback (модаль не открыта)
│   └── (.)products/[id]/
│       └── page.tsx                    # Перехваченный маршрут -> модальное окно
```

**`src/app/layout.tsx`** -- корневой layout, принимающий слот `@modal`:

```tsx
// src/app/layout.tsx
import type { Metadata } from 'next';
import '@/app/globals.css';

export const metadata: Metadata = {
  title: 'My Store',
};

export default function RootLayout({
  children,
  modal,
}: {
  children: React.ReactNode;
  modal: React.ReactNode;
}) {
  return (
    <html lang="ru">
      <body>
        {children}
        {modal}
      </body>
    </html>
  );
}
```

**`src/app/@modal/default.tsx`** -- пустой fallback:

```tsx
// src/app/@modal/default.tsx
export default function ModalDefault() {
  return null;
}
```

**`src/app/products/page.tsx`** -- список товаров:

```tsx
// src/app/products/page.tsx
import Link from 'next/link';
import { getProducts } from '@/services/products.service';

export default async function ProductsPage() {
  const products = await getProducts();

  return (
    <div className="grid grid-cols-3 gap-4 p-8">
      {products.map((product) => (
        <Link
          key={product.id}
          href={`/products/${product.id}`}
          className="rounded-lg border p-4 transition hover:shadow-md"
        >
          <img src={product.image} alt={product.name} className="h-48 w-full object-cover" />
          <h2 className="mt-2 font-semibold">{product.name}</h2>
          <p className="text-gray-600">${product.price}</p>
        </Link>
      ))}
    </div>
  );
}
```

**`src/app/@modal/(.)products/[id]/page.tsx`** -- перехваченный маршрут (модальное окно):

```tsx
// src/app/@modal/(.)products/[id]/page.tsx
import { getProduct } from '@/services/products.service';
import { Modal } from '@/components/ui/modal';

export default async function ProductModal({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const product = await getProduct(id);

  return (
    <Modal>
      <div className="flex gap-6">
        <img src={product.image} alt={product.name} className="h-64 w-64 rounded-lg object-cover" />
        <div>
          <h2 className="text-2xl font-bold">{product.name}</h2>
          <p className="mt-2 text-gray-600">{product.description}</p>
          <p className="mt-4 text-3xl font-bold">${product.price}</p>
          <button className="mt-4 rounded bg-blue-600 px-6 py-2 text-white">В корзину</button>
        </div>
      </div>
    </Modal>
  );
}
```

**`src/components/ui/modal.tsx`** -- переиспользуемый компонент модального окна:

```tsx
// src/components/ui/modal.tsx
'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useCallback } from 'react';

export function Modal({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  const handleClose = useCallback(() => {
    router.back();
  }, [router]);

  // Закрытие по Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') handleClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={handleClose}
    >
      <div
        className="relative max-h-[90vh] w-full max-w-2xl overflow-auto rounded-xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={handleClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
          aria-label="Закрыть"
        >
          X
        </button>
        {children}
      </div>
    </div>
  );
}
```

**`src/app/products/[id]/page.tsx`** -- полная страница товара (при прямом переходе):

```tsx
// src/app/products/[id]/page.tsx
import { getProduct } from '@/services/products.service';
import { notFound } from 'next/navigation';

export default async function ProductPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const product = await getProduct(id);

  if (!product) notFound();

  return (
    <div className="mx-auto max-w-4xl p-8">
      <img src={product.image} alt={product.name} className="h-96 w-full rounded-xl object-cover" />
      <h1 className="mt-6 text-3xl font-bold">{product.name}</h1>
      <p className="mt-4 text-gray-600">{product.description}</p>
      <p className="mt-6 text-4xl font-bold">${product.price}</p>
    </div>
  );
}
```

### Как это работает

1. **Клик по ссылке** (client-side навигация) -> Next.js перехватывает маршрут -> показывает `@modal/(.)products/[id]/page.tsx` как модальное окно поверх текущей страницы. URL обновляется на `/products/123`.
2. **Прямой переход** (ввод URL / обновление страницы) -> рендерится полная страница `products/[id]/page.tsx`.
3. **Закрытие модали** -> `router.back()` возвращает на предыдущий URL, модаль демонтируется.

### Ограничения и подводные камни

- Intercepting Routes работают **только при client-side навигации** через `<Link>` или `router.push`.
- Используйте `router.back()` для закрытия модали, **не** `router.push("/products")` -- это создаст новую запись в истории.
- `default.tsx` в слоте `@modal` **обязателен**, иначе будет 404.
- Осторожно с вложенными route groups -- конвенция `(..)` считает сегменты маршрута, не файловой системы.

---

## 3.4 Динамические маршруты: `[slug]`, `[...slug]`, `[[...slug]]`

### Сравнительная таблица

| Тип                | Синтаксис     | Совпадает                       | НЕ совпадает            | `params`                                    |
| ------------------ | ------------- | ------------------------------- | ----------------------- | ------------------------------------------- |
| Динамический       | `[id]`        | `/products/123`                 | `/products/123/edit`    | `{ id: "123" }`                             |
| Catch-all          | `[...slug]`   | `/docs/a`, `/docs/a/b/c`        | `/docs` (без сегментов) | `{ slug: ["a","b","c"] }`                   |
| Optional catch-all | `[[...slug]]` | `/docs`, `/docs/a`, `/docs/a/b` | -- (совпадает со всем)  | `{ slug: undefined }` или `{ slug: ["a"] }` |

### Примеры использования

**Динамический сегмент** -- для CRUD-страниц:

```tsx
// src/app/users/[id]/page.tsx
export default async function UserPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params; // Next.js 15+: params -- это Promise
  // ...
}
```

**Catch-all** -- для документации с произвольной вложенностью:

```tsx
// src/app/docs/[...slug]/page.tsx
export default async function DocsPage({ params }: { params: Promise<{ slug: string[] }> }) {
  const { slug } = await params;
  // /docs/getting-started/installation -> slug = ["getting-started", "installation"]
  const doc = await getDocByPath(slug.join('/'));
  // ...
}
```

**Optional catch-all** -- для фильтров каталога:

```tsx
// src/app/shop/[[...filters]]/page.tsx
export default async function ShopPage({ params }: { params: Promise<{ filters?: string[] }> }) {
  const { filters } = await params;
  // /shop             -> filters = undefined (показать все)
  // /shop/electronics -> filters = ["electronics"]
  // /shop/electronics/phones -> filters = ["electronics", "phones"]
  const products = await getProducts(filters);
  // ...
}
```

**Важно (Next.js 15+):** `params` и `searchParams` теперь являются `Promise` и требуют `await`.
Это breaking change по сравнению с Next.js 14.

---

## 3.5 loading.tsx, error.tsx, not-found.tsx -- стратегия boundary-файлов

### Иерархия вложенности компонентов

Next.js автоматически оборачивает файлы маршрута в определенную иерархию:

```
<Layout>
  <Template>
    <ErrorBoundary fallback={<Error />}>
      <Suspense fallback={<Loading />}>
        <ErrorBoundary fallback={<NotFound />}>
          <Page />
        </ErrorBoundary>
      </Suspense>
    </ErrorBoundary>
  </Template>
</Layout>
```

**Ключевое правило:** `error.tsx` **не ловит** ошибки из `layout.tsx` того же сегмента --
для этого нужно поместить `error.tsx` в **родительский** сегмент.

### Стратегия размещения

```
src/app/
├── layout.tsx              # Root layout
├── global-error.tsx        # Ловит ошибки из root layout (единственный способ)
├── not-found.tsx           # Глобальная 404 (URL не совпал ни с одним маршрутом)
├── error.tsx               # Глобальный error boundary
├── loading.tsx             # Глобальный loading (осторожно -- может мигать)
│
├── (dashboard)/
│   ├── layout.tsx          # Dashboard layout
│   ├── error.tsx           # Ловит ошибки из dashboard/* но НЕ из этого layout
│   ├── loading.tsx         # Loading для dashboard-секции
│   │
│   ├── dashboard/
│   │   ├── page.tsx
│   │   └── loading.tsx     # Гранулярный loading для /dashboard
│   │
│   └── users/
│       ├── page.tsx        # /users
│       ├── loading.tsx     # Loading для /users
│       ├── error.tsx       # Error только для /users
│       ├── not-found.tsx   # 404 при вызове notFound()
│       └── [id]/
│           ├── page.tsx    # /users/:id
│           ├── loading.tsx # Loading для страницы пользователя
│           └── not-found.tsx # 404 для конкретного пользователя
```

### Код `global-error.tsx`

```tsx
// src/app/global-error.tsx
'use client'; // Обязательно client component

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    // global-error ДОЛЖЕН включать теги <html> и <body>,
    // так как он полностью заменяет root layout при ошибке
    <html>
      <body>
        <div className="flex min-h-screen items-center justify-center">
          <div className="text-center">
            <h1 className="text-2xl font-bold">Что-то пошло не так</h1>
            <p className="mt-2 text-gray-600">{error.digest && `Код ошибки: ${error.digest}`}</p>
            <button onClick={reset} className="mt-4 rounded bg-blue-600 px-4 py-2 text-white">
              Попробовать снова
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
```

### Код `not-found.tsx` с вызовом `notFound()`

```tsx
// src/app/users/[id]/page.tsx
import { notFound } from 'next/navigation';
import { getUserById } from '@/services/users.service';

export default async function UserPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const user = await getUserById(id);

  if (!user) notFound(); // Триггерит ближайший not-found.tsx

  return <UserProfile user={user} />;
}
```

```tsx
// src/app/users/[id]/not-found.tsx
import Link from 'next/link';

export default function UserNotFound() {
  return (
    <div className="p-8 text-center">
      <h2 className="text-xl font-semibold">Пользователь не найден</h2>
      <p className="mt-2 text-gray-600">Проверьте правильность ссылки или вернитесь к списку.</p>
      <Link href="/users" className="mt-4 inline-block text-blue-600 underline">
        К списку пользователей
      </Link>
    </div>
  );
}
```

### Рекомендации по boundary-стратегии

| Уровень             | loading.tsx                          | error.tsx                      | not-found.tsx                 |
| ------------------- | ------------------------------------ | ------------------------------ | ----------------------------- |
| Root (`app/`)       | Осторожно (мигает на каждый переход) | Да                             | Да (глобальная 404)           |
| Route Group         | Да (если все страницы группы похожи) | Да                             | Нет (обычно не нужен)         |
| Конкретная страница | Да (кастомный скелетон)              | Если нужна кастомная обработка | Если есть `notFound()` в page |
| Parallel Route слот | Да (независимый loading)             | Да (изолированная ошибка)      | Редко                         |

---

## 3.6 template.tsx vs layout.tsx -- когда использовать template

### Ключевое различие

| Характеристика         | `layout.tsx`                                | `template.tsx`                            |
| ---------------------- | ------------------------------------------- | ----------------------------------------- |
| **Перемонтирование**   | НЕ перемонтируется при навигации            | Перемонтируется при КАЖДОЙ навигации      |
| **Состояние**          | Сохраняется между страницами                | Сбрасывается на каждой странице           |
| **useEffect**          | Вызывается один раз при первом монтировании | Вызывается при каждой навигации           |
| **DOM**                | Переиспользуется                            | Пересоздается                             |
| **Производительность** | Лучше (нет повторных рендеров)              | Хуже (полный remount)                     |
| **Позиция в иерархии** | Внешний wrapper                             | Внутри layout, снаружи error/loading/page |

### Иерархия: layout оборачивает template

```
<Layout>           ← Не перемонтируется
  <Template>       ← Перемонтируется при навигации
    <ErrorBoundary>
      <Suspense>
        <Page />
      </Suspense>
    </ErrorBoundary>
  </Template>
</Layout>
```

Можно использовать и layout, и template одновременно -- layout будет внешней оболочкой,
а template -- внутренней, перемонтируемой при смене страниц.

### Когда использовать template.tsx

**1. Трекинг просмотров страниц:**

```tsx
// src/app/(dashboard)/template.tsx
'use client';

import { usePathname } from 'next/navigation';
import { useEffect } from 'react';
import { trackPageView } from '@/lib/analytics';

export default function DashboardTemplate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  useEffect(() => {
    trackPageView(pathname);
  }, [pathname]);

  return <>{children}</>;
}
```

**2. Анимации входа/выхода страницы:**

```tsx
// src/app/template.tsx
'use client';

import { useEffect, useRef } from 'react';

export default function AnimatedTemplate({ children }: { children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Анимация появления при каждой навигации
    ref.current?.animate(
      [
        { opacity: 0, transform: 'translateY(10px)' },
        { opacity: 1, transform: 'translateY(0)' },
      ],
      { duration: 300, easing: 'ease-out', fill: 'forwards' },
    );
  }, []);

  return <div ref={ref}>{children}</div>;
}
```

**3. Сброс форм при навигации:**

```tsx
// src/app/(auth)/template.tsx
'use client';

export default function AuthTemplate({ children }: { children: React.ReactNode }) {
  // Форма внутри будет сброшена при каждой навигации
  // между /login и /register, так как template перемонтируется
  return <div className="animate-fadeIn">{children}</div>;
}
```

### Когда НЕ использовать template.tsx

- Если нужно сохранить состояние (открытый sidebar, scroll position) -- используйте `layout.tsx`.
- Если нет специфичной логики на `useEffect`/`useState` -- `layout.tsx` производительнее.
- Если template нужен только для обертки CSS -- используйте `layout.tsx` с CSS-классами.

---

## 3.7 Middleware -- паттерны для enterprise

`middleware.ts` выполняется на Edge Runtime **до** каждого запроса. Это единственная точка
перехвата для auth guards, i18n, редиректов и A/B-тестирования.

### Базовая структура middleware

```ts
// src/middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  // Логика middleware
  return NextResponse.next();
}

// Matcher: middleware вызывается ТОЛЬКО для указанных путей
export const config = {
  matcher: [
    // Исключаем статику, изображения, favicon и API-маршруты
    '/((?!_next/static|_next/image|favicon.ico|api/webhooks).*)',
  ],
};
```

### Паттерн 1: Auth Guard с JWT-верификацией

```ts
// src/middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { jwtVerify } from 'jose';

const PUBLIC_PATHS = ['/', '/about', '/pricing', '/login', '/register'];
const JWT_SECRET = new TextEncoder().encode(process.env.JWT_SECRET!);

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Публичные страницы -- пропускаем
  if (PUBLIC_PATHS.some((path) => pathname === path || pathname.startsWith('/api/public'))) {
    return NextResponse.next();
  }

  const token = request.cookies.get('session-token')?.value;

  if (!token) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('callbackUrl', pathname);
    return NextResponse.redirect(loginUrl);
  }

  try {
    const { payload } = await jwtVerify(token, JWT_SECRET);

    // Передаем данные пользователя в headers для использования в Server Components
    const response = NextResponse.next();
    response.headers.set('x-user-id', String(payload.sub));
    response.headers.set('x-user-role', String(payload.role || 'user'));
    return response;
  } catch {
    // Невалидный/просроченный токен
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('error', 'session-expired');
    return NextResponse.redirect(loginUrl);
  }
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
```

### Паттерн 2: i18n-маршрутизация

```ts
// src/middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const SUPPORTED_LOCALES = ['en', 'ru', 'uz'];
const DEFAULT_LOCALE = 'ru';

function getLocaleFromHeaders(request: NextRequest): string {
  const acceptLang = request.headers.get('accept-language') || '';
  const preferred = acceptLang.split(',')[0]?.split('-')[0]?.toLowerCase();
  return SUPPORTED_LOCALES.includes(preferred || '') ? preferred! : DEFAULT_LOCALE;
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Проверяем, есть ли уже локаль в URL
  const hasLocale = SUPPORTED_LOCALES.some(
    (locale) => pathname.startsWith(`/${locale}/`) || pathname === `/${locale}`,
  );

  if (hasLocale) return NextResponse.next();

  // Определяем локаль из cookie или headers
  const locale = request.cookies.get('NEXT_LOCALE')?.value || getLocaleFromHeaders(request);

  // Перенаправляем на URL с локалью
  const url = request.nextUrl.clone();
  url.pathname = `/${locale}${pathname}`;
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|api).*)'],
};
```

### Паттерн 3: Комбинированный middleware (цепочка)

В реальных проектах middleware обычно совмещает несколько задач.
Рекомендуется разбивать логику на функции и вызывать их последовательно:

```ts
// src/middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Отдельные middleware-функции
import { withAuth } from '@/lib/middleware/auth';
import { withI18n } from '@/lib/middleware/i18n';
import { withRateLimit } from '@/lib/middleware/rate-limit';

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // 1. Rate limiting для API
  if (pathname.startsWith('/api')) {
    const rateLimitResponse = await withRateLimit(request);
    if (rateLimitResponse) return rateLimitResponse; // 429 если превышен лимит
  }

  // 2. i18n для всех страниц (кроме API)
  if (!pathname.startsWith('/api')) {
    const i18nResponse = withI18n(request);
    if (i18nResponse) return i18nResponse; // redirect на URL с локалью
  }

  // 3. Auth для защищенных маршрутов
  if (pathname.startsWith('/dashboard') || pathname.startsWith('/settings')) {
    const authResponse = await withAuth(request);
    if (authResponse) return authResponse; // redirect на /login
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
```

### Ограничения middleware

- Выполняется на **Edge Runtime**: нет доступа к Node.js API (fs, crypto.createHash и т.д.).
- **Один файл** `middleware.ts` на проект (в корне или `src/`).
- Нельзя напрямую обращаться к базе данных -- только через fetch к API.
- Для JWT-верификации используйте `jose` (совместима с Edge Runtime), не `jsonwebtoken`.

---

## 3.8 Route Handlers vs Server Actions -- что когда использовать

### Сравнительная таблица

| Критерий                    | Server Actions                         | Route Handlers                          |
| --------------------------- | -------------------------------------- | --------------------------------------- |
| **Вызов**                   | Из React-компонентов как функции       | Любой HTTP-клиент                       |
| **HTTP-методы**             | Только POST (автоматически)            | GET, POST, PUT, DELETE, PATCH           |
| **Type safety**             | Автоматическая (вызов функции)         | Ручной парсинг Request                  |
| **Кеширование**             | Нет                                    | GET-запросы кешируемы                   |
| **Progressive enhancement** | Да (формы работают без JS)             | Нет                                     |
| **Файл**                    | `actions.ts` или inline `"use server"` | `route.ts`                              |
| **Лучше для**               | Мутации из UI                          | Вебхуки, внешние API, мобильные клиенты |

### Дерево решений

```
Кто вызывает?
├── Внешний клиент (вебхук, мобильное приложение, 3rd party)
│   └── -> Route Handler
├── React-компонент
│   ├── Мутация (создание, обновление, удаление)?
│   │   └── -> Server Action
│   ├── Чтение данных?
│   │   ├── Server Component -> Fetch напрямую в компоненте
│   │   └── Client Component -> Route Handler с кешированием
│   └── Загрузка файлов?
│       └── -> Server Action (FormData) или Route Handler
└── Нужен полный контроль HTTP (headers, status codes, streaming)?
    └── -> Route Handler
```

### Пример Server Action

```ts
// src/features/users/actions/update-user.ts
'use server';

import { revalidatePath } from 'next/cache';
import { z } from 'zod';
import { updateUser } from '@/services/users.service';

const UpdateUserSchema = z.object({
  name: z.string().min(2),
  email: z.string().email(),
});

export async function updateUserAction(formData: FormData) {
  const parsed = UpdateUserSchema.safeParse({
    name: formData.get('name'),
    email: formData.get('email'),
  });

  if (!parsed.success) {
    return { error: parsed.error.flatten().fieldErrors };
  }

  await updateUser(parsed.data);
  revalidatePath('/settings');
  return { success: true };
}
```

### Пример Route Handler

```ts
// src/app/api/webhooks/stripe/route.ts
import { headers } from 'next/headers';
import { NextResponse } from 'next/server';
import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);

export async function POST(request: Request) {
  const body = await request.text();
  const headersList = await headers();
  const signature = headersList.get('stripe-signature')!;

  try {
    const event = stripe.webhooks.constructEvent(
      body,
      signature,
      process.env.STRIPE_WEBHOOK_SECRET!,
    );

    switch (event.type) {
      case 'checkout.session.completed':
        // Обработка успешной оплаты
        break;
      case 'customer.subscription.deleted':
        // Обработка отмены подписки
        break;
    }

    return NextResponse.json({ received: true });
  } catch (err) {
    return NextResponse.json({ error: 'Webhook signature verification failed' }, { status: 400 });
  }
}
```

### Правило 90/10

В типичном enterprise-проекте ~90% серверного кода -- это Server Actions (мутации из UI),
и ~10% -- Route Handlers (вебхуки, публичные API, интеграции).

---

## 3.9 Partial Prerendering (PPR) -- маршрутизация и производительность

PPR (Partial Prerendering) -- стратегия рендеринга, позволяющая комбинировать
статический и динамический контент **в одном маршруте**.

### Как включить (Next.js 15)

```ts
// next.config.ts
import type { NextConfig } from 'next';

const config: NextConfig = {
  experimental: {
    ppr: 'incremental', // Включаем PPR по-маршрутно
  },
};

export default config;
```

```tsx
// src/app/products/page.tsx
export const experimental_ppr = true; // Opt-in для этого маршрута

export default async function ProductsPage() {
  return (
    <div>
      {/* Статическая оболочка -- отправляется мгновенно */}
      <h1>Каталог товаров</h1>
      <FilterBar />

      {/* Динамический контент -- стримится после */}
      <Suspense fallback={<ProductsSkeleton />}>
        <ProductList />
      </Suspense>
    </div>
  );
}
```

### Эволюция в Next.js 16

В Next.js 16 (октябрь 2025) PPR стал стабильным и был переименован:

- Вместо `experimental.ppr` используется `cacheComponents: true`
- Вместо `experimental_ppr` в маршруте -- Cache Components API

---

## 3.10 Блок-схема: выбор паттерна маршрутизации

```
Вопрос                                          Паттерн
───────────────────────────────────────────────────────────────

Нужны разные layout-ы для групп страниц?
  └── Да ────────────────────────────────────> Route Groups

Нужно несколько независимых секций на одной
странице с отдельными loading/error?
  └── Да ────────────────────────────────────> Parallel Routes

Нужно модальное окно с сохранением URL,
которое при прямом переходе -- полная страница?
  └── Да ────────────────────────────────────> Intercepting Routes
                                               + Parallel Routes

Разный контент в зависимости от роли
пользователя (admin/user)?
  └── Да ────────────────────────────────────> Parallel Routes
                                               (условный рендеринг)

Нужен auth guard / i18n / редирект
до рендера страницы?
  └── Да ────────────────────────────────────> Middleware

Маршрут с произвольной глубиной вложенности
(/docs/a/b/c)?
  └── Да ────────────────────────────────────> Catch-all [...slug]

Маршрут может иметь или не иметь сегменты
(/shop или /shop/electronics)?
  └── Да ────────────────────────────────────> Optional catch-all
                                               [[...slug]]

Нужно выполнять useEffect / сбрасывать
состояние при каждой навигации?
  └── Да ────────────────────────────────────> template.tsx

Нужен статический shell + динамический
контент в одном маршруте?
  └── Да ────────────────────────────────────> PPR + Suspense

Для всего остального                          Обычные вложенные
                                               layout + page
```

---

## 3.11 Рекомендации по производительности вложенных layout-ов

### Проблема глубокой вложенности

Каждый layout -- это React-компонент, оборачивающий дочерние. При глубине 5+ уровней:

```
RootLayout > (dashboard)/layout > users/layout > [id]/layout > settings/layout > page
```

Проблемы:

1. **Водопад запросов:** если каждый layout делает async-запрос, они выполняются последовательно (layout рендерится сверху вниз).
2. **Сложность отладки:** ошибку в 5-м уровне сложно отследить.
3. **Негибкость:** layout нельзя отменить/переопределить для одной страницы.

### Решения

**Ограничивайте вложенность -- максимум 3-4 уровня:**

```
RootLayout              # Уровень 1: HTML, providers, глобальные стили
  └── (group)/layout    # Уровень 2: Sidebar, auth guard
      └── section/layout # Уровень 3: Секционный header
          └── page       # Страница
```

**Параллельный data fetching вместо водопада:**

```tsx
// ПЛОХО: водопад -- layout ждет данные перед рендером children
export default async function DashboardLayout({ children }) {
  const user = await getUser(); // 200ms
  const notifications = await getNotifications(); // 300ms
  // Total: 500ms sequential

  return <div>{children}</div>;
}

// ХОРОШО: параллельные запросы
export default async function DashboardLayout({ children }) {
  const [user, notifications] = await Promise.all([getUser(), getNotifications()]);
  // Total: 300ms (parallel)

  return <div>{children}</div>;
}
```

**Выносите динамические данные в Client Components с Suspense:**

```tsx
// ХОРОШО: layout статичный, данные загружаются в Suspense-границах
export default function DashboardLayout({ children }) {
  return (
    <div className="flex">
      <Sidebar />
      <main>
        <Suspense fallback={<TopbarSkeleton />}>
          <Topbar /> {/* Server Component с async data */}
        </Suspense>
        {children}
      </main>
    </div>
  );
}
```

**Делайте layout максимально "тонким":**

Layout должен содержать только структуру (grid, flex) и общие компоненты (sidebar, header).
Бизнес-логика, data fetching и тяжелые вычисления -- в `page.tsx` или отдельных компонентах
с собственными Suspense-границами.

---

## Источники

- [Next.js: Route Groups](https://nextjs.org/docs/app/api-reference/file-conventions/route-groups)
- [Next.js: Parallel Routes](https://nextjs.org/docs/app/api-reference/file-conventions/parallel-routes)
- [Next.js: Intercepting Routes](https://nextjs.org/docs/app/api-reference/file-conventions/intercepting-routes)
- [Next.js: Dynamic Segments](https://nextjs.org/docs/app/api-reference/file-conventions/dynamic-routes)
- [Next.js: template.js](https://nextjs.org/docs/app/api-reference/file-conventions/template)
- [Next.js: Error Handling](https://nextjs.org/docs/app/getting-started/error-handling)
- [Next.js: Partial Prerendering](https://nextjs.org/docs/15/app/getting-started/partial-prerendering)
- [Next.js: Middleware](https://nextjs.org/docs/pages/building-your-application/routing/middleware)
- [Mastering NextJS Parallel Routes (AndiSmith)](https://www.andismith.com/blogs/2025/02/mastering-nextjs-parallel-routes)
- [Server Actions vs Route Handlers (MakerKit)](https://makerkit.dev/blog/tutorials/server-actions-vs-route-handlers)
- [8 Middleware Patterns That Scale (Medium)](https://medium.com/@ThinkingLoop/8-next-js-middleware-patterns-that-scale-across-regions-568dab5f6c38)
- [Next.js Intercepting Routes Guide (Medium)](https://itsankitbhusal.medium.com/next-js-intercepting-routes-a-complete-implementation-guide-2025-what-is-the-intercepting-route-a9571888ac2e)
- [BetterLink Blog: Advanced Routing](https://eastondev.com/blog/en/posts/dev/20251218-nextjs-advanced-routing/)
- [Next.js App Router Patterns 2026 (DEV Community)](https://dev.to/teguh_coding/nextjs-app-router-the-patterns-that-actually-matter-in-2026-146)
- [Next.js 15/16 Features Migration Guide (Jishu Labs)](https://jishulabs.com/blog/nextjs-15-16-features-migration-guide-2026)
- [Next.js Layouts vs Templates (Builder.io)](https://www.builder.io/blog/nextjs-14-layouts-templates)

---

# 4. Границы модулей и управление импортами

> Углубленное исследование инструментов, конфигураций и стратегий для контроля архитектурных границ в Next.js 15+ проектах.
> Дата: апрель 2026.

---

## Содержание

- [4.1 Path Aliases: продвинутая настройка](#41-path-aliases-продвинутая-настройка)
- [4.2 Barrel Files: бенчмарки и альтернативы](#42-barrel-files-бенчмарки-и-альтернативы)
- [4.3 optimizePackageImports: конфигурация Next.js](#43-optimizepackageimports-конфигурация-nextjs)
- [4.4 eslint-plugin-boundaries: полная конфигурация](#44-eslint-plugin-boundaries-полная-конфигурация)
- [4.5 eslint-plugin-import-x: порядок импортов](#45-eslint-plugin-import-x-порядок-импортов)
- [4.6 @feature-sliced/eslint-config](#46-feature-slicedeslint-config)
- [4.7 dependency-cruiser: валидация графа зависимостей](#47-dependency-cruiser-валидация-графа-зависимостей)
- [4.8 Madge: визуализация и обнаружение циклов](#48-madge-визуализация-и-обнаружение-циклов)
- [4.9 Стратегии обнаружения и устранения циклических зависимостей](#49-стратегии-обнаружения-и-устранения-циклических-зависимостей)
- [4.10 Пошаговое руководство: внедрение границ в существующий проект](#410-пошаговое-руководство-внедрение-границ-в-существующий-проект)

---

## 4.1 Path Aliases: продвинутая настройка

### Базовая конфигурация tsconfig.json

```jsonc
// tsconfig.json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"],
      "@/components/*": ["./src/components/*"],
      "@/features/*": ["./src/features/*"],
      "@/lib/*": ["./src/lib/*"],
      "@/hooks/*": ["./src/hooks/*"],
      "@/types/*": ["./src/types/*"],
      "@/services/*": ["./src/services/*"],
      "@/config/*": ["./src/config/*"],
      "@/constants/*": ["./src/constants/*"],
    },
  },
}
```

Next.js нативно поддерживает `paths` и `baseUrl` из `tsconfig.json` -- дополнительная конфигурация бандлера не требуется.

### Выбор префикса: `@/` vs `#/` vs `~/`

| Префикс | Преимущества                                                           | Недостатки                                                                                 |
| ------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `@/*`   | Стандарт Next.js (default при `create-next-app`), широко распространен | Конфликт с npm-scoped пакетами (`@org/pkg`)                                                |
| `#/*`   | Нет конфликтов с npm, визуально отличается от внешних пакетов          | Конфликт с Node.js [subpath imports](https://nodejs.org/api/packages.html#subpath-imports) |
| `~/*`   | Нет конфликтов, используется в Nuxt/Remix                              | Менее распространен в экосистеме Next.js                                                   |

**Рекомендация:** для нового проекта `@/*` остается оптимальным выбором -- он поддерживается Next.js из коробки и является де-факто стандартом. Конфликт с npm-scoped пакетами на практике не возникает, т.к. `@/*` матчит только локальные пути.

### Интеграция с Jest / Vitest

При использовании path aliases необходимо настроить резолвер тестового фреймворка:

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
```

```javascript
// jest.config.js
module.exports = {
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
};
```

### TypeScript Project References в монорепо

TypeScript Project References **не совместимы** напрямую с Next.js, т.к. Next.js использует SWC для компиляции, а не `tsc`. В монорепо рекомендуется:

- Использовать pnpm workspaces + Turborepo вместо Project References
- Определять `tsconfig.json` в каждом пакете для IDE-поддержки
- Для type-checking между пакетами -- `tsc --build` в отдельном CI-шаге

---

## 4.2 Barrel Files: бенчмарки и альтернативы

### Что такое barrel file

Barrel file -- это `index.ts`, который реэкспортирует модули из директории:

```typescript
// src/components/ui/index.ts (barrel file)
export { Button } from './button';
export { Input } from './input';
export { Dialog } from './dialog';
export { DataTable } from './data-table';
// ... ещё 50 компонентов
```

### Реальные бенчмарки производительности

**Данные Vercel (официальный блог, 2024):**

| Метрика                          | С barrel-файлами      | Без / с optimizePackageImports | Улучшение |
| -------------------------------- | --------------------- | ------------------------------ | --------- |
| `@mui/material` dev compile      | 7.1s (2225 модулей)   | 2.9s (735 модулей)             | **-59%**  |
| `@material-ui/icons` dev compile | 10.2s (11738 модулей) | 2.9s (632 модулей)             | **-72%**  |
| `lucide-react` dev compile       | 5.8s (1583 модуля)    | 3.0s (333 модуля)              | **-48%**  |
| `recharts` dev compile           | 5.1s (1485 модулей)   | 3.9s (1317 модулей)            | **-24%**  |
| Рекурсивные barrel (10k модулей) | ~30s компиляция       | ~7s компиляция                 | **-77%**  |
| Cold start (serverless)          | Baseline              | До 40% быстрее                 | **-40%**  |
| Production build                 | Baseline              | ~28% быстрее                   | **-28%**  |

**Данные Atlassian (2024):** удаление barrel-файлов привело к **75% ускорению сборки** в их монорепо.

**Данные из реальных проектов (агрегированные):**

| Кейс                       | First Load JS до | First Load JS после | Экономия             |
| -------------------------- | ---------------- | ------------------- | -------------------- |
| Импорт Button через barrel | 255 KB           | 92.4 KB             | **-64%**             |
| Barrel с SVG-иконками      | +477 KB          | +77 KB              | **-84%**             |
| Среднее по проектам        | --               | --                  | **~48%** bundle size |

### Почему barrel-файлы вредят

```
Импорт через barrel:
import { Button } from '@/components/ui'

Что происходит:
1. Загружается index.ts
2. index.ts парсит ВСЕ реэкспорты
3. Каждый модуль рекурсивно разрешается
4. Tree-shaking в dev-режиме НЕ работает
5. В production -- работает частично (side-effects)

Прямой импорт:
import { Button } from '@/components/ui/button'

Что происходит:
1. Загружается только button.tsx
2. Никаких лишних модулей
```

### Когда barrel-файлы оправданы

1. **Public API пакета в монорепо** -- `exports` в `package.json` определяет контракт:

```jsonc
// packages/ui/package.json
{
  "name": "@repo/ui",
  "exports": {
    "./button": "./src/button.tsx",
    "./input": "./src/input.tsx",
    "./dialog": "./src/dialog.tsx",
  },
}
```

2. **С `optimizePackageImports`** -- Next.js автоматически оптимизирует barrel-файлы для указанных пакетов.

### Рекомендация

Используйте **прямые импорты** для внутреннего кода проекта:

```typescript
// Плохо
import { Button, Input, Dialog } from '@/components/ui';

// Хорошо
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog } from '@/components/ui/dialog';
```

---

## 4.3 optimizePackageImports: конфигурация Next.js

### Как это работает

`optimizePackageImports` (добавлен в Next.js 13.5) анализирует entry point пакета. Если обнаруживается barrel-файл -- Next.js автоматически перезаписывает импорты на прямые пути к модулям. Это аналог `modularizeImports`, но полностью автоматический.

### Пакеты, оптимизированные по умолчанию

Next.js автоматически оптимизирует следующие пакеты (не нужно указывать в конфиге):

```
lucide-react             date-fns                 lodash-es
ramda                    antd                     react-bootstrap
ahooks                   @ant-design/icons        @headlessui/react
@headlessui-float/react  @heroicons/react/20/solid
@heroicons/react/24/solid                         @heroicons/react/24/outline
@visx/visx               @tremor/react            rxjs
@mui/material            @mui/icons-material      recharts
react-use                @material-ui/core        @emotion/react
@emotion/styled          tss-react/mui            @mantine/core
@mantine/hooks           react-icons/*
```

### Добавление своих пакетов

```typescript
// next.config.ts
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  experimental: {
    optimizePackageImports: [
      // Ваши пакеты с barrel-файлами
      '@repo/ui',
      '@repo/icons',
      'my-design-system',
    ],
  },
};

export default nextConfig;
```

### Верификация: Vercel Conformance

Vercel предоставляет правило `NEXTJS_MISSING_OPTIMIZE_PACKAGE_IMPORTS`, которое предупреждает, если пакет с barrel-файлом не включен в `optimizePackageImports`. Доступно в Vercel Dashboard для Enterprise-планов.

---

## 4.4 eslint-plugin-boundaries: полная конфигурация

### Установка

```bash
pnpm add -D eslint-plugin-boundaries
```

### Полная конфигурация для гибридной архитектуры

```javascript
// eslint.config.mjs
import boundaries from 'eslint-plugin-boundaries';

export default [
  {
    plugins: {
      boundaries,
    },
    settings: {
      // Определение архитектурных элементов
      'boundaries/elements': [
        { type: 'app', pattern: 'src/app/*', mode: 'folder' },
        { type: 'features', pattern: 'src/features/*', mode: 'folder' },
        { type: 'components', pattern: 'src/components/*', mode: 'folder' },
        { type: 'hooks', pattern: 'src/hooks/*', mode: 'file' },
        { type: 'services', pattern: 'src/services/*', mode: 'file' },
        { type: 'lib', pattern: 'src/lib/*', mode: 'file' },
        { type: 'types', pattern: 'src/types/*', mode: 'file' },
        { type: 'config', pattern: 'src/config/*', mode: 'file' },
        { type: 'constants', pattern: 'src/constants/*', mode: 'file' },
        { type: 'utils', pattern: 'src/utils/*', mode: 'file' },
      ],
      // Игнорировать тестовые файлы
      'boundaries/ignore': ['**/*.test.ts', '**/*.test.tsx', '**/*.spec.ts'],
    },
    rules: {
      // --- Rule 1: boundaries/dependencies ---
      // Главное правило: контролирует какие элементы могут импортировать какие
      'boundaries/dependencies': [
        2,
        {
          default: 'disallow',
          rules: [
            // app/ может импортировать всё (точка входа приложения)
            {
              from: { type: 'app' },
              allow: {
                to: {
                  type: [
                    'features',
                    'components',
                    'hooks',
                    'services',
                    'lib',
                    'types',
                    'config',
                    'constants',
                    'utils',
                  ],
                },
              },
            },
            // features/ -- бизнес-фичи, могут использовать общие ресурсы, но НЕ другие фичи
            {
              from: { type: 'features' },
              allow: {
                to: {
                  type: [
                    'components',
                    'hooks',
                    'services',
                    'lib',
                    'types',
                    'config',
                    'constants',
                    'utils',
                  ],
                },
              },
            },
            // Фича может импортировать САМУ СЕБЯ (внутренние модули)
            {
              from: { type: 'features' },
              allow: { to: { type: 'features', selector: '${from.selector}' } },
            },
            // components/ -- переиспользуемые, НЕ знают о features
            {
              from: { type: 'components' },
              allow: {
                to: {
                  type: ['components', 'hooks', 'lib', 'types', 'config', 'constants', 'utils'],
                },
              },
            },
            // hooks/ -- только чистые зависимости
            {
              from: { type: 'hooks' },
              allow: { to: { type: ['lib', 'types', 'config', 'constants', 'utils'] } },
            },
            // services/ -- серверная логика
            {
              from: { type: 'services' },
              allow: { to: { type: ['lib', 'types', 'config', 'constants', 'utils'] } },
            },
            // lib/ -- только types, config, constants, utils
            {
              from: { type: 'lib' },
              allow: { to: { type: ['types', 'config', 'constants', 'utils'] } },
            },
            // utils/ -- изолированы, могут использовать только types и constants
            {
              from: { type: 'utils' },
              allow: { to: { type: ['types', 'constants'] } },
            },
            // types/ -- полностью изолированы (только другие types)
            {
              from: { type: 'types' },
              allow: { to: { type: ['types'] } },
            },
            // config/ -- может использовать types и constants
            {
              from: { type: 'config' },
              allow: { to: { type: ['types', 'constants'] } },
            },
            // constants/ -- полностью изолированы
            {
              from: { type: 'constants' },
              allow: { to: { type: ['types'] } },
            },
          ],
        },
      ],

      // --- Rule 2: boundaries/no-unknown-files ---
      // Все файлы должны принадлежать известному элементу
      'boundaries/no-unknown-files': [1],

      // --- Rule 3: boundaries/no-unknown ---
      // Известные элементы не могут импортировать неизвестные файлы
      'boundaries/no-unknown': [2],

      // --- Rule 4: boundaries/no-ignored ---
      // Известные элементы не импортируют игнорируемые файлы
      'boundaries/no-ignored': [1],

      // --- Deprecated rules (v4, для обратной совместимости) ---
      // 'boundaries/element-types': -- заменен на boundaries/dependencies в v5
      // 'boundaries/entry-point': -- заменен на boundaries/dependencies в v5
      // 'boundaries/external': -- заменен на boundaries/dependencies в v5
    },
  },
];
```

### Визуализация графа разрешенных зависимостей

```
Граф зависимостей (стрелка = "может импортировать"):

  ┌─────┐
  │ app │ ─────────────────────────────────────────────┐
  └──┬──┘                                              │
     │                                                 │
     v                                                 v
  ┌──────────┐     ┌────────────┐     ┌──────────┐  ┌──────────┐
  │ features │ ──> │ components │ ──> │  hooks   │  │ services │
  └────┬─────┘     └─────┬──────┘     └────┬─────┘  └────┬─────┘
       │                 │                 │              │
       │    ┌────────────┼─────────────────┘              │
       │    │            │                                │
       v    v            v                                v
  ┌─────┐  ┌─────┐  ┌────────┐  ┌───────────┐  ┌───────┐
  │ lib │  │utils│  │ config │  │ constants │  │ types │
  └──┬──┘  └──┬──┘  └───┬────┘  └─────┬─────┘  └───────┘
     │        │          │             │            ^
     └────────┴──────────┴─────────────┴────────────┘
```

### Правило запрета кросс-фичевых импортов

Одна из ключевых возможностей -- запрет импортов между фичами. Фича `auth` не должна импортировать из фичи `billing` напрямую:

```
src/features/auth/components/login-form.tsx
  ✅ import { validateEmail } from '@/lib/validation';
  ✅ import { Button } from '@/components/ui/button';
  ✅ import { useAuth } from '@/features/auth/hooks/use-auth';  // та же фича
  ❌ import { useBilling } from '@/features/billing/hooks/use-billing';  // ДРУГАЯ фича!
```

Если двум фичам нужно взаимодействовать, выносите общий код в `lib/`, `hooks/` или `services/`.

---

## 4.5 eslint-plugin-import-x: порядок импортов

### Почему import-x, а не import

`eslint-plugin-import-x` -- это форк `eslint-plugin-import`, адаптированный для ESLint flat config и с поддержкой ESLint 9+/10. Оригинальный `eslint-plugin-import` имеет проблемы совместимости с flat config.

### Установка

```bash
pnpm add -D eslint-plugin-import-x eslint-import-resolver-typescript @typescript-eslint/parser
```

### Полная конфигурация

```javascript
// eslint.config.mjs
import * as importX from 'eslint-plugin-import-x';
import tsParser from '@typescript-eslint/parser';

export default [
  // Базовые пресеты
  importX.flatConfigs.recommended,
  importX.flatConfigs.typescript,

  {
    files: ['**/*.{ts,tsx,js,jsx,mjs}'],
    languageOptions: {
      parser: tsParser,
      ecmaVersion: 'latest',
      sourceType: 'module',
    },
    settings: {
      'import-x/extensions': ['.js', '.jsx', '.ts', '.tsx'],
      'import-x/internal-regex': '^@/',
    },
    rules: {
      // === Порядок импортов ===
      'import-x/order': [
        'error',
        {
          groups: [
            'builtin', // node:fs, node:path
            'external', // react, next, zod
            'internal', // @/lib, @/components
            ['parent', 'sibling'], // ../, ./
            'index', // ./
            'type', // import type { ... }
          ],
          pathGroups: [
            // React и Next.js всегда первыми среди external
            { pattern: 'react', group: 'external', position: 'before' },
            { pattern: 'react-dom/**', group: 'external', position: 'before' },
            { pattern: 'next', group: 'external', position: 'before' },
            { pattern: 'next/**', group: 'external', position: 'before' },
            // Внутренние алиасы
            { pattern: '@/components/**', group: 'internal', position: 'before' },
            { pattern: '@/features/**', group: 'internal', position: 'before' },
            { pattern: '@/lib/**', group: 'internal' },
            { pattern: '@/hooks/**', group: 'internal' },
            { pattern: '@/types/**', group: 'internal', position: 'after' },
          ],
          pathGroupsExcludedImportTypes: ['react', 'next'],
          'newlines-between': 'always',
          alphabetize: {
            order: 'asc',
            caseInsensitive: true,
          },
          warnOnUnassignedImports: true,
        },
      ],

      // === Запрет проблемных паттернов ===
      'import-x/no-cycle': ['error', { maxDepth: 5 }],
      'import-x/no-self-import': 'error',
      'import-x/no-useless-path-segments': ['error', { noUselessIndex: true }],
      'import-x/no-duplicates': ['error', { 'prefer-inline': true }],
      'import-x/no-mutable-exports': 'error',
      'import-x/no-relative-packages': 'error',

      // === Стиль импортов ===
      'import-x/first': 'error',
      'import-x/newline-after-import': ['error', { count: 1 }],
      'import-x/no-anonymous-default-export': 'warn',
      'import-x/consistent-type-specifier-style': ['error', 'prefer-top-level'],

      // === Запрет barrel-файлов для внутреннего кода ===
      'import-x/no-internal-modules': 'off', // не включаем, чтобы прямые импорты работали

      // === Неразрешенные зависимости ===
      'import-x/no-unresolved': [
        'error',
        {
          ignore: ['^@/'], // path aliases резолвит TypeScript
        },
      ],
    },
  },
];
```

### Результат: консистентный порядок импортов

```typescript
// 1. Builtin
import { readFile } from 'node:fs/promises';

// 2. External (React/Next первыми)
import React from 'react';
import { notFound } from 'next/navigation';
import { z } from 'zod';

// 3. Internal
import { Button } from '@/components/ui/button';
import { useAuth } from '@/features/auth/hooks/use-auth';
import { cn } from '@/lib/utils';
import { useDebounce } from '@/hooks/use-debounce';

// 4. Parent/Sibling
import { loginSchema } from '../schemas';
import { FormField } from './form-field';

// 5. Types
import type { User } from '@/types/user';
```

---

## 4.6 @feature-sliced/eslint-config

### Обзор

`@feature-sliced/eslint-config` -- ESLint-конфигурация для проектов, использующих архитектуру Feature-Sliced Design. Предоставляет три ключевых правила:

1. **import-order** -- порядок импортов по слоям FSD (app > pages > widgets > features > entities > shared)
2. **public-api** -- запрет импорта внутренних модулей в обход публичного API слайса
3. **layers-slices** -- валидация зависимостей между слоями (слой не может импортировать из вышестоящего)

### Установка

```bash
pnpm add -D @feature-sliced/eslint-config eslint-plugin-import eslint-plugin-boundaries
```

### Конфигурация (legacy .eslintrc)

```json
{
  "extends": ["@feature-sliced"],
  "parser": "@typescript-eslint/parser",
  "settings": {
    "import/resolver": {
      "typescript": {
        "alwaysTryTypes": true
      }
    }
  }
}
```

### Flat Config (адаптер)

Официальная flat config поддержка отсутствует (пакет в beta, v0.1.1). Существует сторонний адаптер:

```bash
pnpm add -D @uvarovag/eslint-config-feature-sliced-flat
```

### Рекомендация

Для проектов, **не использующих** строгий FSD -- предпочтительнее настроить `eslint-plugin-boundaries` вручную (секция 4.4). Это дает больше контроля и работает с flat config нативно. `@feature-sliced/eslint-config` оправдан только при полном следовании FSD-методологии.

---

## 4.7 dependency-cruiser: валидация графа зависимостей

### Что это

dependency-cruiser -- инструмент для валидации и визуализации зависимостей. В отличие от ESLint-плагинов, он работает на уровне всего проекта и создает полный граф зависимостей. Поддерживает JavaScript, TypeScript, CoffeeScript.

### Установка и инициализация

```bash
pnpm add -D dependency-cruiser

# Создать начальную конфигурацию
npx depcruise --init
# Создаст .dependency-cruiser.cjs с набором разумных правил
```

### Полная конфигурация для Next.js проекта

```javascript
// .dependency-cruiser.cjs
/** @type {import('dependency-cruiser').IConfiguration} */
module.exports = {
  forbidden: [
    // === Правило 1: Запрет циклических зависимостей ===
    {
      name: 'no-circular',
      severity: 'error',
      comment: 'Циклические зависимости усложняют рефакторинг и ломают tree-shaking',
      from: {},
      to: { circular: true },
    },

    // === Правило 2: features/ не импортируют друг друга ===
    {
      name: 'no-cross-feature-imports',
      severity: 'error',
      comment: 'Фичи изолированы. Общий код -- в lib/, hooks/, services/',
      from: { path: '^src/features/([^/]+)/.+' },
      to: {
        path: '^src/features/([^/]+)/.+',
        pathNot: '^src/features/$1/.+', // $1 ссылается на захваченную группу из from
      },
    },

    // === Правило 3: components/ не зависят от features/ ===
    {
      name: 'no-components-to-features',
      severity: 'error',
      comment: 'Компоненты -- переиспользуемые, не должны знать о бизнес-фичах',
      from: { path: '^src/components/' },
      to: { path: '^src/features/' },
    },

    // === Правило 4: lib/ не зависит от components/, features/, app/ ===
    {
      name: 'no-lib-to-upper-layers',
      severity: 'error',
      comment: 'lib/ -- нижний слой, не зависит от UI и бизнес-логики',
      from: { path: '^src/lib/' },
      to: { path: '^src/(components|features|app|hooks|services)/' },
    },

    // === Правило 5: utils/ полностью изолированы ===
    {
      name: 'no-utils-to-project-code',
      severity: 'error',
      comment: 'utils/ -- чистые функции без зависимостей от проектного кода',
      from: { path: '^src/utils/' },
      to: {
        path: '^src/(components|features|app|hooks|services|lib)/',
      },
    },

    // === Правило 6: Запрет прямых импортов node_modules ===
    {
      name: 'no-orphan-dependencies',
      severity: 'warn',
      comment: 'Зависимость используется, но не указана в package.json',
      from: {},
      to: {
        dependencyTypes: ['npm-no-pkg', 'npm-unknown'],
      },
    },

    // === Правило 7: Запрет dev-зависимостей в production-коде ===
    {
      name: 'no-dev-deps-in-production',
      severity: 'error',
      comment: 'Production-код не должен зависеть от devDependencies',
      from: {
        path: '^src/',
        pathNot: '\\.(test|spec|stories)\\.(ts|tsx|js|jsx)$',
      },
      to: {
        dependencyTypes: ['npm-dev'],
      },
    },

    // === Правило 8: Server-only код не импортируется в client ===
    {
      name: 'no-server-in-client',
      severity: 'error',
      comment: 'Файлы с "use client" не должны импортировать серверную логику',
      from: { path: '^src/.*\\.client\\.' },
      to: { path: '^src/services/' },
    },
  ],

  options: {
    // TypeScript
    tsPreCompilationDeps: true,
    tsConfig: { fileName: 'tsconfig.json' },

    // Директории для анализа
    doNotFollow: {
      path: 'node_modules',
    },

    // Исключения
    exclude: {
      path: ['\\.(test|spec|stories)\\.', '__tests__', '__mocks__', '\\.d\\.ts$'],
    },

    // Reporter
    reporterOptions: {
      dot: {
        theme: {
          graph: { rankdir: 'TB', splines: 'ortho' },
          node: { shape: 'box', style: 'rounded' },
          modules: [
            { criteria: { source: '^src/app/' }, attributes: { fillcolor: '#ffcccc' } },
            { criteria: { source: '^src/features/' }, attributes: { fillcolor: '#ccffcc' } },
            { criteria: { source: '^src/components/' }, attributes: { fillcolor: '#ccccff' } },
            { criteria: { source: '^src/lib/' }, attributes: { fillcolor: '#ffffcc' } },
          ],
        },
      },
    },
  },
};
```

### Команды

```bash
# Валидация зависимостей по правилам
npx depcruise src --config

# Генерация SVG-графа
npx depcruise src --config --output-type dot | dot -T svg > dependency-graph.svg

# Проверка только циклических зависимостей
npx depcruise src --config --output-type err --focus "^src/features"

# Граф конкретной директории
npx depcruise src/features/auth --config --output-type dot | dot -T svg > auth-deps.svg
```

### Интеграция с CI

```jsonc
// package.json
{
  "scripts": {
    "deps:validate": "depcruise src --config",
    "deps:graph": "depcruise src --config --output-type dot | dot -T svg > docs/dependency-graph.svg",
    "deps:circular": "depcruise src --config --output-type err",
  },
}
```

---

## 4.8 Madge: визуализация и обнаружение циклов

### Что это

Madge -- легковесный инструмент для визуализации графа зависимостей и обнаружения циклических зависимостей. Проще в настройке, чем dependency-cruiser, но с меньшим набором правил.

### Установка

```bash
pnpm add -D madge

# Для генерации изображений требуется Graphviz
# Ubuntu/Debian: sudo apt install graphviz
# macOS: brew install graphviz
# Arch: sudo pacman -S graphviz
```

### Конфигурация

```jsonc
// .madgerc
{
  "fileExtensions": ["ts", "tsx", "js", "jsx"],
  "excludeRegExp": [
    "node_modules",
    "\\.test\\.",
    "\\.spec\\.",
    "\\.stories\\.",
    "__tests__",
    "__mocks__",
  ],
  "tsConfig": "tsconfig.json",
  "detectiveOptions": {
    "ts": {
      "skipTypeImports": true,
      "skipAsyncImports": false,
    },
  },
}
```

### CLI-команды

```bash
# Обнаружение циклических зависимостей
npx madge --circular src/

# Визуализация графа зависимостей
npx madge --image deps.svg src/

# Вывод дерева зависимостей конкретного файла
npx madge --depends src/features/auth/hooks/use-auth.ts src/

# Поиск "осиротевших" модулей (без импортов)
npx madge --orphans src/

# Модули без зависимостей (листья)
npx madge --leaves src/

# JSON-вывод для интеграции
npx madge --json src/

# Граф с определенным layout
npx madge --image deps.svg --layout fdp src/
```

### Программный API (для CI/CD)

```typescript
// scripts/check-circular.ts
import madge from 'madge';

async function checkCircularDeps() {
  const result = await madge('src/', {
    fileExtensions: ['ts', 'tsx'],
    tsConfig: 'tsconfig.json',
    detectiveOptions: {
      ts: { skipTypeImports: true },
    },
  });

  const circular = result.circular();

  if (circular.length > 0) {
    console.error(`Found ${circular.length} circular dependencies:\n`);
    circular.forEach((cycle, i) => {
      console.error(`  ${i + 1}. ${cycle.join(' -> ')}`);
    });
    process.exit(1);
  }

  console.log('No circular dependencies found.');
}

checkCircularDeps();
```

### Интеграция в package.json

```jsonc
// package.json
{
  "scripts": {
    "check:circular": "madge --circular src/",
    "check:graph": "madge --image docs/dependency-graph.svg src/",
    "check:orphans": "madge --orphans src/",
  },
}
```

### Madge vs dependency-cruiser

| Критерий              | Madge                            | dependency-cruiser                |
| --------------------- | -------------------------------- | --------------------------------- |
| Настройка             | Минимальная, работает из коробки | Требуется конфигурация правил     |
| Кастомные правила     | Нет (только циклы + orphans)     | Да (forbidden, allowed, required) |
| Визуализация          | Встроенная (`--image`)           | Через Graphviz pipe               |
| Архитектурные границы | Нет                              | Да (regex-based rules)            |
| CI/CD интеграция      | Exit code 1 при циклах           | Exit code + детальный отчет       |
| Скорость              | Быстрее на малых проектах        | Лучше масштабируется              |
| **Рекомендация**      | MVP, малые проекты               | Enterprise, строгие правила       |

---

## 4.9 Стратегии обнаружения и устранения циклических зависимостей

### Почему циклы опасны

1. **Нарушают tree-shaking** -- бандлер не может определить, что можно удалить
2. **Undefined на момент импорта** -- в CommonJS/ESM порядок инициализации непредсказуем
3. **Усложняют рефакторинг** -- невозможно перенести модуль без "потянуть за собой" цепочку
4. **Увеличивают bundle size** -- весь цикл загружается целиком

### Типичные паттерны циклов и решения

**Паттерн 1: Взаимный импорт компонентов**

```
// ПРОБЛЕМА: A -> B -> A
// user-card.tsx imports user-avatar.tsx
// user-avatar.tsx imports user-card.tsx (для tooltip)

// РЕШЕНИЕ: Extract shared logic
// user-card.tsx -> user-avatar.tsx -> avatar-tooltip.tsx
//                                     (новый компонент без обратной зависимости)
```

**Паттерн 2: Типы создают циклы**

```typescript
// ПРОБЛЕМА:
// user.service.ts imports { Order } from './order.types'
// order.service.ts imports { User } from './user.types'
// user.types.ts imports { Order } from './order.types'  -- ok
// order.types.ts imports { User } from './user.types'  -- цикл!

// РЕШЕНИЕ: Вынести общие типы
// src/types/shared.ts -- { User, Order, UserWithOrders }
// Оба сервиса импортируют из shared.ts
```

**Паттерн 3: Хуки зависят друг от друга**

```typescript
// ПРОБЛЕМА:
// useAuth.ts -> useUser.ts -> useAuth.ts

// РЕШЕНИЕ: Dependency Inversion
// useAuth.ts -- standalone, только auth-логика
// useUser.ts -- принимает userId как аргумент, не знает об auth
// useAuthenticatedUser.ts -- композиция: useAuth() + useUser(auth.userId)
```

**Паттерн 4: Barrel-файлы маскируют циклы**

```
// ПРОБЛЕМА: index.ts реэкспортирует всё, создавая скрытые циклы
// src/features/auth/index.ts exports everything
// src/features/auth/hooks/use-auth.ts imports from '../index.ts'
//   -> index.ts re-exports use-auth.ts -> ЦИКЛ

// РЕШЕНИЕ: Прямые импорты (без barrel-файлов для внутреннего кода)
```

### Стратегия "Dependency Inversion" для разрыва циклов

```
ДО (цикл):
  ┌─────────┐       ┌─────────┐
  │ ModuleA │ ───-> │ ModuleB │
  │         │ <──── │         │
  └─────────┘       └─────────┘

ПОСЛЕ (inversion):
  ┌─────────┐       ┌───────────────┐       ┌─────────┐
  │ ModuleA │ ───-> │ InterfaceB    │ <──── │ ModuleB │
  │         │       │ (types only)  │       │         │
  └─────────┘       └───────────────┘       └─────────┘
```

Выносим интерфейс (типы) в отдельный модуль. ModuleA зависит от интерфейса, ModuleB реализует его. Цикл разорван.

### Автоматизация обнаружения

```jsonc
// package.json -- единая точка проверки
{
  "scripts": {
    "lint:deps": "depcruise src --config",
    "lint:circular": "madge --circular --extensions ts,tsx src/",
    "lint:all": "pnpm lint:deps && pnpm lint:circular && pnpm lint",
  },
}
```

---

## 4.10 Пошаговое руководство: внедрение границ в существующий проект

### Шаг 1: Аудит текущего состояния (день 1)

```bash
# Установить инструменты
pnpm add -D madge dependency-cruiser eslint-plugin-boundaries eslint-plugin-import-x

# Сгенерировать граф зависимостей
npx madge --image current-deps.svg src/

# Найти все циклические зависимости
npx madge --circular --extensions ts,tsx src/
# Записать количество: например, "Found 23 circular dependencies"

# Инициализировать dependency-cruiser
npx depcruise --init
```

### Шаг 2: Определить архитектурные элементы (день 1)

Проанализировать текущую структуру папок и определить, какие элементы существуют:

```bash
# Посмотреть верхнеуровневую структуру
ls -d src/*/
```

Зафиксировать элементы в `boundaries/elements` (секция 4.4).

### Шаг 3: Начать с `warn`, не `error` (неделя 1)

```javascript
// eslint.config.mjs -- первый этап, только warnings
rules: {
  'boundaries/dependencies': [1, { /* warn, не error */ }],
  'import-x/no-cycle': ['warn', { maxDepth: 3 }],
}
```

Запустить линтер, посчитать количество нарушений:

```bash
npx eslint src/ --format compact 2>&1 | grep "boundaries/" | wc -l
# Например: "147 нарушений"
```

### Шаг 4: Устранить критичные нарушения (недели 2-4)

Приоритеты:

1. **Циклические зависимости** -- ломают runtime, исправить первыми
2. **components/ -> features/** -- нарушает переиспользуемость
3. **lib/ -> верхние слои** -- нарушает изоляцию утилит
4. **Кросс-фичевые импорты** -- выносить общий код в shared-слои

```bash
# Отслеживать прогресс
npx madge --circular --extensions ts,tsx src/ | wc -l
# Неделя 1: 23 цикла
# Неделя 2: 12 циклов
# Неделя 3: 3 цикла
# Неделя 4: 0 циклов
```

### Шаг 5: Переключить на `error` (неделя 5)

```javascript
rules: {
  'boundaries/dependencies': [2, { /* error */ }],
  'import-x/no-cycle': ['error', { maxDepth: 5 }],
}
```

### Шаг 6: Добавить в CI (неделя 5)

```yaml
# .github/workflows/lint.yml
name: Architecture Check
on: [pull_request]
jobs:
  boundaries:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: pnpm
      - run: pnpm install --frozen-lockfile
      - run: pnpm lint:deps
      - run: pnpm lint:circular
      - run: pnpm lint
```

### Шаг 7: Документировать и поддерживать

Добавить в CONTRIBUTING.md или CLAUDE.md:

```markdown
## Architecture Boundaries

- features/ не импортируют друг друга
- components/ не зависят от features/
- lib/ и utils/ -- нижний слой, без обратных зависимостей
- Циклические зависимости запрещены (проверяется в CI)
- Используйте прямые импорты вместо barrel-файлов
```

---

## Источники

- [Next.js: Absolute Imports and Module Path Aliases](https://nextjs.org/docs/app/building-your-application/configuring/absolute-imports-and-module-aliases)
- [Next.js: optimizePackageImports](https://nextjs.org/docs/app/api-reference/config/next-config-js/optimizePackageImports)
- [Vercel: How We Optimized Package Imports in Next.js](https://vercel.com/blog/how-we-optimized-package-imports-in-next-js)
- [Atlassian: 75% Faster Builds by Removing Barrel Files](https://www.atlassian.com/blog/atlassian-engineering/faster-builds-when-removing-barrel-files)
- [TkDodo: Please Stop Using Barrel Files](https://tkdodo.eu/blog/please-stop-using-barrel-files)
- [eslint-plugin-boundaries (GitHub)](https://github.com/javierbrea/eslint-plugin-boundaries)
- [JS Boundaries Documentation](https://www.jsboundaries.dev/docs/overview/)
- [eslint-plugin-import-x (npm)](https://www.npmjs.com/package/eslint-plugin-import-x)
- [eslint-plugin-import-x DeepWiki](https://deepwiki.com/un-ts/eslint-plugin-import-x/2.1-installation-and-basic-configuration)
- [dependency-cruiser (GitHub)](https://github.com/sverweij/dependency-cruiser)
- [dependency-cruiser Rules Reference](https://github.com/sverweij/dependency-cruiser/blob/main/doc/rules-reference.md)
- [Madge (npm)](https://www.npmjs.com/package/madge)
- [Madge Circular Dependency Detection (DeepWiki)](https://deepwiki.com/pahen/madge/4.4-circular-dependency-detection)
- [@feature-sliced/eslint-config (GitHub)](https://github.com/feature-sliced/eslint-config)
- [Feature-Sliced Design: Mastering ESLint Config](https://feature-sliced.design/blog/mastering-eslint-config)
- [TypeScript Path Aliases: Why Your Prefix Choice Matters](https://medium.com/@LRNZ09/typescript-path-aliases-why-your-prefix-choice-matters-more-than-you-think-787963f27429)
- [Vercel Conformance: NEXTJS_MISSING_OPTIMIZE_PACKAGE_IMPORTS](https://vercel.com/docs/conformance/rules/NEXTJS_MISSING_OPTIMIZE_PACKAGE_IMPORTS)
- [Next.js + TypeScript Monorepo Discussion](https://github.com/vercel/next.js/discussions/50866)
- [The Hidden Next.js Performance Killer: Barrel Exports](https://javascript.plainenglish.io/the-hidden-next-js-performance-killer-how-barrel-exports-are-secretly-destroying-your-bundle-size-c56ce1563cef)
- [Barrel Files: Why You Should Stop Using Them (DEV Community)](https://dev.to/tassiofront/barrel-files-and-why-you-should-stop-using-them-now-bc4)
- [ESLint v10: Flat Config Completion (InfoQ)](https://www.infoq.com/news/2026/04/eslint-10-release/)

---

# 5. Монорепо: Turborepo, Nx и внутренние пакеты

# 6. Примеры из реальных enterprise-проектов

# 7. Расширенные рекомендации

> Глубокое исследование инструментов монорепо, реальных архитектур и практических рекомендаций.
> Дата: апрель 2026.

---

## 5. Монорепо: Turborepo, Nx и внутренние пакеты

### 5.1 Turborepo vs Nx: детальное сравнение (2025-2026)

| Критерий                              | Turborepo                                      | Nx                                                        |
| ------------------------------------- | ---------------------------------------------- | --------------------------------------------------------- |
| **Философия**                         | Быстрый task runner поверх npm/pnpm workspaces | Полноценный monorepo-фреймворк ("ОС для монорепо")        |
| **Написан на**                        | Rust (с v1.7+)                                 | Node.js                                                   |
| **Скорость warm cache**               | ~1.5 сек                                       | ~3 сек                                                    |
| **Скорость cold cache (2-5 пакетов)** | ~2.8 сек (в ~3x быстрее)                       | ~8.3 сек                                                  |
| **Производительность 50+ пакетов**    | Хорошая                                        | Отличная (до 7x быстрее за счёт project graph)            |
| **Кеширование**                       | Локальное + Remote (Vercel)                    | Локальное + Remote (Nx Cloud, бесплатный тир 500ч/мес)    |
| **Модульные границы**                 | Нет встроенных                                 | Есть (enforce через ESLint правила и tags)                |
| **Генераторы кода**                   | Нет встроенных                                 | Обширные (scaffolding для React, Angular, NestJS и др.)   |
| **Граф зависимостей**                 | Базовая визуализация                           | Интерактивный визуальный граф + affected detection        |
| **Distributed CI**                    | Нет                                            | Есть (Nx Cloud распределяет задачи по машинам)            |
| **Поддержка языков**                  | Только JS/TS                                   | Polyglot: JS, Java, .NET, Go, Python                      |
| **Конфигурация**                      | Один `turbo.json`                              | `nx.json` + `project.json` для каждого проекта            |
| **Кривая обучения**                   | Низкая (~15 мин setup)                         | Высокая (project graphs, tags, executors, generators)     |
| **AI-интеграция**                     | Нет                                            | `nx configure-ai-agents` для автономных агентов           |
| **Экосистема плагинов**               | Минимальная (generic task runner)              | Обширная (Next.js, React, Angular, NestJS, Cypress и др.) |
| **Стоимость remote cache**            | Vercel usage-based (может быть дорого)         | Nx Cloud: бесплатный тир 500 ч/мес                        |
| **Публикация пакетов**                | Нет встроенной                                 | Через плагин (+ Lerna v6 использует Nx под капотом)       |

#### Рекомендации по размеру команды

| Размер команды      | Рекомендация                                                |
| ------------------- | ----------------------------------------------------------- |
| 1-3 разработчика    | Базовые npm/pnpm workspaces без дополнительных инструментов |
| 3-15 разработчиков  | **Turborepo** -- оптимальное соотношение простоты к пользе  |
| 15-50 разработчиков | Оба подходят; гибрид Turborepo + Nx Cloud для кеширования   |
| 50+ разработчиков   | **Nx** -- governance-функции оправдывают сложность          |

> **Важный инсайт:** "Многие команды используют Turborepo для оркестрации задач, но Nx Cloud для remote caching" -- инструменты совместимы и можно выбирать компоненты по мере роста потребностей.

> **Ключевая мысль:** "Разница между Turborepo и Nx значительно меньше, чем разница между любым из них и отсутствием инструмента монорепо вообще."

---

### 5.2 Типичная структура Turborepo + pnpm

```
my-enterprise/
├── apps/
│   ├── web/                # Next.js основное приложение
│   │   ├── src/
│   │   │   ├── app/        # App Router
│   │   │   ├── components/
│   │   │   ├── features/
│   │   │   └── lib/
│   │   ├── next.config.ts
│   │   ├── package.json
│   │   └── tsconfig.json
│   ├── admin/              # Next.js админ-панель
│   ├── docs/               # Документация (Mintlify / Nextra)
│   ├── api/                # Standalone API (Express / Hono)
│   └── storybook/          # Storybook для UI-компонентов
├── packages/
│   ├── ui/                 # Shared UI-компоненты (@repo/ui)
│   ├── db/                 # Prisma / Drizzle схема + клиент (@repo/db)
│   ├── auth/               # Общая логика аутентификации (@repo/auth)
│   ├── email/              # Email-шаблоны (React Email) (@repo/email)
│   ├── lib/                # Shared утилиты (@repo/lib)
│   ├── types/              # Shared TypeScript-типы (@repo/types)
│   ├── eslint-config/      # Shared ESLint конфигурация (@repo/eslint-config)
│   ├── typescript-config/  # Shared tsconfig (@repo/typescript-config)
│   └── tailwind-config/    # Shared Tailwind конфигурация (@repo/tailwind-config)
├── turbo.json              # Конфигурация Turborepo
├── pnpm-workspace.yaml     # Определение workspace
├── package.json            # Root package.json (private: true)
├── .npmrc                  # pnpm настройки
└── .gitignore
```

---

### 5.3 Конфигурация pnpm-workspace.yaml

```yaml
# pnpm-workspace.yaml
packages:
  - 'apps/*'
  - 'packages/*'
```

**Root package.json:**

```jsonc
{
  "name": "my-enterprise",
  "private": true,
  "packageManager": "pnpm@9.15.0",
  "scripts": {
    "build": "turbo run build",
    "dev": "turbo run dev",
    "lint": "turbo run lint",
    "test": "turbo run test",
    "check-types": "turbo run check-types",
    "clean": "turbo run clean",
    "format": "prettier --write \"**/*.{ts,tsx,md}\"",
  },
  "devDependencies": {
    "prettier": "^3.4.0",
    "turbo": "^2.4.0",
  },
}
```

> **Важное ограничение:** Turborepo не поддерживает вложенные пакеты типа `apps/**` или `packages/**` -- каждый пакет должен иметь свой `package.json` на первом уровне вложенности.

---

### 5.4 Полная конфигурация turbo.json с task pipeline

```jsonc
// turbo.json
{
  "$schema": "https://turborepo.dev/schema.json",

  // Глобальные зависимости -- изменение этих файлов инвалидирует кеш ВСЕХ задач
  "globalDependencies": ["tsconfig.json", ".env.production", ".env.local"],

  // Глобальные переменные окружения, влияющие на все хеши задач
  "globalEnv": ["NODE_ENV", "VERCEL_URL"],

  // Режим переменных окружения: "strict" фильтрует только указанные
  "envMode": "strict",

  // UI-режим терминала: "tui" (интерактивный) или "stream" (потоковый)
  "ui": "stream",

  // Максимальная параллельность (число или процент от ядер CPU)
  "concurrency": "80%",

  "tasks": {
    // ── BUILD ──────────────────────────────────────────────
    "build": {
      // ^build = сначала собери все зависимости этого пакета
      "dependsOn": ["^build"],
      // Какие файлы кешировать после успешной сборки
      "outputs": [".next/**", "!.next/cache/**", "dist/**"],
      // Какие файлы учитывать при определении изменений
      "inputs": ["src/**", "package.json", "tsconfig.json", "next.config.ts", "tailwind.config.ts"],
      // Переменные окружения, влияющие на хеш этой задачи
      "env": ["DATABASE_URL", "NEXT_PUBLIC_*"],
    },

    // ── LINT ───────────────────────────────────────────────
    "lint": {
      "dependsOn": ["^check-types"],
      "inputs": ["src/**", "eslint.config.mjs", "package.json"],
      "outputs": [],
    },

    // ── CHECK-TYPES ────────────────────────────────────────
    "check-types": {
      "dependsOn": ["^check-types"],
      "inputs": ["src/**", "tsconfig.json", "package.json"],
      "outputs": [],
    },

    // ── TEST ───────────────────────────────────────────────
    "test": {
      // Сначала build, потом test (в том же пакете)
      "dependsOn": ["build"],
      "inputs": ["src/**", "tests/**", "vitest.config.ts"],
      "outputs": ["coverage/**"],
      "env": ["DATABASE_URL", "TEST_DATABASE_URL"],
    },

    // ── DEV ────────────────────────────────────────────────
    "dev": {
      // Кеш отключён для dev-серверов
      "cache": false,
      // persistent = долгоживущий процесс (dev server)
      "persistent": true,
      // interruptible = turbo watch может перезапускать при изменениях
      "interruptible": true,
    },

    // ── CLEAN ──────────────────────────────────────────────
    "clean": {
      "cache": false,
      "outputs": [],
    },

    // ── DB ─────────────────────────────────────────────────
    "db:generate": {
      "cache": false,
      "outputs": [],
    },
    "db:push": {
      "cache": false,
      "outputs": [],
    },
  },
}
```

#### Типы зависимостей в `dependsOn`

| Синтаксис          | Значение                                                | Пример                                |
| ------------------ | ------------------------------------------------------- | ------------------------------------- |
| `"^build"`         | Сначала выполни `build` во **всех зависимостях** пакета | UI-пакет собирается до web-приложения |
| `"lint"`           | Сначала выполни `lint` **в том же пакете**              | Тесты запускаются только после линта  |
| `"@repo/db#build"` | Сначала выполни `build` **в конкретном пакете**         | Web ждёт сборку базы данных           |

#### Специальные переменные в `inputs`

| Переменная        | Значение                                                         |
| ----------------- | ---------------------------------------------------------------- |
| `$TURBO_DEFAULT$` | Восстанавливает значения по умолчанию (для исключения паттернов) |
| `$TURBO_ROOT$`    | Путь относительно корня репозитория, а не пакета                 |

---

### 5.5 Internal Packages Pattern: три стратегии компиляции

Turborepo предлагает три стратегии работы с внутренними пакетами:

#### 5.5.1 Just-in-Time (JIT) пакеты -- рекомендуемый подход

Пакет экспортирует TypeScript напрямую, компиляция происходит бандлером приложения-потребителя (Turbopack, webpack, Vite).

```jsonc
// packages/ui/package.json
{
  "name": "@repo/ui",
  "type": "module",
  "exports": {
    "./button": "./src/button.tsx",
    "./input": "./src/input.tsx",
    "./dialog": "./src/dialog.tsx",
    "./data-table": "./src/data-table.tsx",
    "./card": "./src/card.tsx",
  },
  "scripts": {
    "lint": "eslint . --max-warnings 0",
    "check-types": "tsc --noEmit",
  },
  "devDependencies": {
    "@repo/eslint-config": "workspace:*",
    "@repo/typescript-config": "workspace:*",
    "typescript": "^5.8.0",
  },
  "peerDependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
  },
}
```

**Плюсы:** минимальная конфигурация, нет отдельного build-шага, мгновенные изменения при разработке.

**Минусы:** не кешируется Turborepo (нет build output), ошибки TS пробрасываются в приложение-потребитель.

#### 5.5.2 Compiled пакеты

Пакет компилируется самостоятельно через `tsc`, результат попадает в `dist/`.

```jsonc
// packages/lib/package.json
{
  "name": "@repo/lib",
  "type": "module",
  "exports": {
    "./utils": {
      "types": "./src/utils.ts",
      "default": "./dist/utils.js",
    },
    "./cn": {
      "types": "./src/cn.ts",
      "default": "./dist/cn.js",
    },
    "./constants": {
      "types": "./src/constants.ts",
      "default": "./dist/constants.js",
    },
  },
  "scripts": {
    "build": "tsc",
    "dev": "tsc --watch",
    "check-types": "tsc --noEmit",
  },
  "devDependencies": {
    "@repo/typescript-config": "workspace:*",
    "typescript": "^5.8.0",
  },
}
```

**Плюсы:** кешируется Turborepo (`dist/**` в outputs), работает с любыми инструментами (не только бандлерами).

**Минусы:** требуется отдельный build-шаг, более сложная конфигурация TypeScript.

#### 5.5.3 Publishable пакеты

Готовы к публикации в npm. Используются для open-source библиотек или пакетов, которые нужны за пределами монорепо. Рекомендуется `changesets` для управления версиями.

**Выбор стратегии:**

| Сценарий                              | Рекомендация                          |
| ------------------------------------- | ------------------------------------- |
| UI-компоненты для Next.js             | JIT -- бандлер Next.js скомпилирует   |
| Утилиты, используемые в API (Node.js) | Compiled -- Node.js не имеет бандлера |
| Публичная библиотека                  | Publishable -- нужна подготовка к npm |
| Типы и константы                      | JIT -- минимум конфигурации           |

---

### 5.6 Shared Config пакеты

#### 5.6.1 TypeScript Config (`@repo/typescript-config`)

```jsonc
// packages/typescript-config/package.json
{
  "name": "@repo/typescript-config",
  "private": true,
  "exports": {
    "./base.json": "./base.json",
    "./nextjs.json": "./nextjs.json",
    "./react-library.json": "./react-library.json",
    "./node.json": "./node.json",
  },
}
```

```jsonc
// packages/typescript-config/base.json
{
  "$schema": "https://json.schemastore.org/tsconfig",
  "compilerOptions": {
    "strict": true,
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "incremental": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
  },
  "exclude": ["node_modules", "dist"],
}
```

```jsonc
// packages/typescript-config/nextjs.json
{
  "$schema": "https://json.schemastore.org/tsconfig",
  "extends": "./base.json",
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "ES2022"],
    "jsx": "preserve",
    "noEmit": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "plugins": [{ "name": "next" }],
  },
}
```

**Использование в приложении:**

```jsonc
// apps/web/tsconfig.json
{
  "extends": "@repo/typescript-config/nextjs.json",
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"],
    },
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"],
}
```

#### 5.6.2 ESLint Config (`@repo/eslint-config`)

```jsonc
// packages/eslint-config/package.json
{
  "name": "@repo/eslint-config",
  "private": true,
  "exports": {
    "./base": "./base.js",
    "./nextjs": "./nextjs.js",
    "./react-internal": "./react-internal.js",
  },
  "dependencies": {
    "@typescript-eslint/eslint-plugin": "^8.20.0",
    "@typescript-eslint/parser": "^8.20.0",
    "eslint-config-prettier": "^10.0.0",
    "eslint-plugin-react": "^7.37.0",
    "eslint-plugin-react-hooks": "^5.1.0",
    "eslint-plugin-boundaries": "^4.3.0",
  },
  "devDependencies": {
    "eslint": "^9.18.0",
    "typescript": "^5.8.0",
  },
}
```

```javascript
// packages/eslint-config/base.js
import tseslint from '@typescript-eslint/eslint-plugin';
import tsparser from '@typescript-eslint/parser';
import prettier from 'eslint-config-prettier';

/** @type {import('eslint').Linter.Config[]} */
export default [
  {
    files: ['**/*.ts', '**/*.tsx'],
    languageOptions: {
      parser: tsparser,
      parserOptions: {
        project: true,
      },
    },
    plugins: {
      '@typescript-eslint': tseslint,
    },
    rules: {
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/consistent-type-imports': 'error',
    },
  },
  prettier,
];
```

```javascript
// packages/eslint-config/nextjs.js
import base from './base.js';
import reactPlugin from 'eslint-plugin-react';
import hooksPlugin from 'eslint-plugin-react-hooks';

/** @type {import('eslint').Linter.Config[]} */
export default [
  ...base,
  {
    plugins: {
      react: reactPlugin,
      'react-hooks': hooksPlugin,
    },
    rules: {
      'react/react-in-jsx-scope': 'off',
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
    },
    settings: {
      react: { version: 'detect' },
    },
  },
];
```

#### 5.6.3 Tailwind Config (`@repo/tailwind-config`)

```jsonc
// packages/tailwind-config/package.json
{
  "name": "@repo/tailwind-config",
  "private": true,
  "type": "module",
  "exports": {
    ".": "./tailwind.config.ts",
    "./postcss": "./postcss.config.mjs",
  },
  "devDependencies": {
    "tailwindcss": "^4.0.0",
  },
}
```

```typescript
// packages/tailwind-config/tailwind.config.ts
import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: 'class',
  content: [
    // Путь будет дополнен в приложении-потребителе
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eff6ff',
          500: '#3b82f6',
          900: '#1e3a5f',
        },
      },
      fontFamily: {
        sans: ['var(--font-geist-sans)'],
        mono: ['var(--font-geist-mono)'],
      },
    },
  },
  plugins: [],
};

export default config;
```

---

### 5.7 Remote Caching в Turborepo

Remote caching -- одна из главных причин использования Turborepo. CI не повторяет работу, уже выполненную другим разработчиком или пайплайном.

**Настройка с Vercel (2 команды):**

```bash
# Авторизация
npx turbo login

# Привязка репозитория к Vercel-проекту
npx turbo link
```

После этого:

1. При запуске задачи Turborepo автоматически отправляет outputs в Remote Cache
2. На другой машине (CI или коллега) при тех же inputs задача пропускается и outputs скачиваются из кеша
3. Артефакты подписываются HMAC-SHA256 для проверки целостности

**Альтернативы Vercel Remote Cache:**

- **Nx Cloud** -- можно использовать с Turborepo, бесплатный тир 500 ч/мес
- **Self-hosted** -- `turborepo-remote-cache` (open-source, Docker)

**Управление кешем:**

```jsonc
// turbo.json -- настройки кеша
{
  "cacheDir": ".turbo/cache", // Директория локального кеша
  "cacheMaxAge": "7d", // Автоудаление через 7 дней
  "cacheMaxSize": "10GB", // Максимальный размер кеша
}
```

---

### 5.8 Когда переходить на монорепо

| Сигнал                   | Описание                                                |
| ------------------------ | ------------------------------------------------------- |
| 2+ приложения            | web + admin, web + mobile-web, web + docs               |
| Команда 5+ разработчиков | Необходимость единого code style и shared-кода          |
| Дублирование кода        | Одни и те же утилиты, типы, компоненты в разных репо    |
| Синхронизация релизов    | Сложно поддерживать совместимость между отдельными репо |
| CI занимает >10 мин      | Remote caching может сократить до ~1-2 мин              |

---

## 6. Примеры из реальных enterprise-проектов

### 6.1 Cal.com -- open-source Calendly

**Репозиторий:** [github.com/calcom/cal.com](https://github.com/calcom/cal.com) | 42k+ stars

**Стек:** Turborepo + Yarn Workspaces, Next.js 13+ (App Router), PostgreSQL + Prisma ORM, tRPC, NextAuth.js, Zod, Tailwind CSS, Biome (вместо ESLint + Prettier), Vitest, Playwright.

```
cal.com/
├── apps/
│   ├── web/                    # Основное Next.js приложение
│   └── api/
│       ├── v1/                 # Legacy REST API
│       └── v2/                 # Modern Platform API
├── packages/
│   ├── ui/                     # Design system (@calcom/ui)
│   ├── features/               # 73 бизнес-модуля (bookings, auth, calendars, webhooks)
│   ├── lib/                    # 32 утилитарных библиотеки
│   ├── prisma/                 # Схема БД и миграции
│   ├── trpc/                   # Type-safe tRPC-роутеры (viewer, public)
│   ├── emails/                 # Email-шаблоны
│   ├── embeds/                 # Виджеты для встраивания
│   ├── app-store/              # 112 интеграций третьих сторон
│   ├── i18n/                   # Интернационализация
│   ├── platform/               # Platform SDK
│   ├── config/                 # ESLint, TypeScript конфиги
│   ├── tsconfig/               # Shared TypeScript конфигурации
│   ├── types/                  # Общие типы
│   ├── ee/                     # Enterprise Edition функционал
│   └── testing/                # Тестовые утилиты
└── turbo.json
```

**Ключевые архитектурные паттерны Cal.com:**

1. **Фичи как пакет:** 73 бизнес-модуля вынесены в `packages/features/` -- каждая фича содержит свои компоненты, логику и API
2. **Трёхуровневая архитектура API:** Controllers -> Services (бизнес-логика) -> Repositories (доступ к данным) -> Database
3. **Enterprise-функции изолированы** в `packages/ee/` -- чёткое разделение open-source и платных функций
4. **112 интеграций** организованы в `packages/app-store/` как отдельные модули
5. **Biome вместо ESLint + Prettier** -- тренд 2025-2026 на замену двух инструментов одним
6. **300+ переменных окружения** -- управляются через строгую типизацию с Zod

**9 основных моделей БД:** User, Team, EventType, Booking, Availability, Credential, Webhook, Payment, Workflow.

---

### 6.2 next-forge -- production-grade Turborepo template от Vercel

**Репозиторий:** [github.com/vercel/next-forge](https://github.com/vercel/next-forge) | 7k+ stars

**Стек:** Turborepo + Bun, Next.js, TypeScript (91.9% кода), Clerk (auth), Stripe (платежи), Resend (email), Sentry, PostHog, Tailwind CSS.

```
next-forge/
├── apps/
│   ├── web/                    # Маркетинговый сайт (port 3001)
│   ├── app/                    # Основное приложение (port 3000)
│   ├── api/                    # RESTful API сервер
│   ├── docs/                   # Документация (Mintlify)
│   ├── email/                  # Email-шаблоны (React Email)
│   └── storybook/              # UI-компоненты development
├── packages/                   # Shared-пакеты
│   ├── design-system/          # UI-компоненты
│   ├── database/               # ORM + миграции
│   └── auth/                   # Аутентификация
├── turbo/
│   └── generators/             # Turborepo generators для scaffolding
├── scripts/                    # Build/utility скрипты
└── .github/                    # CI/CD конфигурация
```

**Ключевые паттерны next-forge:**

1. **Разделение web и app:** маркетинг и основное приложение -- отдельные деплои
2. **6 приложений** -- web, app, api, docs, email, storybook -- каждое деплоится независимо
3. **Интеграция 10+ сервисов:** Stripe, Resend, Google Analytics, PostHog, Sentry, BetterStack, Arcjet
4. **AI-утилиты** встроены из коробки
5. **Real-time коллаборация:** аватары, live cursors
6. **Feature flags, webhooks, cron jobs** -- enterprise-паттерны "из коробки"
7. **Установка одной командой:** `npx next-forge@latest init`

---

### 6.3 Vercel Commerce -- эталон e-commerce на Next.js

**Репозиторий:** [github.com/vercel/commerce](https://github.com/vercel/commerce) | 11k+ stars

**Стек:** Next.js (App Router), TypeScript (99.2%), pnpm, Tailwind CSS, Server Components + Server Actions + Suspense + useOptimistic.

```
commerce/
├── app/                        # Next.js App Router
│   ├── layout.tsx
│   ├── page.tsx
│   ├── error.tsx
│   ├── search/
│   │   ├── page.tsx            # Каталог товаров
│   │   └── [collection]/
│   │       └── page.tsx        # Фильтр по коллекции
│   ├── product/
│   │   └── [handle]/
│   │       └── page.tsx        # Страница товара
│   └── api/
│       └── revalidate/
│           └── route.ts        # Webhook для ревалидации
├── components/
│   ├── cart/                   # Компоненты корзины
│   ├── grid/                   # Grid-layout товаров
│   ├── layout/                 # Navbar, Footer, Search
│   ├── product/                # Карточка товара, галерея
│   └── icons.tsx               # SVG-иконки
├── lib/
│   └── shopify/                # Абстракция провайдера
│       ├── index.ts            # API-клиент
│       ├── types.ts            # Типы
│       └── queries/            # GraphQL-запросы
└── fonts/                      # Кастомные шрифты
```

**Ключевые паттерны Vercel Commerce:**

1. **Не монорепо** -- единый Next.js проект без Turborepo, но с чистой архитектурой
2. **Провайдер-абстракция:** `lib/shopify/` -- единственное место для замены при переходе на другой e-commerce бэкенд (BigCommerce, Medusa, Saleor)
3. **Server-first:** максимальное использование Server Components, Server Actions, Suspense
4. **useOptimistic** для мгновенного UI-отклика при добавлении в корзину
5. **Webhook ревалидация** -- push-модель обновления данных от Shopify

---

### 6.4 Taxonomy от shadcn -- демо-приложение Next.js

**Репозиторий:** [github.com/shadcn-ui/taxonomy](https://github.com/shadcn-ui/taxonomy) | 18k+ stars

**Стек:** Next.js 13 (App Router), TypeScript, Tailwind CSS, Radix UI, Prisma + PlanetScale, NextAuth.js, Stripe, Contentlayer + MDX.

```
taxonomy/
├── app/                        # Next.js App Router
│   ├── layout.tsx              # Root layout
│   ├── page.tsx                # Landing page
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   ├── (dashboard)/
│   │   └── dashboard/
│   │       ├── page.tsx
│   │       ├── loading.tsx
│   │       ├── billing/page.tsx
│   │       └── settings/page.tsx
│   ├── (docs)/
│   │   └── docs/
│   │       └── [[...slug]]/page.tsx
│   ├── (marketing)/
│   │   ├── page.tsx
│   │   ├── pricing/page.tsx
│   │   └── blog/
│   │       ├── page.tsx
│   │       └── [...slug]/page.tsx
│   └── api/
│       └── auth/[...nextauth]/route.ts
├── components/                 # UI-компоненты (Radix UI)
├── config/                     # Навигация, подписки, site metadata
├── content/                    # MDX-контент (блог, документация)
├── hooks/                      # useDebounce, useLockBody, useMediaQuery
├── lib/                        # auth, db, stripe, validations, utils
├── prisma/                     # Схема базы данных
├── styles/                     # Глобальные стили
└── types/                      # TypeScript определения
```

**Ключевые паттерны Taxonomy:**

1. **Route Groups по назначению:** `(auth)`, `(dashboard)`, `(docs)`, `(marketing)` -- каждая группа со своим layout
2. **Catch-all маршруты** для документации: `[[...slug]]` -- опциональный catch-all
3. **MDX + Contentlayer** -- статический контент компилируется в типизированные данные
4. **Слоистая архитектура** без features-папки -- подходит для среднего проекта
5. **Референсная реализация** shadcn/ui паттернов

---

### 6.5 Supabase -- open-source Firebase

**Репозиторий:** [github.com/supabase/supabase](https://github.com/supabase/supabase) | 100k+ stars

**Стек:** Turborepo + pnpm Workspaces, Next.js (Studio Dashboard), TypeScript (68.7%), MDX (27.2%), Knip, Prettier.

```
supabase/
├── apps/
│   ├── studio/                 # Next.js Dashboard (основной UI)
│   │   ├── components/         # UI-компоненты дашборда
│   │   ├── pages/              # Pages Router (legacy)
│   │   ├── hooks/              # React-хуки
│   │   ├── lib/                # Утилиты
│   │   └── stores/             # State management
│   ├── docs/                   # Документация (MDX)
│   └── www/                    # Маркетинговый сайт
├── packages/                   # Shared-пакеты
│   ├── ui/                     # Design system
│   ├── common/                 # Общие утилиты
│   ├── shared-types/           # TypeScript типы
│   └── config/                 # Shared конфигурации
├── e2e/
│   └── studio/                 # E2E-тесты для Studio
├── docker/                     # Docker конфигурация
├── i18n/                       # Интернационализация
├── examples/                   # Примеры интеграций
├── turbo.jsonc                 # Turborepo конфигурация
└── pnpm-workspace.yaml         # Workspace определение
```

**Ключевые паттерны Supabase:**

1. **Studio как отдельное приложение:** полноценный Next.js дашборд с собственными stores, hooks, components
2. **3 приложения:** studio (дашборд), docs (документация), www (маркетинг)
3. **Supabase workspace как пакет:** `supabase/` директория объявлена как workspace с `package.json` для интеграции CLI-команд в `turbo.json`
4. **E2E-тесты изолированы:** `e2e/studio/` -- отдельная директория для end-to-end тестов
5. **Knip для обнаружения мёртвого кода** -- находит неиспользуемые файлы и зависимости

---

### 6.6 Next.js Enterprise Boilerplate (Blazity)

**Репозиторий:** [github.com/Blazity/next-enterprise](https://github.com/Blazity/next-enterprise) | 7.3k+ stars

**Стек:** Next.js 15 (App Router), Tailwind CSS v4, pnpm + Corepack, TypeScript (strict + ts-reset), Vitest + React Testing Library + Playwright, Storybook, OpenTelemetry, Terraform (AWS), GitHub Actions.

```
next-enterprise/
├── .github/
│   └── workflows/              # CI: bundle size, performance, tests
├── .storybook/                 # Storybook конфигурация
├── app/                        # Next.js App Router
├── components/                 # React-компоненты
├── e2e/                        # Playwright E2E тесты
├── styles/                     # Глобальные стили
├── assets/                     # Статические ресурсы
├── vitest.config.ts            # Unit-тесты
├── playwright.config.ts        # E2E-тесты
└── terraform/                  # AWS Infrastructure as Code
    ├── vpc/                    # VPC изоляция
    ├── ecs/                    # Container orchestration
    ├── ecr/                    # Image registry
    ├── alb/                    # Application Load Balancer
    ├── s3-cloudfront/          # CDN
    ├── waf/                    # Web Application Firewall
    └── redis/                  # Кеширование
```

**Ключевые паттерны Blazity:**

1. **Не монорепо** -- единый Next.js проект с фокусом на DevOps
2. **Terraform IaC:** полная AWS-инфраструктура (VPC, ECS, ECR, ALB, S3, CloudFront, WAF, Redis)
3. **CI/CD из коробки:** GitHub Actions с bundle size tracking и performance monitoring
4. **CVA (Class Variance Authority)** для design system
5. **OpenTelemetry** для observability
6. **T3 Env** для типизированных переменных окружения
7. **Health checks** совместимые с Kubernetes
8. **Semantic Release** для автоматизированного changelog

---

### 6.7 Next.js Boilerplate (ixartz)

**Репозиторий:** [github.com/ixartz/Next-js-Boilerplate](https://github.com/ixartz/Next-js-Boilerplate) | 10k+ stars

**Стек:** Next.js 16+, React 19, Tailwind CSS 4, Drizzle ORM + PostgreSQL, Clerk (auth), Oxlint + Oxfmt (замена ESLint + Prettier), Vitest, Playwright, Storybook, Sentry, PostHog, next-intl (i18n).

```
src/
├── app/                        # Next.js App Router
│   ├── [locale]/               # Интернационализация
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── (auth)/             # Аутентификация
│   │   └── dashboard/          # Защищённые страницы
├── components/                 # React-компоненты
├── libs/                       # Конфигурации третьих библиотек
├── locales/                    # Файлы переводов (i18n)
├── models/                     # Drizzle ORM схемы
├── styles/                     # Глобальные стили
├── templates/                  # Layout-шаблоны
├── types/                      # TypeScript определения
├── utils/                      # Хелперы
└── validations/                # Zod-схемы валидации
```

**Ключевые паттерны ixartz:**

1. **Oxlint + Oxfmt** -- Rust-based замена ESLint + Prettier (в 50-100x быстрее)
2. **Drizzle ORM** -- type-safe SQL без overhead Prisma, поддержка PostgreSQL, SQLite, MySQL
3. **PGlite** для локальной разработки -- PostgreSQL в браузере/Node.js без Docker
4. **Lefthook** вместо Husky -- более быстрые git hooks
5. **next-intl** для i18n с `[locale]` route segment
6. **Colocated тесты** -- `*.test.ts` рядом с исходным кодом вместо отдельной `tests/` папки
7. **Monitoring as Code** -- Checkly тесты рядом с E2E тестами
8. **Multi-tenancy и RBAC** -- опциональные enterprise-фичи

---

## 7. Расширенные рекомендации

### Приоритизированный чеклист для нового enterprise-проекта (2025-2026)

#### Приоритет 1: Критические решения (день 1)

| #   | Рекомендация                                           | Обоснование                                                                                                                                   |
| --- | ------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **Используйте `src/` директорию**                      | Отделяет исходный код от конфигурационных файлов в корне. Поддерживается Next.js нативно.                                                     |
| 2   | **Гибридная архитектура: feature-based + layer-based** | `src/features/` для бизнес-логики, `src/components/`, `src/lib/`, `src/hooks/` для общих ресурсов. Оптимальный баланс организации и простоты. |
| 3   | **Route Groups с первого дня**                         | `(marketing)`, `(dashboard)`, `(auth)` -- разные layouts без влияния на URL. Переделка позже будет болезненной.                               |
| 4   | **TypeScript strict mode + path aliases**              | `@/*` для импортов. Без strict mode технический долг накопится незаметно.                                                                     |
| 5   | **Server Components по умолчанию**                     | `'use client'` только для интерактивных элементов. Вынесите клиентскую логику в отдельные компоненты.                                         |

#### Приоритет 2: Архитектурные решения (неделя 1)

| #   | Рекомендация                                           | Обоснование                                                                                                                                    |
| --- | ------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| 6   | **Избегайте barrel-файлов (index.ts)**                 | Atlassian зафиксировала 75% ускорение сборки после их удаления. Используйте прямые импорты: `import { Button } from '@/components/ui/button'`. |
| 7   | **Контролируйте архитектурные границы**                | `eslint-plugin-boundaries` предотвращает импорт из `features/` в `components/`. Без этого архитектура деградирует за месяцы.                   |
| 8   | **Loading/Error boundaries на каждом уровне**          | Гранулярный UX. Не более 4 уровней вложенности layout.                                                                                         |
| 9   | **Типизированные env-переменные**                      | `T3 Env` или Zod-валидация при старте -- падайте рано, а не в runtime.                                                                         |
| 10  | **ORM — ответственность бэкенд-сервисов, не Next.js.** | В frontend-only BFF проекте ORM не используется; данные приходят из API бэкенд-сервисов.                                                       |

#### Приоритет 3: Масштабирование (месяц 1-3)

| #   | Рекомендация                                  | Обоснование                                                                                                              |
| --- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| 11  | **Монорепо при 2+ приложениях**               | Turborepo + pnpm workspaces + internal packages. Не раньше, чем появится реальная потребность в шаринге кода.            |
| 12  | **JIT-пакеты для UI-компонентов**             | Экспортируйте `.tsx` напрямую -- бандлер Next.js скомпилирует. Минимум конфигурации.                                     |
| 13  | **Shared config пакеты**                      | `@repo/typescript-config`, `@repo/eslint-config`, `@repo/tailwind-config` -- единый источник правды для всех приложений. |
| 14  | **Remote caching в CI**                       | `turbo login && turbo link` -- CI не повторяет работу дважды. Экономит 5-15 минут на каждый pipeline.                    |
| 15  | **Biome или Oxlint вместо ESLint + Prettier** | Единый инструмент, написанный на Rust, в 50-100x быстрее. Cal.com и ixartz уже мигрировали.                              |

#### Приоритет 4: Enterprise-функции (месяц 3+)

| #   | Рекомендация                        | Обоснование                                                                                    |
| --- | ----------------------------------- | ---------------------------------------------------------------------------------------------- |
| 16  | **OpenTelemetry для observability** | Трейсы, метрики, логи в одном стандарте. Интегрируется с Next.js через `instrumentation.ts`.   |
| 17  | **Feature flags**                   | Отделяйте деплой от релиза. PostHog, LaunchDarkly или самописные через `@repo/flags`.          |
| 18  | **Infrastructure as Code**          | Terraform (AWS) или Pulumi. Blazity boilerplate -- готовый пример с VPC, ECS, CloudFront, WAF. |
| 19  | **Мониторинг бандла**               | `@next/bundle-analyzer` + GitHub Actions для трекинга размера при каждом PR.                   |
| 20  | **E2E-тесты как gating mechanism**  | Playwright тесты блокируют merge в main. Критические пути тестируются первыми.                 |

---

### 7.1 Quick Start Decision Tree: выбор архитектуры

```
Начало
│
├─ Сколько приложений?
│  │
│  ├─ Одно приложение
│  │  │
│  │  ├─ Масштаб проекта?
│  │  │  │
│  │  │  ├─ Маленький (до 20 страниц)
│  │  │  │  └─ ✅ Next.js + layer-based
│  │  │  │     Шаблон: ixartz/Next-js-Boilerplate
│  │  │  │
│  │  │  ├─ Средний (20-100 страниц)
│  │  │  │  └─ ✅ Next.js + гибрид (features + layers)
│  │  │  │     Шаблон: shadcn/taxonomy
│  │  │  │
│  │  │  └─ Большой (100+ страниц)
│  │  │     └─ ✅ Next.js + Feature-Sliced Design
│  │  │        или монорепо с одним приложением
│  │  │
│  │  └─ E-commerce?
│  │     └─ ✅ Vercel Commerce как основа
│  │
│  └─ Несколько приложений (web + admin + docs + ...)
│     │
│     ├─ Размер команды?
│     │  │
│     │  ├─ 3-15 человек
│     │  │  └─ ✅ Turborepo + pnpm workspaces
│     │  │     Шаблон: next-forge
│     │  │
│     │  └─ 15+ человек
│     │     │
│     │     ├─ Только JS/TS?
│     │     │  └─ ✅ Turborepo + Nx Cloud (гибрид)
│     │     │
│     │     └─ Polyglot (Java, Go, Python)?
│     │        └─ ✅ Nx (полноценный фреймворк)
│     │
│     └─ SaaS-продукт?
│        └─ ✅ next-forge (Vercel) или Cal.com как референс
│
└─ Open-source с enterprise-тиром?
   └─ ✅ Cal.com паттерн:
      packages/ee/ для платных фич,
      packages/features/ для бизнес-логики
```

---

### 7.2 Сводная таблица шаблонов

| Шаблон              | Stars | Монорепо         | Фокус          | Auth          | Тесты               | IaC           |
| ------------------- | ----- | ---------------- | -------------- | ------------- | ------------------- | ------------- |
| **next-forge**      | 7k+   | Turborepo + Bun  | SaaS fullstack | Clerk         | -                   | -             |
| **Blazity**         | 7.3k+ | Нет              | DevOps + CI/CD | -             | Vitest + Playwright | Terraform AWS |
| **ixartz**          | 10k+  | Нет              | DX + i18n      | Clerk         | Vitest + Playwright | -             |
| **Taxonomy**        | 18k+  | Нет              | shadcn/ui demo | NextAuth      | -                   | -             |
| **Cal.com**         | 42k+  | Turborepo + Yarn | Scheduling     | NextAuth      | Vitest + Playwright | Docker        |
| **Vercel Commerce** | 11k+  | Нет              | E-commerce     | -             | -                   | -             |
| **Supabase**        | 100k+ | Turborepo + pnpm | BaaS Dashboard | Supabase Auth | Playwright          | Docker        |

> **Примечание:** ORM — ответственность бэкенд-сервисов, не Next.js. Колонка ORM удалена из таблицы.

---

### 7.3 Антипаттерны: чего избегать

1. **Преждевременная монорепо** -- не создавайте монорепо для одного приложения "на будущее". Миграция в монорепо проще, чем содержание пустой инфраструктуры.

2. **Barrel-файлы везде** -- `index.ts` в каждой папке убивает производительность сборки и создаёт циклические зависимости.

3. **`git add -A` в монорепо** -- случайный коммит `node_modules`, `.env`, гигантских lock-файлов. Всегда `git add` конкретные файлы.

4. **Вложенные workspaces** (`packages/**`) -- Turborepo не поддерживает. Используйте плоскую структуру `packages/*`.

5. **TypeScript paths в JIT-пакетах** -- используйте Node.js subpath imports вместо `compilerOptions.paths`.

6. **Общий `tsconfig.json` в корне** -- каждый пакет должен иметь свой `tsconfig.json`, расширяющий shared конфиг. Иначе ломается кеширование.

7. **Монолитный UI-пакет** -- один `@repo/ui` с 200+ компонентами. Разделяйте по назначению: `@repo/ui`, `@repo/forms`, `@repo/charts`.

8. **Игнорирование `dependsOn` в turbo.json** -- без `^build` приложение может собираться до своих зависимостей, вызывая непредсказуемые ошибки.

---

## Источники

- [Turborepo: Configuration Reference](https://turborepo.dev/docs/reference/configuration)
- [Turborepo: Structuring a Repository](https://turborepo.dev/docs/crafting-your-repository/structuring-a-repository)
- [Turborepo: Creating an Internal Package](https://turborepo.dev/docs/crafting-your-repository/creating-an-internal-package)
- [Turborepo: Internal Packages](https://turborepo.dev/docs/core-concepts/internal-packages)
- [Turborepo: Remote Caching](https://turborepo.dev/docs/core-concepts/remote-caching)
- [Turborepo: Configuring Tasks](https://turborepo.dev/docs/crafting-your-repository/configuring-tasks)
- [Turborepo: Best Practices for Packages](https://github.com/vercel/turborepo/blob/main/skills/turborepo/references/best-practices/packages.md)
- [Turborepo vs Nx 2026 -- PkgPulse](https://www.pkgpulse.com/blog/turborepo-vs-nx-monorepo-2026)
- [Monorepo Tools Comparison: Turborepo vs Nx vs Lerna 2025 -- DEV Community](https://dev.to/_d7eb1c1703182e3ce1782/monorepo-tools-comparison-turborepo-vs-nx-vs-lerna-in-2025-15a6)
- [Nx vs Turborepo -- Nx Official](https://nx.dev/docs/guides/adopting-nx/nx-vs-turborepo)
- [Best Monorepo Tools in 2026 -- PkgPulse](https://www.pkgpulse.com/blog/best-monorepo-tools-2026)
- [next-forge -- GitHub](https://github.com/vercel/next-forge)
- [Cal.com Architecture Overview](https://www.mintlify.com/calcom/cal.com/developers/contributing/architecture)
- [Cal.com -- GitHub](https://github.com/calcom/cal.com)
- [Vercel Commerce -- GitHub](https://github.com/vercel/commerce)
- [shadcn/taxonomy -- GitHub](https://github.com/shadcn-ui/taxonomy)
- [Supabase Monorepo -- GitHub](https://github.com/supabase/supabase)
- [Blazity/next-enterprise -- GitHub](https://github.com/Blazity/next-enterprise)
- [ixartz/Next-js-Boilerplate -- GitHub](https://github.com/ixartz/Next-js-Boilerplate)
- [pnpm Workspaces](https://pnpm.io/workspaces)
- [Complete Monorepo Guide: pnpm + Workspace + Changesets](https://jsdev.space/complete-monorepo-guide/)
- [Setting Up Turborepo with React Native and Next.js -- Medium](https://medium.com/better-dev-nextjs-react/setting-up-turborepo-with-react-native-and-next-js-the-2025-production-guide-690478ad75af)
- [Building Complexus: Enterprise Frontend Architecture -- DEV Community](https://dev.to/josemukorivo/building-complexus-how-i-am-building-a-modern-enterprise-frontend-architecture-with-nextjs-and-48bp)
