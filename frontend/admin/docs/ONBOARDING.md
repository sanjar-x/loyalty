# Онбординг — `frontend/admin`

Документ для новых разработчиков. Прочитать первым: [`ARCHITECTURE.md`](./ARCHITECTURE.md). Этот файл — практическая выжимка «как сделать N за 5 минут».

## Запуск

```bash
npm install
npm run dev          # http://localhost:3000  (next dev --webpack)
npm run lint         # FSD-границы + Next core-web-vitals
npm run typecheck    # tsc --noEmit (allowJs, не требует TS)
npm run format       # prettier --write
```

## Стек

Next.js 16 (App Router) · React 19 · Tailwind 4 · dayjs · `@svgr/webpack`. Без TypeScript в коде, но `tsconfig.json` подключён для LSP/IntelliSense (`allowJs: true`, `checkJs: false`).

## Где что лежит — короткая шпаргалка

```
src/
├── app/        Next.js routes (тонкие page/layout/route)
├── widgets/    композиция UI (Sidebar, PageStub)
├── features/   действия пользователя (auth, product-form, …)
├── entities/   бизнес-сущности (product, order, …)
├── shared/     ui/lib/api/auth/hooks/mocks — без бизнес-логики
└── assets/     icons (SVG → React-компонент через svgr)
```

Импорт **ТОЛЬКО через `index.js`** слайса:

```js
// ✓ ОК
import { ProductDetailsForm } from '@/features/product-form';
import { ProductRow } from '@/entities/product';

// ✗ ESLint завалит билд
import { ProductRow } from '@/entities/product/ui/ProductRow';
```

Server-only код у `category` — отдельный entry: `@/entities/category/server`.

## Чеклист «как добавить…»

### Новую страницу

1. `src/app/admin/<route>/page.jsx` — тонкий компонент.
2. UI собирается из `widgets`/`features`/`entities`. Никакого fetching/state.
3. Нужен loading? `loading.jsx` рядом. Ошибка? `error.jsx`.
4. CSS — Tailwind + `cn()`. Page-shell-стили (header/title) — локальный `page.module.css`.

### Новую фичу (действие пользователя)

```
src/features/<kebab-name>/
├── ui/         React-компоненты
├── model/      хуки, reducers, providers
├── api/        client-side fetch wrappers (опц.)
├── lib/        чистые утилиты (опц.)
└── index.js    public API — barrel
```

Помни: **cross-feature imports запрещены**. Общее → в `shared/` или `entities/`.

### Новую сущность

```
src/entities/<kebab-name>/
├── ui/         карточки, list-rows, метрики (read-only)
├── api/        fetch wrappers (или *.mock.js если backend ещё не готов)
├── lib/        константы, чистые утилиты
└── index.js    barrel
```

Mock-only сущности должны иметь `api/<name>.mock.js` и комментарий-TODO в `index.js`:

```js
// TODO: replace mock-backed API with real backend integration when /api/<x> is ready.
export { getX } from './api/x.mock';
```

### Новый BFF endpoint

`src/app/api/<path>/route.js`. Используй:

- `getAccessToken()` из `@/shared/auth/cookies` для авторизации.
- `backendFetch()` для backend, `imageBackendFetch()` для image-backend.
- Возвращай error-envelope: `{ error: { code, message, details } }` со статусом backend.

### Новую SVG-иконку

1. Положи в `src/assets/icons/<name>.svg` (используй `currentColor` для fill/stroke).
2. Импортируй: `import MyIcon from '@/assets/icons/my.svg'`.
3. Применяй: `<MyIcon className={styles.icon} width={20} height={20} />`.

## Auth

- Login: `<form>` POST `/api/auth/login` → cookies (httpOnly).
- Edge middleware (`src/middleware.js`) рефрешит JWT за 30s до истечения, фильтр `/admin/:path*`.
- `useAuth()` из `@/features/auth` — клиентский Context (`user`, `logout`).

## Media upload (3 шага + SSE)

Используй хуки из `@/features/product-form`:

- `useImageUpload` — eager upload при выборе файла.
- `useSubmitProduct` — оркестрация всего create-flow.
- `useUpdateProduct` — diff-based PATCH.

Не вызывай `reserveMediaUpload`/`uploadToS3`/`confirmMedia` напрямую из страницы.

## i18n entity-данных

```js
import { i18n, buildI18nPayload } from '@/shared/lib/utils';

const label = i18n(product.titleI18N); // → "Кроссовки"
const payload = buildI18nPayload(ru, en); // → { ru, en: en || ru }
```

## Pre-commit

При коммите автоматически: `eslint --fix` + `prettier --write` для staged-файлов (через `husky` + `lint-staged`). Не коммить с `--no-verify` без причины.

## Куда задавать вопросы

- Архитектура: [`docs/ARCHITECTURE.md`](./ARCHITECTURE.md)
- Соглашения по коду: [`docs/CONVENTIONS.md`](./CONVENTIONS.md)
- Создание продукта (multi-step): [`docs/product-creation-flow.md`](./product-creation-flow.md)
- OpenAPI backend: `openapi/backend.json`, `openapi/image-backend.json`
