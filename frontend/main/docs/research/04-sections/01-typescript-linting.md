# TypeScript, ESLint v9, Prettier & Biome -- глубокое исследование

> Расширение секций 1-3 из `04-dx-tooling.md`. Дата: 2026-04-05

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

## 4. Biome -- альтернатива ESLint + Prettier

### 4.1 Обзор

Biome (бывший Rome) -- линтер + форматтер + import sorter на Rust.
Версия 2.3 (январь 2026): 423+ lint-правил, type-aware линтинг.

### 4.2 biome.json для Next.js

```jsonc
{
  "$schema": "https://biomejs.dev/schemas/2.3/schema.json",
  "vcs": { "enabled": true, "clientKind": "git", "useIgnoreFile": true },
  "files": {
    "ignoreUnknown": true,
    "ignore": [".next/**", "node_modules/**", "dist/**", "coverage/**"],
  },
  "formatter": {
    "enabled": true,
    "indentStyle": "space",
    "indentWidth": 2,
    "lineWidth": 100,
    "lineEnding": "lf",
  },
  "javascript": {
    "formatter": {
      "quoteStyle": "single",
      "trailingCommas": "all",
      "semicolons": "always",
      "arrowParentheses": "always",
      "bracketSpacing": true,
      "jsxQuoteStyle": "double",
    },
  },
  "linter": {
    "enabled": true,
    "rules": {
      "recommended": true,
      "complexity": {
        "noExcessiveCognitiveComplexity": {
          "level": "warn",
          "options": { "maxAllowedComplexity": 15 },
        },
      },
      "correctness": {
        "noUnusedVariables": "error",
        "noUnusedImports": "error",
        "useExhaustiveDependencies": "warn",
        "useHookAtTopLevel": "error",
      },
      "suspicious": { "noExplicitAny": "error", "noConsole": "warn", "noDoubleEquals": "error" },
      "style": { "useConst": "error", "noNonNullAssertion": "warn", "useImportType": "warn" },
      "nursery": {
        "useSortedClasses": { "level": "warn", "options": { "functions": ["cn", "cva", "clsx"] } },
      },
    },
  },
  "organizeImports": { "enabled": true },
}
```

### 4.3 Next.js + Biome

```javascript
// next.config.mjs -- отключить встроенный ESLint
const nextConfig = { eslint: { ignoreDuringBuilds: true } };
export default nextConfig;
```

```jsonc
// package.json
{
  "scripts": {
    "lint": "biome check .",
    "lint:fix": "biome check --write .",
    "format": "biome format --write .",
    "ci:check": "biome ci .",
  },
}
```

### 4.4 Миграция

```bash
pnpm add -D @biomejs/biome
pnpm exec biome migrate eslint .eslintrc.json   # ~70% правил конвертируется
pnpm exec biome migrate prettier .prettierrc
```

### 4.5 Ограничения Biome (апрель 2026)

| Функция                        | Статус                                |
| ------------------------------ | ------------------------------------- |
| Tailwind -- стандартные классы | Работает (nursery `useSortedClasses`) |
| Tailwind -- кастомные утилиты  | Не поддерживается                     |
| Vue/Svelte SFC                 | Частичная (roadmap 2026)              |
| Кастомные плагины              | Не поддерживается                     |
| Architecture boundaries        | Не поддерживается                     |
| React hooks rules              | Встроен                               |
| jsx-a11y аналог                | Частичный                             |

---

## 5. Сравнительные таблицы

### 5.1 ESLint + Prettier vs Biome

| Критерий                     |    ESLint + Prettier     |       Biome       |
| ---------------------------- | :----------------------: | :---------------: |
| **Скорость** (10k файлов)    |         ~12 сек          | ~0.3 сек (35-40x) |
| **Зависимости**              |       127+ пакетов       |    1 бинарник     |
| **Конфигурация**             |        2-4 файла         |      1 файл       |
| **Tailwind CSS**             |          Полная          |     Частичная     |
| **Плагины**                  |    Богатая экосистема    |        Нет        |
| **Architecture enforcement** | eslint-plugin-boundaries |        Нет        |
| **Type-aware linting**       |        296 правил        |    423+ правил    |
| **IDE-поддержка**            |         Все IDE          | VS Code, IntelliJ |
| **Зрелость**                 |         10+ лет          |      ~2 года      |

### 5.2 Prettier vs Biome formatter vs dprint

| Критерий               | Prettier |   Biome   | dprint |
| ---------------------- | :------: | :-------: | :----: |
| Скорость               | Базовая  |   ~35x    |  ~30x  |
| Prettier-совместимость |    --    |   97%+    |  ~95%  |
| Tailwind sort          |  Полная  | Частичная |  Нет   |
| Языки                  |   20+    |    10+    |  15+   |
| Плагины                |  Много   |    Нет    |  WASM  |

### 5.3 Когда какой инструмент

| Сценарий                            | Рекомендация      |
| ----------------------------------- | ----------------- |
| Enterprise + Tailwind CSS           | ESLint + Prettier |
| Enterprise + FSD/Clean Architecture | ESLint + Prettier |
| Новый проект без Tailwind           | Biome             |
| Максимальная скорость CI            | Biome             |
| Монорепо с разными фреймворками     | ESLint + Prettier |
| Маленькая команда, быстрый старт    | Biome             |

---

## 6. Рекомендация для проекта

**Основной стек:** ESLint v9 + typescript-eslint v8 + Prettier + prettier-plugin-tailwindcss

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

**Альтернатива (без Tailwind):** `pnpm add -D @biomejs/biome && pnpm exec biome init`
-- одна команда `biome ci .` заменяет `eslint . && prettier --check .` в 35x быстрее.

---

## Источники

[Next.js TS Config](https://nextjs.org/docs/app/api-reference/config/typescript) | [TSConfig Reference](https://www.typescriptlang.org/tsconfig/) | [ESLint Migration](https://eslint.org/docs/latest/use/configure/migration-guide) | [ESLint extends 2025](https://eslint.org/blog/2025/03/flat-config-extends-define-config-global-ignores/) | [Next.js 16 + ESLint 9](https://chris.lu/web_development/tutorials/next-js-16-linting-setup-eslint-9-flat-config) | [import-x docs](https://deepwiki.com/un-ts/eslint-plugin-import-x/2-getting-started) | [Biome vs Prettier](https://biomejs.dev/formatter/differences-with-prettier/) | [Biome Roadmap 2026](https://biomejs.dev/blog/roadmap-2026/) | [Biome + Next.js](https://www.timsanteford.com/posts/how-to-use-biome-with-next-js-for-linting-and-formatting/)
