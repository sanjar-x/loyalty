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

| #   | Рекомендация                                  | Обоснование                                                                                                                                            |
| --- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 6   | **Избегайте barrel-файлов (index.ts)**        | Atlassian зафиксировала 75% ускорение сборки после их удаления. Используйте прямые импорты: `import { Button } from '@/components/ui/button'`.         |
| 7   | **Контролируйте архитектурные границы**       | `eslint-plugin-boundaries` предотвращает импорт из `features/` в `components/`. Без этого архитектура деградирует за месяцы.                           |
| 8   | **Loading/Error boundaries на каждом уровне** | Гранулярный UX. Не более 4 уровней вложенности layout.                                                                                                 |
| 9   | **Типизированные env-переменные**             | `T3 Env` или Zod-валидация при старте -- падайте рано, а не в runtime.                                                                                 |
| 10  | **Выберите ORM осознанно**                    | Prisma -- зрелый, богатая экосистема, но тяжёлый. Drizzle -- легкий, type-safe SQL, быстрее. Для новых проектов в 2025-2026 Drizzle набирает momentum. |

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

| Шаблон              | Stars | Монорепо         | Фокус          | ORM     | Auth          | Тесты               | IaC           |
| ------------------- | ----- | ---------------- | -------------- | ------- | ------------- | ------------------- | ------------- |
| **next-forge**      | 7k+   | Turborepo + Bun  | SaaS fullstack | ORM     | Clerk         | -                   | -             |
| **Blazity**         | 7.3k+ | Нет              | DevOps + CI/CD | -       | -             | Vitest + Playwright | Terraform AWS |
| **ixartz**          | 10k+  | Нет              | DX + i18n      | Drizzle | Clerk         | Vitest + Playwright | -             |
| **Taxonomy**        | 18k+  | Нет              | shadcn/ui demo | Prisma  | NextAuth      | -                   | -             |
| **Cal.com**         | 42k+  | Turborepo + Yarn | Scheduling     | Prisma  | NextAuth      | Vitest + Playwright | Docker        |
| **Vercel Commerce** | 11k+  | Нет              | E-commerce     | -       | -             | -                   | -             |
| **Supabase**        | 100k+ | Turborepo + pnpm | BaaS Dashboard | -       | Supabase Auth | Playwright          | Docker        |

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
