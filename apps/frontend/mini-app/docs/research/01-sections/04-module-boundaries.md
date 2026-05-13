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
