# CI/CD, Env-менеджмент, Пакетный менеджер, Кодогенерация, Мониторинг

Детальное исследование инфраструктурных инструментов для enterprise Next.js 16+ проекта.
Дата: 2026-04-05.

---

## 1. CI/CD --- GitHub Actions (полный пайплайн)

### 1.1 Архитектура пайплайна

Стратегия: **fan-out / fan-in**. Один job `install` кеширует зависимости, затем
`lint`, `typecheck`, `test-unit`, `test-e2e` запускаются **параллельно**. Финальный
job `build` ждёт прохождения всех проверок. `concurrency` отменяет устаревшие
запуски на том же PR, сокращая расход CI-минут на 30--40%.

Оптимизация кеширования:

- Холодная установка pnpm на CI --- ~1 мин. 20 сек.
- С прогретым кешем --- ~40 сек. + ~10 сек. на сжатие.
- `.next/cache` кешируется отдельно для инкрементальных сборок.

### 1.2 Полный CI Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

env:
  NODE_VERSION: '22'
  PNPM_VERSION: '10'

jobs:
  # ─── Установка и кеширование зависимостей ────────────────────────
  install:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: pnpm/action-setup@v4
        with:
          version: ${{ env.PNPM_VERSION }}

      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'pnpm'

      - run: pnpm install --frozen-lockfile

      - uses: actions/cache/save@v4
        with:
          path: |
            node_modules
            .next/cache
          key: deps-${{ runner.os }}-${{ hashFiles('pnpm-lock.yaml') }}

  # ─── Линтинг ─────────────────────────────────────────────────────
  lint:
    needs: install
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: ${{ env.PNPM_VERSION }}
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
      - uses: actions/cache/restore@v4
        with:
          path: |
            node_modules
            .next/cache
          key: deps-${{ runner.os }}-${{ hashFiles('pnpm-lock.yaml') }}
      - run: pnpm lint
      - run: pnpm format:check

  # ─── Проверка типов ──────────────────────────────────────────────
  typecheck:
    needs: install
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: ${{ env.PNPM_VERSION }}
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
      - uses: actions/cache/restore@v4
        with:
          path: |
            node_modules
            .next/cache
          key: deps-${{ runner.os }}-${{ hashFiles('pnpm-lock.yaml') }}
      - run: pnpm typecheck

  # ─── Unit-тесты ─────────────────────────────────────────────────
  test-unit:
    needs: install
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: ${{ env.PNPM_VERSION }}
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
      - uses: actions/cache/restore@v4
        with:
          path: |
            node_modules
            .next/cache
          key: deps-${{ runner.os }}-${{ hashFiles('pnpm-lock.yaml') }}
      - run: pnpm test:coverage
      - uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: coverage/
          retention-days: 14

  # ─── E2E-тесты (Playwright) ─────────────────────────────────────
  test-e2e:
    needs: install
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: ${{ env.PNPM_VERSION }}
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
      - uses: actions/cache/restore@v4
        with:
          path: |
            node_modules
            .next/cache
          key: deps-${{ runner.os }}-${{ hashFiles('pnpm-lock.yaml') }}
      - run: pnpm exec playwright install --with-deps chromium
      - run: pnpm build
        env:
          NEXT_PUBLIC_APP_URL: http://localhost:3000
      - run: pnpm exec playwright test --project=chromium
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 7

  # ─── Сборка (только после всех проверок) ─────────────────────────
  build:
    needs: [lint, typecheck, test-unit]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: ${{ env.PNPM_VERSION }}
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
      - uses: actions/cache/restore@v4
        with:
          path: |
            node_modules
            .next/cache
          key: deps-${{ runner.os }}-${{ hashFiles('pnpm-lock.yaml') }}
      - run: pnpm build
      - uses: actions/upload-artifact@v4
        with:
          name: build-output
          path: .next/
          retention-days: 3

  # ─── Анализ размера бандла (только на PR) ────────────────────────
  bundle-analysis:
    if: github.event_name == 'pull_request'
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: build-output
          path: .next/
      - uses: hashicorp/nextjs-bundle-analysis@v0.7
        with:
          budget: 350
          red-status-percentage: 15
```

### 1.3 Ключевые оптимизации

| Приём                                 | Эффект                                                                |
| ------------------------------------- | --------------------------------------------------------------------- |
| `concurrency.cancel-in-progress`      | Отменяет устаревшие запуски --- экономия 30--40% CI-минут             |
| `pnpm/action-setup` + `cache: 'pnpm'` | Автокеширование store --- установка ~40 сек.                          |
| `actions/cache/save` + `restore`      | Переиспользование `node_modules` и `.next/cache` между jobs           |
| Параллельные jobs                     | `lint`, `typecheck`, `test-unit`, `test-e2e` выполняются одновременно |
| `--frozen-lockfile`                   | Гарантирует воспроизводимость --- никаких неявных обновлений          |
| `retention-days`                      | Ограничение хранения артефактов --- экономия storage                  |
| `hashicorp/nextjs-bundle-analysis`    | Комментарий с diff размера бандла прямо в PR                          |

---

## 2. Управление переменными окружения

### 2.1 @t3-oss/env-nextjs + Zod

Пакет `@t3-oss/env-nextjs` обеспечивает **type-safe валидацию** переменных
окружения через Zod с разделением на server/client. Ошибка при отсутствующей
переменной возникает **при старте приложения**, а не в рантайме при обращении.

```bash
pnpm add @t3-oss/env-nextjs zod
```

```typescript
// src/env.ts
import { createEnv } from '@t3-oss/env-nextjs';
import { z } from 'zod';

export const env = createEnv({
  // ── Серверные переменные (недоступны на клиенте) ──────────────
  server: {
    DATABASE_URL: z.string().url(),
    AUTH_SECRET: z.string().min(32),
    REDIS_URL: z.string().url().optional(),
    TELEGRAM_BOT_TOKEN: z.string().min(1),
    NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  },

  // ── Клиентские переменные (NEXT_PUBLIC_*) ────────────────────
  client: {
    NEXT_PUBLIC_APP_URL: z.string().url(),
    NEXT_PUBLIC_POSTHOG_KEY: z.string().min(1),
    NEXT_PUBLIC_TELEGRAM_BOT_USERNAME: z.string().min(1),
  },

  // ── Маппинг на process.env ───────────────────────────────────
  // Для Next.js < 13.4.4 нужен полный runtimeEnv.
  // Для Next.js >= 13.4.4 можно использовать experimental__runtimeEnv
  // и указывать только клиентские переменные.
  experimental__runtimeEnv: {
    NEXT_PUBLIC_APP_URL: process.env.NEXT_PUBLIC_APP_URL,
    NEXT_PUBLIC_POSTHOG_KEY: process.env.NEXT_PUBLIC_POSTHOG_KEY,
    NEXT_PUBLIC_TELEGRAM_BOT_USERNAME: process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME,
  },

  // ── Дополнительные настройки ─────────────────────────────────
  skipValidation: !!process.env.SKIP_ENV_VALIDATION,
  emptyStringAsUndefined: true,
});
```

### 2.2 Использование в коде

```typescript
// src/lib/db.ts — серверный код
import { env } from '@/env';

const db = new PrismaClient({
  datasourceUrl: env.DATABASE_URL, // type-safe, автокомплит
});
```

```typescript
// src/components/analytics.tsx — клиентский код
import { env } from '@/env';

// env.DATABASE_URL — TS-ошибка! Серверная переменная в клиентском коде.
// env.NEXT_PUBLIC_POSTHOG_KEY — OK, клиентская переменная.
```

### 2.3 Организация .env файлов

```
.env                  # Дефолтные значения (НЕ секреты), коммитится
.env.local            # Локальные секреты (в .gitignore)
.env.development      # Переопределения для dev
.env.production       # Переопределения для production
.env.test             # Переопределения для тестов
.env.example          # Шаблон с пустыми значениями (коммитится)
```

```bash
# .env.example
DATABASE_URL=postgresql://user:password@localhost:5432/mydb
AUTH_SECRET=
REDIS_URL=
TELEGRAM_BOT_TOKEN=

NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_POSTHOG_KEY=
NEXT_PUBLIC_TELEGRAM_BOT_USERNAME=
```

### 2.4 Валидация в CI

```yaml
# Добавить в job lint (или отдельный job)
- name: Validate env
  run: pnpm exec tsx src/env.ts
  env:
    DATABASE_URL: postgresql://ci:ci@localhost:5432/ci
    AUTH_SECRET: ci-secret-that-is-at-least-32-chars-long
    TELEGRAM_BOT_TOKEN: fake-token
    NEXT_PUBLIC_APP_URL: http://localhost:3000
    NEXT_PUBLIC_POSTHOG_KEY: phc_fake
    NEXT_PUBLIC_TELEGRAM_BOT_USERNAME: test_bot
```

---

## 3. Пакетный менеджер --- pnpm

### 3.1 Сравнение (актуальные данные 2026)

| Критерий                          | pnpm 10                        | Bun 1.3+                       | Yarn 4 (Berry)          | npm 11              |
| --------------------------------- | ------------------------------ | ------------------------------ | ----------------------- | ------------------- |
| Скорость установки (cold)         | 6--8x vs npm                   | 25--30x vs npm                 | 3--5x vs npm            | Базовая             |
| Экономия диска                    | **-60%** (content-addressable) | Стандартная                    | -50% (PnP/zip)          | Стандартная         |
| Монорепо                          | Отличная (workspaces)          | Базовая                        | Хорошая                 | Базовая             |
| Strict dependency resolution      | Да (по умолчанию)              | Нет                            | Да (PnP)                | Нет                 |
| Совместимость с npm-экосистемой   | Высокая                        | Бывают проблемы                | Средняя (PnP)           | Эталонная           |
| CI-кеширование                    | Отличное                       | Хорошее                        | Хорошее (zero-installs) | Базовое             |
| Поддержка patch по version ranges | Да (v10+)                      | Нет                            | Да                      | Нет                 |
| Production readiness              | Enterprise-стандарт            | Используется Anthropic, Vercel | Enterprise-готов        | Enterprise-стандарт |

**Вывод:** pnpm --- лучший баланс скорости, экономии диска и строгости зависимостей
для enterprise. Bun идеален для стартапов и greenfield-проектов, но менее предсказуем
в сложных монорепо-сценариях. Мы используем **pnpm 10**.

### 3.2 Конфигурация pnpm

```yaml
# .npmrc
engine-strict=true
auto-install-peers=true
strict-peer-dependencies=false
shamefully-hoist=false
resolution-mode=highest
```

```jsonc
// package.json (секция packageManager — corepack)
{
  "packageManager": "pnpm@10.7.0",
  "engines": {
    "node": ">=22.0.0",
    "pnpm": ">=10.0.0",
  },
}
```

```bash
# Включение corepack (гарантирует версию pnpm)
corepack enable
corepack prepare pnpm@10.7.0 --activate
```

### 3.3 Полезные команды pnpm

```bash
# Проверка неиспользуемых зависимостей
pnpm why <package>

# Обновление зависимостей интерактивно
pnpm update --interactive --latest

# Проверка уязвимостей
pnpm audit

# Очистка store (освобождение диска)
pnpm store prune
```

---

## 4. Мониторинг производительности и анализ бандла

### 4.1 Next.js Bundle Analyzer (Turbopack)

Начиная с Next.js 16, Turbopack --- **дефолтный бандлер**. Next.js 16.1 добавил
экспериментальный Bundle Analyzer, интегрированный с Turbopack module graph.

```bash
# Для Turbopack (Next.js 16.1+) — новый экспериментальный анализатор
npx next internal turbo-trace-server .next/diagnostics/analyze
```

Для Webpack-mode (fallback) используется `@next/bundle-analyzer`:

```bash
pnpm add -D @next/bundle-analyzer
```

```typescript
// next.config.ts
import type { NextConfig } from 'next';

const withBundleAnalyzer = (await import('@next/bundle-analyzer')).default({
  enabled: process.env.ANALYZE === 'true',
  openAnalyzer: true,
});

const nextConfig: NextConfig = {
  // ... конфигурация
};

export default withBundleAnalyzer(nextConfig);
```

```bash
# Запуск анализа
ANALYZE=true pnpm build
```

### 4.2 hashicorp/nextjs-bundle-analysis (CI)

GitHub Action, который автоматически комментирует PR с diff-ом размера бандла:
показывает какие роуты выросли/уменьшились и на сколько. Конфигурация показана
выше в CI workflow (секция `bundle-analysis`).

### 4.3 Lighthouse CI

```bash
pnpm add -D @lhci/cli
```

```yaml
# lighthouserc.js
module.exports = {
  ci: {
    collect: {
      url: ['http://localhost:3000/', 'http://localhost:3000/app'],
      startServerCommand: 'pnpm start',
      numberOfRuns: 3,
    },
    assert: {
      assertions: {
        'categories:performance': ['error', { minScore: 0.9 }],
        'categories:accessibility': ['error', { minScore: 0.95 }],
        'categories:best-practices': ['warn', { minScore: 0.9 }],
        'categories:seo': ['warn', { minScore: 0.9 }],
        'first-contentful-paint': ['warn', { maxNumericValue: 1800 }],
        'largest-contentful-paint': ['error', { maxNumericValue: 2500 }],
        'cumulative-layout-shift': ['error', { maxNumericValue: 0.1 }],
        'total-blocking-time': ['warn', { maxNumericValue: 200 }],
      },
    },
    upload: {
      target: 'temporary-public-storage',
    },
  },
};
```

### 4.4 why-did-you-render (отладка ре-рендеров)

```bash
pnpm add -D @welldone-software/why-did-you-render
```

```typescript
// src/lib/wdyr.ts (подключать ТОЛЬКО в development)
import React from 'react';

if (process.env.NODE_ENV === 'development') {
  const { default: whyDidYouRender } = await import('@welldone-software/why-did-you-render');
  whyDidYouRender(React, {
    trackAllPureComponents: true,
    trackHooks: true,
    logOnDifferentValues: true,
  });
}
```

### 4.5 Сводная таблица инструментов мониторинга

| Инструмент                          | Назначение                   | Когда использовать           |
| ----------------------------------- | ---------------------------- | ---------------------------- |
| Next.js Bundle Analyzer (Turbopack) | Визуализация module graph    | Отладка размера бандла (dev) |
| `@next/bundle-analyzer`             | Webpack treemap визуализация | Fallback для webpack mode    |
| `hashicorp/nextjs-bundle-analysis`  | Diff размера бандла в PR     | CI --- на каждый PR          |
| Lighthouse CI                       | Web Vitals аудит             | CI --- перед деплоем         |
| `why-did-you-render`                | Ненужные ре-рендеры          | Отладка перформанса (dev)    |
| React DevTools Profiler             | Профилирование рендер-циклов | Ручная отладка (dev)         |

---

## 5. Кодогенерация --- Plop.js

### 5.1 Установка и TypeScript-конфигурация

```bash
pnpm add -D plop
```

С Node.js 22+ TypeScript-конфиг работает **из коробки** --- не нужны дополнительные
флаги или транспиляторы.

```bash
# Инициализация TypeScript plopfile
pnpm exec plop --init-ts
```

### 5.2 Plopfile --- генераторы

```typescript
// plopfile.ts
import type { NodePlopAPI } from 'plop';

export default function (plop: NodePlopAPI) {
  // ── Генератор компонента ─────────────────────────────────────
  plop.setGenerator('component', {
    description: 'React component with test and barrel export',
    prompts: [
      {
        type: 'input',
        name: 'name',
        message: 'Component name (PascalCase):',
        validate: (value: string) => /^[A-Z][a-zA-Z0-9]+$/.test(value) || 'Must be PascalCase',
      },
      {
        type: 'list',
        name: 'type',
        message: 'Component type:',
        choices: ['ui', 'feature', 'layout'],
      },
    ],
    actions: [
      {
        type: 'add',
        path: 'src/components/{{type}}/{{pascalCase name}}/{{pascalCase name}}.tsx',
        templateFile: 'templates/component.tsx.hbs',
      },
      {
        type: 'add',
        path: 'src/components/{{type}}/{{pascalCase name}}/{{pascalCase name}}.test.tsx',
        templateFile: 'templates/component.test.tsx.hbs',
      },
      {
        type: 'add',
        path: 'src/components/{{type}}/{{pascalCase name}}/index.ts',
        templateFile: 'templates/barrel.ts.hbs',
      },
    ],
  });

  // ── Генератор хука ───────────────────────────────────────────
  plop.setGenerator('hook', {
    description: 'Custom React hook with test',
    prompts: [
      {
        type: 'input',
        name: 'name',
        message: 'Hook name (without "use" prefix):',
        validate: (value: string) => /^[A-Z][a-zA-Z0-9]+$/.test(value) || 'Must be PascalCase',
      },
    ],
    actions: [
      {
        type: 'add',
        path: 'src/hooks/use{{pascalCase name}}.ts',
        templateFile: 'templates/hook.ts.hbs',
      },
      {
        type: 'add',
        path: 'src/hooks/use{{pascalCase name}}.test.ts',
        templateFile: 'templates/hook.test.ts.hbs',
      },
    ],
  });

  // ── Генератор серверного действия ────────────────────────────
  plop.setGenerator('action', {
    description: 'Next.js Server Action',
    prompts: [
      {
        type: 'input',
        name: 'name',
        message: 'Action name (camelCase):',
      },
      {
        type: 'input',
        name: 'feature',
        message: 'Feature folder:',
      },
    ],
    actions: [
      {
        type: 'add',
        path: 'src/features/{{feature}}/actions/{{camelCase name}}.ts',
        templateFile: 'templates/server-action.ts.hbs',
      },
    ],
  });
}
```

### 5.3 Handlebars-шаблоны

```handlebars
{{!-- templates/component.tsx.hbs --}}
import type { ComponentPropsWithoutRef } from 'react';

import { cn } from '@/lib/utils';

interface {{pascalCase name}}Props extends ComponentPropsWithoutRef<'div'> {
  /** TODO: add props */
}

export function {{pascalCase name}}({
  className,
  ...props
}: {{pascalCase name}}Props) {
  return (
    <div className={cn('', className)} {...props}>
      {{pascalCase name}}
    </div>
  );
}
```

```handlebars
{{!-- templates/component.test.tsx.hbs --}}
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { {{pascalCase name}} } from './{{pascalCase name}}';

describe('{{pascalCase name}}', () => {
  it('renders without crashing', () => {
    render(<{{pascalCase name}} />);
    expect(screen.getByText('{{pascalCase name}}')).toBeInTheDocument();
  });
});
```

```handlebars
{{! templates/barrel.ts.hbs }}
export {
{{pascalCase name}}
} from './{{pascalCase name}}';
```

```handlebars
{{!-- templates/hook.ts.hbs --}}
import { useState } from 'react';

export function use{{pascalCase name}}() {
  const [state, setState] = useState<unknown>(null);

  return { state, setState } as const;
}
```

```handlebars
{{! templates/hook.test.ts.hbs }}
import { renderHook } from '@testing-library/react'; import { describe, expect, it } from 'vitest';
import { use{{pascalCase name}}
} from './use{{pascalCase name}}'; describe('use{{pascalCase name}}', () => { it('returns initial
state', () => { const { result } = renderHook(() => use{{pascalCase name}}());
expect(result.current.state).toBeNull(); }); });
```

```handlebars
{{!-- templates/server-action.ts.hbs --}}
'use server';

import { z } from 'zod';

const {{camelCase name}}Schema = z.object({
  // TODO: define input schema
});

type {{pascalCase name}}Input = z.infer<typeof {{camelCase name}}Schema>;

export async function {{camelCase name}}(input: {{pascalCase name}}Input) {
  const parsed = {{camelCase name}}Schema.safeParse(input);

  if (!parsed.success) {
    return { success: false as const, error: parsed.error.flatten() };
  }

  // TODO: implement action logic

  return { success: true as const, data: null };
}
```

---

## 6. Полный набор npm-скриптов

```jsonc
// package.json — scripts
{
  "scripts": {
    // ── Разработка ──────────────────────────────────────────────
    "dev": "next dev --turbopack",
    "dev:debug": "NODE_OPTIONS='--inspect' next dev --turbopack",

    // ── Сборка и запуск ─────────────────────────────────────────
    "build": "next build",
    "start": "next start",
    "preview": "next build && next start",

    // ── Качество кода ───────────────────────────────────────────
    "lint": "eslint .",
    "lint:fix": "eslint . --fix",
    "format": "prettier --write .",
    "format:check": "prettier --check .",
    "typecheck": "tsc --noEmit",

    // ── Тестирование ────────────────────────────────────────────
    "test": "vitest",
    "test:run": "vitest run",
    "test:coverage": "vitest run --coverage",
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui",
    "test:e2e:install": "playwright install --with-deps",

    // ── Кодогенерация ───────────────────────────────────────────
    "generate": "plop",
    "generate:component": "plop component",
    "generate:hook": "plop hook",
    "generate:action": "plop action",

    // ── Анализ и мониторинг ─────────────────────────────────────
    "analyze": "ANALYZE=true next build",
    "lighthouse": "lhci autorun",

    // ── Утилиты ─────────────────────────────────────────────────
    "clean": "rm -rf .next node_modules/.cache",
    "clean:full": "rm -rf .next node_modules",
    "deps:check": "pnpm outdated",
    "deps:update": "pnpm update --interactive --latest",

    // ── CI helpers ──────────────────────────────────────────────
    "ci:lint": "eslint . --max-warnings=0",
    "ci:test": "vitest run --coverage --reporter=json",
    "ci:e2e": "playwright test --project=chromium --reporter=json",

    // ── Pre-commit (вызывается через lint-staged) ───────────────
    "prepare": "husky",
  },
}
```

---

## 7. Итоговые рекомендации

| Категория         | Инструмент                            | Обоснование                                                 |
| ----------------- | ------------------------------------- | ----------------------------------------------------------- |
| CI/CD             | GitHub Actions (fan-out/fan-in)       | Параллельные jobs + кеширование pnpm --- пайплайн <5 мин.   |
| Env validation    | `@t3-oss/env-nextjs` + Zod            | Type-safe, fail-fast при старте, разделение server/client   |
| Пакетный менеджер | pnpm 10 + corepack                    | Строгие зависимости, -60% диска, enterprise-стандарт        |
| Bundle analysis   | Turbopack Analyzer + hashicorp action | Dev-отладка + автоматический diff в PR                      |
| Perf monitoring   | Lighthouse CI + why-did-you-render    | Automated Web Vitals + ручная отладка ре-рендеров           |
| Кодогенерация     | Plop.js (TypeScript plopfile)         | Единообразие структуры, 3 генератора: component/hook/action |

---

**Источники:**

- [GitHub Actions CI/CD for Node.js: The Complete 2026 Guide](https://axiom-experiment.hashnode.dev/github-actions-cicd-for-nodejs-the-complete-2026-guide)
- [PNPM GitHub Actions Cache](https://theodorusclarence.com/shorts/github/pnpm-github-actions-cache)
- [Next.js CI Build Caching (official docs)](https://nextjs.org/docs/pages/building-your-application/deploying/ci-build-caching)
- [Next.js Env Validation with @t3-oss/env-nextjs (2026)](https://medium.com/@the.sikandar.dev/next-js-env-validation-with-t3-oss-env-nextjs-0733778b1b73)
- [T3 Env --- Next.js docs](https://env.t3.gg/docs/nextjs)
- [pnpm vs npm vs yarn vs Bun: The 2026 Package Manager Showdown](https://dev.to/pockit_tools/pnpm-vs-npm-vs-yarn-vs-bun-the-2026-package-manager-showdown-51dc)
- [PNPM vs. Bun Install vs. Yarn Berry (Better Stack)](https://betterstack.com/community/guides/scaling-nodejs/pnpm-vs-bun-install-vs-yarn/)
- [Turbopack in 2026: The Complete Guide](https://dev.to/pockit_tools/turbopack-in-2026-the-complete-guide-to-nextjss-rust-powered-bundler-oda)
- [Next.js 16.1 --- Bundle Analyzer](https://nextjs.org/blog/next-16-1)
- [Optimizing: Bundle Analyzer (Next.js docs)](https://nextjs.org/docs/14/pages/building-your-application/optimizing/bundle-analyzer)
- [Plop.js Documentation](https://plopjs.com/documentation/)
- [Plop.js Template Creation (Perficient, 2025)](https://blogs.perficient.com/2025/03/20/plop-js-a-micro-generator-framework-template-creation-part-2/)
