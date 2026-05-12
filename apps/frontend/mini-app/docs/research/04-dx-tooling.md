# DX и Tooling: TypeScript, ESLint, тестирование, CI/CD и кодогенерация (2025-2026)

> **Контекст проекта:** Frontend-only Next.js приложение, часть большой системы с отдельными
> бэкенд-сервисами. Next.js выступает как BFF (Backend for Frontend) / proxy-слой.
>
> Полное исследование: TypeScript strict, ESLint v9 flat config, Prettier, Biome,
> Git hooks (Husky), Vitest, Playwright, MSW v2, CI/CD (GitHub Actions), env-менеджмент,
> pnpm, bundle analysis, Plop.js кодогенерация.

---

## Содержание

### Часть 1 — TypeScript, ESLint v9, Prettier & Biome

- [1. TypeScript — продвинутая конфигурация](#1-typescript--продвинутая-конфигурация)
- [2. ESLint v9 Flat Config](#2-eslint-v9-flat-config--полная-настройка)
- [3. Prettier — конфигурация и интеграция](#3-prettier--конфигурация-и-интеграция)
- [4. Рекомендация для проекта](#4-рекомендация-для-проекта)

### Часть 2 — Git Hooks и тестирование

- [1. Git Hooks — Husky v9 + lint-staged + commitlint](#1-git-hooks--husky-v9--lint-staged--commitlint)
- [2. Vitest — unit/integration тестирование](#2-vitest--unitintegration-тестирование)
- [3. Playwright — E2E тестирование](#3-playwright--e2e-тестирование)
- [4. MSW v2 — мокирование API](#4-msw-v2--мокирование-api)
- [5. Стратегия тестирования — пирамида](#5-стратегия-тестирования--пирамида)

### Часть 3 — CI/CD, Env, пакетный менеджер, кодогенерация, мониторинг

- [1. CI/CD — GitHub Actions](#1-cicd----github-actions-полный-пайплайн)
- [2. Управление переменными окружения](#2-управление-переменными-окружения)
- [3. Пакетный менеджер — pnpm](#3-пакетный-менеджер----pnpm)
- [4. Мониторинг производительности и анализ бандла](#4-мониторинг-производительности-и-анализ-бандла)
- [5. Кодогенерация — Plop.js](#5-кодогенерация----plopjs)
- [6. Полный набор npm-скриптов](#6-полный-набор-npm-скриптов)
- [7. Итоговые рекомендации](#7-итоговые-рекомендации)

---

# Часть 1 — TypeScript, ESLint v9, Prettier & Biome

---

## 1. TypeScript -- продвинутая конфигурация

### 1.1 Контекст

TypeScript -- самый используемый язык на GitHub (State of JS 2025: 40% пишут только на TS).
Next.js 15 генерирует `strict: true` по умолчанию, но для enterprise этого недостаточно.
TS 5.7 добавил stricter checks для `in` operator, 5.8 -- `--erasableSyntaxOnly` для
нативного запуска через Node.js 23+ `--experimental-strip-types`.

### 1.2 Полный tsconfig.json для Next.js 15+

```jsonc
{
  "$schema": "https://json.schemastore.org/tsconfig",
  "compilerOptions": {
    // STRICT MODE
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noImplicitOverride": true,
    "noPropertyAccessFromIndexSignature": true,
    "forceConsistentCasingInFileNames": true,

    // MODULE SYSTEM
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "ES2023"],
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "verbatimModuleSyntax": true,
    "esModuleInterop": true,

    // NEXT.JS
    "jsx": "preserve",
    "incremental": true,
    "skipLibCheck": true,
    "noEmit": true,

    // PATH ALIASES
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"],
      "@/components/*": ["./src/components/*"],
      "@/lib/*": ["./src/lib/*"],
      "@/hooks/*": ["./src/hooks/*"],
      "@/types/*": ["./src/types/*"],
      "@/store/*": ["./src/store/*"],
    },
    "plugins": [{ "name": "next" }],
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules", ".next", "dist", "coverage"],
}
```

### 1.3 Справочник строгих флагов

| Флаг                                 | Что делает                                      | Влияние |
| ------------------------------------ | ----------------------------------------------- | :-----: |
| `strict`                             | Включает все strict-family флаги                | Высокое |
| `noUncheckedIndexedAccess`           | `obj[key]` возвращает `T \| undefined`          | Среднее |
| `exactOptionalPropertyTypes`         | `{ a?: string }` запрещает явный `a: undefined` | Среднее |
| `noImplicitOverride`                 | Требует `override` для перезаписанных методов   | Низкое  |
| `noPropertyAccessFromIndexSignature` | Заставляет `obj["key"]` для index signatures    | Среднее |
| `verbatimModuleSyntax`               | Требует `import type { X }` для типов           | Высокое |

### 1.4 Стратегия постепенного ужесточения

```
Фаза 1: strict: true                          (1-2 спринта на фиксы)
Фаза 2: + noUncheckedIndexedAccess
Фаза 3: + exactOptionalPropertyTypes
Фаза 4: + noPropertyAccessFromIndexSignature
Фаза 5: + verbatimModuleSyntax
```

Между фазами: `// @ts-expect-error` с TODO + правило `@typescript-eslint/ban-ts-comment`.

---

## 2. ESLint v9 Flat Config -- полная настройка

### 2.1 Ключевые изменения

- **Flat config** (`eslint.config.mjs`) -- единственный формат. `.eslintrc.*` deprecated.
- **`extends`** в flat config (март 2025) -- упрощает конфигурацию.
- **typescript-eslint v8** -- единый пакет с парсером, плагином и конфигами.
- **`projectService`** -- автоматическое обнаружение tsconfig (замена `project`).
- **eslint-plugin-import-x** -- форк `eslint-plugin-import` с нативным flat config.

### 2.2 Полный eslint.config.mjs

```javascript
// eslint.config.mjs
import { dirname } from 'path';
import { fileURLToPath } from 'url';
import { FlatCompat } from '@eslint/eslintrc';
import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import importX from 'eslint-plugin-import-x';
import boundaries from 'eslint-plugin-boundaries';
import reactHooks from 'eslint-plugin-react-hooks';
import jsxA11y from 'eslint-plugin-jsx-a11y';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const compat = new FlatCompat({ baseDirectory: __dirname });

export default tseslint.config(
  // BASE
  js.configs.recommended,
  ...tseslint.configs.recommendedTypeChecked,
  ...tseslint.configs.stylisticTypeChecked,
  ...compat.extends('next/core-web-vitals', 'next/typescript'),
  importX.flatConfigs.recommended,
  importX.flatConfigs.typescript,

  // TYPESCRIPT
  {
    languageOptions: {
      parserOptions: { projectService: true, tsconfigRootDir: __dirname },
    },
    rules: {
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_', destructuredArrayIgnorePattern: '^_' },
      ],
      '@typescript-eslint/consistent-type-imports': [
        'warn',
        { prefer: 'type-imports', fixStyle: 'inline-type-imports' },
      ],
      '@typescript-eslint/consistent-type-exports': [
        'warn',
        { fixMixedExportsWithInlineTypeSpecifier: true },
      ],
      '@typescript-eslint/no-misused-promises': [
        'error',
        { checksVoidReturn: { attributes: false } },
      ],
      '@typescript-eslint/no-floating-promises': 'error',
      '@typescript-eslint/await-thenable': 'error',
      '@typescript-eslint/no-unnecessary-condition': 'warn',
      '@typescript-eslint/prefer-nullish-coalescing': 'warn',
      '@typescript-eslint/prefer-optional-chain': 'warn',
      '@typescript-eslint/strict-boolean-expressions': [
        'warn',
        {
          allowString: true,
          allowNumber: false,
          allowNullableObject: true,
          allowNullableBoolean: true,
          allowNullableString: true,
        },
      ],
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-non-null-assertion': 'warn',
      '@typescript-eslint/ban-ts-comment': [
        'error',
        {
          'ts-expect-error': 'allow-with-description',
          'ts-ignore': true,
          'ts-nocheck': true,
          minimumDescriptionLength: 10,
        },
      ],
      '@typescript-eslint/naming-convention': [
        'warn',
        { selector: 'typeLike', format: ['PascalCase'] },
        { selector: 'enumMember', format: ['UPPER_CASE'] },
        {
          selector: 'variable',
          types: ['boolean'],
          format: ['PascalCase'],
          prefix: ['is', 'has', 'should', 'can', 'will'],
        },
      ],
    },
  },

  // IMPORT ORDERING
  {
    rules: {
      'import-x/order': [
        'warn',
        {
          groups: ['builtin', 'external', 'internal', ['parent', 'sibling'], 'index', 'type'],
          pathGroups: [
            { pattern: 'react', group: 'builtin', position: 'before' },
            { pattern: 'next/**', group: 'builtin', position: 'before' },
            { pattern: '@/**', group: 'internal', position: 'before' },
          ],
          pathGroupsExcludedImportTypes: ['react', 'next'],
          'newlines-between': 'always',
          alphabetize: { order: 'asc', caseInsensitive: true },
        },
      ],
      'import-x/no-duplicates': ['warn', { 'prefer-inline': true }],
      'import-x/no-cycle': ['error', { maxDepth: 4 }],
      'import-x/no-self-import': 'error',
      'import-x/consistent-type-specifier-style': ['warn', 'prefer-inline'],
    },
    settings: {
      'import-x/resolver': {
        typescript: { alwaysTryTypes: true, project: './tsconfig.json' },
      },
    },
  },

  // REACT HOOKS & A11Y
  {
    plugins: { 'react-hooks': reactHooks, 'jsx-a11y': jsxA11y },
    rules: {
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
      'jsx-a11y/alt-text': 'error',
      'jsx-a11y/anchor-is-valid': 'error',
      'jsx-a11y/aria-props': 'error',
      'jsx-a11y/click-events-have-key-events': 'warn',
      'jsx-a11y/heading-has-content': 'error',
    },
  },

  // ARCHITECTURE BOUNDARIES (FSD)
  {
    plugins: { boundaries },
    settings: {
      'boundaries/elements': [
        { type: 'app', pattern: 'src/app/*' },
        { type: 'widgets', pattern: 'src/widgets/*' },
        { type: 'features', pattern: 'src/features/*' },
        { type: 'entities', pattern: 'src/entities/*' },
        { type: 'shared', pattern: 'src/shared/*' },
      ],
    },
    rules: {
      'boundaries/element-types': [
        'error',
        {
          default: 'disallow',
          rules: [
            { from: 'app', allow: ['widgets', 'features', 'entities', 'shared'] },
            { from: 'widgets', allow: ['features', 'entities', 'shared'] },
            { from: 'features', allow: ['entities', 'shared'] },
            { from: 'entities', allow: ['shared'] },
          ],
        },
      ],
    },
  },

  // IGNORES
  { ignores: ['.next/', 'node_modules/', 'dist/', 'coverage/', '*.config.*'] },
);
```

### 2.3 Зависимости

```bash
pnpm add -D \
  eslint @eslint/js @eslint/eslintrc typescript-eslint \
  eslint-plugin-import-x eslint-import-resolver-typescript \
  eslint-plugin-boundaries eslint-plugin-react-hooks \
  eslint-plugin-jsx-a11y eslint-config-prettier
```

### 2.4 eslint-plugin-import-x vs eslint-plugin-import

| Критерий           | import (legacy) |     import-x      |
| ------------------ | :-------------: | :---------------: |
| Flat config        |   Compat-слой   |     Нативный      |
| TypeScript         | Через resolver  |    Встроенный     |
| ESM                |    Проблемы     | Полная поддержка  |
| Производительность |    Медленный    |      Быстрее      |
| **Рекомендация**   |     Legacy      | **Новые проекты** |

### 2.5 projectService (typescript-eslint v8)

```javascript
// v7 (старый):  parserOptions: { project: true, tsconfigRootDir: __dirname }
// v8 (новый):   parserOptions: { projectService: true, tsconfigRootDir: __dirname }
// v8 (advanced):
parserOptions: {
  projectService: {
    allowDefaultProject: ["*.js", "*.mjs"],
    defaultProject: "./tsconfig.json",
  },
  tsconfigRootDir: __dirname,
}
```

Преимущества: авто-обнаружение tsconfig, корректная работа в монорепо, поддержка
файлов вне tsconfig через `allowDefaultProject`.

---

## 3. Prettier -- конфигурация и интеграция

### 3.1 .prettierrc

```jsonc
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "useTabs": false,
  "trailingComma": "all",
  "printWidth": 100,
  "bracketSpacing": true,
  "bracketSameLine": false,
  "arrowParens": "always",
  "endOfLine": "lf",
  "singleAttributePerLine": false,
  "jsxSingleQuote": false,
  "quoteProps": "as-needed",
  "plugins": ["prettier-plugin-tailwindcss"],
  "tailwindFunctions": ["cn", "cva", "clsx", "twMerge"],
  "tailwindAttributes": ["className", "class", "tw"],
}
```

### 3.2 .prettierignore

```
.next/
node_modules/
dist/
coverage/
pnpm-lock.yaml
*.min.js
*.min.css
public/
playwright-report/
```

### 3.3 Интеграция ESLint + Prettier

**eslint-config-prettier** отключает конфликтующие ESLint-правила:

```javascript
// eslint.config.mjs -- добавить ПОСЛЕДНИМ
import prettierConfig from 'eslint-config-prettier';
export default tseslint.config(
  // ... все конфиги ...
  prettierConfig,
);
```

### 3.4 prettier-plugin-tailwindcss

Главная причина выбора Prettier для проектов с Tailwind CSS:

- Сортировка классов по официальному порядку Tailwind
- Чтение `tailwind.config.js/ts` для кастомных утилит
- Поддержка `cn()`, `cva()`, `clsx()` через `tailwindFunctions`
- Работает с JSX, Vue, Svelte, HTML

---

## 4. Рекомендация для проекта

**Стек:** ESLint v9 + typescript-eslint v8 + Prettier + prettier-plugin-tailwindcss

Причины: полная поддержка Tailwind, architecture boundaries (FSD), зрелая экосистема
плагинов (jsx-a11y, react-hooks, import-x), 10+ лет документации.

```bash
# Установка
pnpm add -D eslint @eslint/js @eslint/eslintrc typescript-eslint \
  eslint-plugin-import-x eslint-import-resolver-typescript \
  eslint-plugin-boundaries eslint-plugin-react-hooks \
  eslint-plugin-jsx-a11y eslint-config-prettier \
  prettier prettier-plugin-tailwindcss
```

---

## Источники

[Next.js TS Config](https://nextjs.org/docs/app/api-reference/config/typescript) | [TSConfig Reference](https://www.typescriptlang.org/tsconfig/) | [ESLint Migration](https://eslint.org/docs/latest/use/configure/migration-guide) | [ESLint extends 2025](https://eslint.org/blog/2025/03/flat-config-extends-define-config-global-ignores/) | [Next.js 16 + ESLint 9](https://chris.lu/web_development/tutorials/next-js-16-linting-setup-eslint-9-flat-config) | [import-x docs](https://deepwiki.com/un-ts/eslint-plugin-import-x/2-getting-started) | [Biome vs Prettier](https://biomejs.dev/formatter/differences-with-prettier/) | [Biome Roadmap 2026](https://biomejs.dev/blog/roadmap-2026/) | [Biome + Next.js](https://www.timsanteford.com/posts/how-to-use-biome-with-next-js-for-linting-and-formatting/)

---

---

# Часть 2 — Git Hooks и стек тестирования

> Husky v9 + lint-staged + commitlint, Vitest, Playwright, MSW v2,
> паттерны тестирования RSC и Server Actions.

---

## 1. Git Hooks — Husky v9 + lint-staged + commitlint

### 1.1 Установка и инициализация

```bash
pnpm add -D husky lint-staged @commitlint/cli @commitlint/config-conventional
pnpm exec husky init  # создаёт .husky/ и prepare-скрипт
```

### 1.2 Конфигурация хуков

```bash
# .husky/pre-commit
pnpm exec lint-staged
```

```bash
# .husky/commit-msg
pnpm exec commitlint --edit "$1"
```

```bash
# .husky/pre-push
pnpm run typecheck
```

### 1.3 lint-staged — линтинг только staged-файлов

Критически важно для больших проектов: линтинг всего проекта — минуты, staged-файлов — секунды.

```jsonc
// package.json
{
  "lint-staged": {
    "*.{ts,tsx}": ["eslint --fix --max-warnings=0", "prettier --write"],
    "*.{json,md,yml,yaml}": ["prettier --write"],
    "*.css": ["prettier --write"],
  },
}
```

- `--max-warnings=0` — блокирует коммит с любыми warning'ами
- Порядок: сначала eslint (может менять код), потом prettier (финальное форматирование)
- **nano-staged** — альтернатива размером 47 КБ vs 6.7 МБ, идентичный API

### 1.4 commitlint — валидация коммит-сообщений

```javascript
// commitlint.config.js
export default {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
      ['feat', 'fix', 'refactor', 'docs', 'test', 'chore', 'ci', 'perf', 'style'],
    ],
    'subject-max-length': [2, 'always', 72],
    'subject-full-stop': [2, 'never', '.'],
    'type-case': [2, 'always', 'lower-case'],
    'body-leading-blank': [1, 'always'],
  },
};
```

---

## 2. Vitest — unit/integration тестирование

### 2.1 Vitest vs Jest — бенчмарки 2025-2026

| Метрика            | Vitest               | Jest              | Разница        |
| ------------------ | -------------------- | ----------------- | -------------- |
| Холодный запуск    | ~1.2 сек             | ~4.8 сек          | 4x быстрее     |
| Watch-режим (HMR)  | ~50 мс               | ~2-3 сек          | 40-60x быстрее |
| RAM (50K LOC)      | ~800 МБ              | ~1.2 ГБ           | на 30% меньше  |
| ESM                | Нативная             | Экспериментальная | стабильна      |
| TypeScript         | Из коробки (ESBuild) | ts-jest/babel     | zero-config    |
| npm downloads/нед. | ~3.8 млн             | ~35 млн           | Jest зрелее    |

**Вывод**: Vitest — стандарт для новых Next.js 15+ проектов. Jest — только legacy/React Native.

### 2.2 vitest.config.ts

```typescript
import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [tsconfigPaths(), react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./vitest.setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    exclude: ['src/**/*.e2e.{test,spec}.{ts,tsx}', 'e2e/**'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/**/*.d.ts', 'src/**/*.test.*', 'src/**/index.ts', 'src/**/*.stories.*'],
      thresholds: { branches: 80, functions: 80, lines: 80, statements: 80 },
    },
    reporters: ['verbose'],
    testTimeout: 10_000,
  },
});
```

### 2.3 vitest.setup.ts

```typescript
import '@testing-library/jest-dom/vitest';
import { server } from '@/mocks/server';

// Мок Next.js router
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(), replace: vi.fn(), back: vi.fn(),
    prefetch: vi.fn(), refresh: vi.fn(),
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));

// Мок next/image
vi.mock('next/image', () => ({
  default: (props: React.ImgHTMLAttributes<HTMLImageElement>) => <img {...props} />,
}));

// MSW lifecycle
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

### 2.4 Стратегия тестирования RSC

Vitest/RTL **не поддерживают async Server Components** — RSC рендерятся на сервере
и возвращают сериализованный payload, а не React-дерево.

```
Async Server Components → E2E тесты (Playwright)
Sync Server Components  → Unit тесты (Vitest + RTL)
Client Components       → Unit тесты (Vitest + RTL)
Server Actions          → Unit тесты (мок зависимостей)
```

### 2.5 Тестирование Server Actions

`'use server'` игнорируется Vitest — функция выполняется как обычная async-функция:

```typescript
// src/actions/create-user.test.ts
vi.mock('next/cache', () => ({ revalidatePath: vi.fn() }));
vi.mock('@/lib/api-server', () => ({
  apiServer: { post: vi.fn().mockResolvedValue({ id: '1' }) },
}));

import { createUser } from './create-user';

describe('createUser', () => {
  it('creates user with valid data', async () => {
    const formData = new FormData();
    formData.set('name', 'John Doe');
    formData.set('email', 'john@test.com');
    const result = await createUser(formData);
    expect(result).toEqual({ success: true });
  });

  it('returns validation errors for invalid data', async () => {
    const formData = new FormData();
    formData.set('name', '');
    formData.set('email', 'not-an-email');
    const result = await createUser(formData);
    expect(result).toHaveProperty('error');
  });
});
```

---

## 3. Playwright — E2E тестирование

### 3.1 playwright.config.ts

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { open: 'never' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ...(process.env.CI ? [['github' as const]] : []),
  ],
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 10_000,
  },
  projects: [
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], storageState: 'e2e/.auth/user.json' },
      dependencies: ['setup'],
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'], storageState: 'e2e/.auth/user.json' },
      dependencies: ['setup'],
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'], storageState: 'e2e/.auth/user.json' },
      dependencies: ['setup'],
    },
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'], storageState: 'e2e/.auth/user.json' },
      dependencies: ['setup'],
    },
  ],
  // Production build (НЕ dev — нестабилен для E2E)
  webServer: {
    command: 'pnpm build && pnpm start',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
  },
});
```

### 3.2 Auth Setup — переиспользование аутентификации

Аутентификация выполняется один раз, state переиспользуется всеми браузерами:

```typescript
// e2e/auth.setup.ts
import { expect, test as setup } from '@playwright/test';

setup('authenticate', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill('test@example.com');
  await page.getByLabel('Password').fill('password123');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page).toHaveURL('/dashboard');
  await page.context().storageState({ path: 'e2e/.auth/user.json' });
});
```

### 3.3 Page Object Model (POM)

```typescript
// e2e/pages/dashboard.page.ts
import type { Locator, Page } from '@playwright/test';

export class DashboardPage {
  readonly heading: Locator;
  readonly searchInput: Locator;

  constructor(private page: Page) {
    this.heading = page.getByRole('heading', { name: 'Dashboard' });
    this.searchInput = page.getByPlaceholder('Search...');
  }

  async goto() {
    await this.page.goto('/dashboard');
  }

  async search(query: string) {
    await this.searchInput.fill(query);
    await this.searchInput.press('Enter');
  }
}
```

### 3.4 Тестирование async RSC через Playwright

```typescript
// e2e/users.spec.ts
test('renders server-fetched user list', async ({ page }) => {
  await page.goto('/users');
  // RSC отрендерил данные на сервере — Playwright видит готовый HTML
  await expect(page.getByRole('heading', { name: 'Users' })).toBeVisible();
  await expect(page.getByTestId('user-card')).toHaveCount(10);
});
```

---

## 4. MSW v2 — мокирование API

### 4.1 Архитектура в Next.js App Router

MSW перехватывает запросы на сетевом уровне. Два контекста:

- **Server** (Node.js): `setupServer` из `msw/node` — для Vitest и SSR
- **Browser**: `setupWorker` из `msw/browser` — для development через Service Worker

В Next.js 15 MSW корректно перехватывает серверные запросы (в RSC/Route Handlers).
В Next.js 14 это не работало.

### 4.2 Структура и handlers

```
src/mocks/
├── handlers/
│   ├── users.ts      # Handlers для /api/users
│   ├── auth.ts       # Handlers для /api/auth
│   └── index.ts      # Re-export всех handlers
├── browser.ts        # setupWorker
├── server.ts         # setupServer
└── index.ts          # Условная инициализация
```

```typescript
// src/mocks/handlers/users.ts
import { http, HttpResponse } from 'msw';

export const usersHandlers = [
  http.get('/api/users', () => {
    return HttpResponse.json([
      { id: '1', name: 'Alice', email: 'alice@example.com' },
      { id: '2', name: 'Bob', email: 'bob@example.com' },
    ]);
  }),
  http.post('/api/users', async ({ request }) => {
    const body = (await request.json()) as { name: string; email: string };
    return HttpResponse.json({ id: '3', ...body }, { status: 201 });
  }),
];
```

```typescript
// src/mocks/server.ts
import { setupServer } from 'msw/node';
import { handlers } from './handlers';
export const server = setupServer(...handlers);
```

```typescript
// src/mocks/browser.ts
import { setupWorker } from 'msw/browser';
import { handlers } from './handlers';
export const worker = setupWorker(...handlers);
```

### 4.3 Условная инициализация в layout

```typescript
// src/mocks/index.ts
export async function initMocks() {
  if (typeof window === 'undefined') {
    const { server } = await import('./server');
    server.listen({ onUnhandledRequest: 'bypass' });
  } else {
    const { worker } = await import('./browser');
    await worker.start({ onUnhandledRequest: 'bypass' });
  }
}
```

```typescript
// src/app/layout.tsx — вызов на верхнем уровне
async function enableMocking() {
  if (process.env.NEXT_PUBLIC_API_MOCKING !== 'enabled') return;
  const { initMocks } = await import('@/mocks');
  await initMocks();
}
enableMocking();
```

### 4.4 Переопределение handlers в тестах

```typescript
import { http, HttpResponse } from 'msw';
import { server } from '@/mocks/server';

it('shows error state on API failure', async () => {
  server.use(
    http.get('/api/users', () => HttpResponse.json({ error: 'Server Error' }, { status: 500 })),
  );
  render(<UserList />);
  await waitFor(() => expect(screen.getByText(/error/i)).toBeInTheDocument());
});
```

---

## 5. Стратегия тестирования — пирамида

### 5.1 Что чем тестировать

| Слой              | Инструмент             | Примеры                                       |
| ----------------- | ---------------------- | --------------------------------------------- |
| Утилиты, helpers  | Vitest                 | `formatDate()`, `cn()`, `parseSearchParams()` |
| Zod-схемы         | Vitest                 | Валидация форм, env-переменных                |
| Server Actions    | Vitest + мок apiServer | `createUser()`, `updateProfile()`             |
| Custom hooks      | Vitest + `renderHook`  | `useDebounce()`, `useMediaQuery()`            |
| Client Components | Vitest + RTL           | Формы, кнопки, модалки                        |
| Sync RSC          | Vitest + RTL           | Presentational-компоненты без async           |
| Async RSC         | Playwright             | Страницы с серверным fetch                    |
| User flows        | Playwright             | Регистрация, оплата, CRUD                     |

### 5.2 Установка всего стека

```bash
# Git hooks
pnpm add -D husky lint-staged @commitlint/cli @commitlint/config-conventional

# Unit/Integration
pnpm add -D vitest @vitejs/plugin-react vite-tsconfig-paths \
  @testing-library/react @testing-library/dom @testing-library/jest-dom \
  @testing-library/user-event jsdom msw

# E2E
pnpm add -D @playwright/test

# Init
pnpm exec husky init && pnpm exec playwright install
```

### 5.3 Чеклист готовности

- [ ] `vitest.config.ts` с coverage thresholds 80%
- [ ] `vitest.setup.ts` подключает jest-dom + MSW server
- [ ] `playwright.config.ts` с auth setup и webServer
- [ ] `.husky/pre-commit` запускает lint-staged
- [ ] `.husky/commit-msg` запускает commitlint
- [ ] MSW handlers покрывают API-эндпоинты
- [ ] `.gitignore` содержит `e2e/.auth/`, `test-results/`, `playwright-report/`

---

## Источники

- [Next.js Official: Testing with Vitest](https://nextjs.org/docs/app/guides/testing/vitest)
- [Setting up Vitest for Next.js 15](https://www.wisp.blog/blog/setting-up-vitest-for-nextjs-15)
- [Testing RSC with RTL and Vitest](https://aurorascharff.no/posts/running-tests-with-rtl-and-vitest-on-internationalized-react-server-components-in-nextjs-app-router/)
- [Next.js Playwright E2E Guide](https://eastondev.com/blog/en/posts/dev/20260107-nextjs-playwright-e2e/)
- [Playwright + Next.js Best Practices](https://jsmastery.com/blogs/test-next-js-apps-with-playwright-5-best-practices)
- [Setting up MSW in Next.js App Router](https://gimbap.dev/blog/setting-msw-in-next)
- [MSW + Next.js 15 Setup](https://blog.stackademic.com/setting-up-msw-and-urql-with-next-js-15-cbfd374e916a)
- [Next.js 16 x MSW Integration](https://github.com/laststance/next-msw-integration)
- [Husky + lint-staged Setup 2025](https://dev.to/_d7eb1c1703182e3ce1782/git-hooks-with-husky-and-lint-staged-the-complete-setup-guide-for-2025-53ji)
- [Commitlint Local Setup](https://commitlint.js.org/guides/local-setup.html)
- [Jest vs Vitest 2025](https://medium.com/@ruverd/jest-vs-vitest-which-test-runner-should-you-use-in-2025-5c85e4f2bda9)
- [Vitest vs Jest Benchmarks](https://dev.to/thejaredwilcurt/vitest-vs-jest-benchmarks-on-a-5-year-old-real-work-spa-4mf1)

---

---

# Часть 3 — CI/CD, Env, пакетный менеджер, кодогенерация, мониторинг

> Инфраструктурные инструменты для enterprise Next.js 16+ проекта.

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
    API_BASE_URL: z.string().url(), // URL бэкенд-сервиса
    AUTH_SERVICE_URL: z.string().url(), // URL auth-сервиса
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
// src/lib/api-server.ts — серверный HTTP-клиент (BFF proxy)
import { env } from '@/env';
import ky from 'ky';

export const apiServer = ky.create({
  prefixUrl: env.API_BASE_URL, // type-safe, автокомплит
  timeout: 15_000,
});
```

```typescript
// src/components/analytics.tsx — клиентский код
import { env } from '@/env';

// env.API_BASE_URL — TS-ошибка! Серверная переменная в клиентском коде.
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
API_BASE_URL=http://localhost:8080
AUTH_SERVICE_URL=http://localhost:8081
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
    API_BASE_URL: http://localhost:8080
    AUTH_SERVICE_URL: http://localhost:8081
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
