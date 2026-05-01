# Архитектура `frontend/admin`

Документ для команды. Описывает слои, правила импорта и куда класть новый код. Отклонения — только через PR с обоснованием.

Стек: Next.js 16 (App Router) + React 19 + JSX (без TS) + Tailwind 4 + dayjs.
Методология: **Feature-Sliced Design (FSD)**.

## 1. Слои

```
┌──────────────────────────────────────────────────────────┐
│  app/         — Next.js routes (pages + /api BFF)        │ ← top
├──────────────────────────────────────────────────────────┤
│  widgets/     — composite UI shell (Sidebar, PageStub)   │
├──────────────────────────────────────────────────────────┤
│  features/    — user actions / business interactions      │
├──────────────────────────────────────────────────────────┤
│  entities/    — business entities (cards, reads, models) │
├──────────────────────────────────────────────────────────┤
│  shared/      — cross-cutting, no business logic          │ ← bottom
└──────────────────────────────────────────────────────────┘
```

Высший слой импортирует только из нижестоящих. Сиблинги в одном слое **не импортируют друг друга** (никаких cross-feature, cross-entity).

| Слой        | Может импортировать из                                |
| ----------- | ----------------------------------------------------- |
| `app/`      | `widgets`, `features`, `entities`, `shared`           |
| `widgets/`  | `features`, `entities`, `shared`                      |
| `features/` | `entities` (через index), `shared`, свои внутренности |
| `entities/` | другие `entities` (через index), `shared`             |
| `shared/`   | только `shared`                                       |

Эти правила прошиты в ESLint (`eslint.config.mjs`, `no-restricted-imports`). Нарушение → ошибка lint, CI красный.

## 2. Анатомия слайса

Слайс — это `entities/<x>` или `features/<x>`. Каждый слайс имеет одинаковые внутренние сегменты:

```
<slice>/
├── ui/         # React-компоненты
├── model/      # хуки, бизнес-стейт (reducers, providers)
├── api/        # обёртки fetch (client/server)
├── lib/        # чистые утилиты, константы
├── config/     # статическая конфигурация (редко)
└── index.js    # publicAPI — единственный валидный путь импорта снаружи
```

Не каждый слайс имеет все сегменты — только нужные.

### Public API (`index.js`)

`index.js` — это контракт слайса. Снаружи импорт идёт **только** через него:

```js
// ✓ ОК
import { ProductRow, PRODUCT_STATUS_LABELS } from '@/entities/product';
import { useProductFilters, BulkBar } from '@/features/product-filter';

// ✗ ESLint отклонит
import { ProductRow } from '@/entities/product/ui/ProductRow';
import { useProductFilters } from '@/features/product-filter/model/useProductFilters';
```

Зачем: рефакторинг внутренностей слайса не должен ломать всех потребителей.

### Server-only entry

Если слайс отдаёт код, использующий `next/headers` или иные server-only API, выноси его в отдельный entry-point рядом с `index.js`. Сейчас единственный пример: `entities/category/server.js` — экспортирует `fetchCategoryTreeServer` (читает cookies).

```js
// Server Component
import { fetchCategoryTreeServer } from '@/entities/category/server';
```

## 3. Где что лежит

### entity vs feature

- **`entities/<x>`** — бизнес-сущность: карточки, метрики, read-only API, модель. «Как заказ выглядит», «как достать пользователя по id».
- **`features/<x>`** — пользовательское действие: фильтрация, форма создания, архивация, смена статуса. «Что пользователь делает с заказом».

Грубое правило: если компонент не вызывает мутации и не управляет процессом — он, скорее всего, в `entities/`. Если есть кнопка-действие, конфирм-модалка, флоу из нескольких шагов — это `features/`.

### shared

Сюда идут только переиспользуемые примитивы без бизнес-логики:

- UI-компоненты, не привязанные к конкретной сущности (`Button`, `Modal`, `DateRangePicker`).
- Утилиты-функции (`cn`, `formatCurrency`, `calculatePeriodStats`).
- API-клиенты (`backendFetch`, `imageBackendFetch`).
- Технические хуки (`useOutsideClick`, `useToast`).

Если кажется, что это «общее, но про продукты/заказы» — оно не в `shared`, а в `entities/<x>`.

### widgets

Композитные блоки страничной оболочки: сайдбар, шапка, page-stub. Используются `app/` для построения layout-ов. В отличие от features, они почти не несут активных действий — это «UI-композиция».

### app

Только маршруты Next.js. Тонкие `page.jsx`, `layout.jsx`, `loading.jsx`, `route.js`. Логика и состав UI — собирается из `widgets`/`features`/`entities`. В `app/api/*` — BFF-роуты (тонкие прокси к backend).

## 4. Чеклист «куда положить новый код»

1. **Это компонент или хук?**
   - Чистая утилита → `lib/` (свой слайс или `shared/lib`).
   - Хук с состоянием → `model/` слайса.
   - Компонент → `ui/` слайса.

2. **Это про конкретную сущность (продукт, заказ, пользователь)?**
   - Read-only / карточка / метрики → `entities/<x>/ui`.
   - Действие (фильтр, модалка, форма) → `features/<x>-action/`.
   - Иначе — расширь существующую сущность.

3. **Это переиспользуется в нескольких местах?**
   - Внутри одной фичи → внутри неё.
   - Через несколько features/entities → подними в `shared/` или соответствующий entity.

4. **Это страница/маршрут?**
   - `app/admin/<route>/page.jsx` (тонкая, собирает features/entities).

5. **Это BFF-эндпоинт?**
   - `app/api/<path>/route.js`.

6. **Это server-only код в entity?**
   - Дополнительный `entities/<x>/server.js` entry, импорт через `@/entities/<x>/server`.

## 5. Имена и стиль

- **Файлы**: `PascalCase.jsx` для UI, `camelCase.js` для всего остального.
- **Папки слайсов**: `kebab-case` (`product-filter`, `order-status-change`).
- **Барель**: каждый слайс имеет `index.js` с named-экспортами; default-экспорты hooks допустимы.
- **CSS**: Tailwind-классы + `cn()` из `@/shared/lib/utils`. CSS Modules — только для сложных layouts/анимаций.
- **Дизайн-токены**: палитра `app-*` из `tailwind.config.js` — **не** хардкодить hex.
- **i18n**: объекты `{ru, en}`. Чтение — `i18n(obj)`. Запись — `buildI18nPayload(ru, en)`.
- **Даты**: `dayjs` из `@/shared/lib/dayjs`, формат через `formatDateTime`.

## 6. Команды разработки

```bash
npm run dev          # dev server
npm run build        # production build (запускайте перед PR — webpack-only)
npm run lint         # ESLint, включая FSD-границы
npm run format       # Prettier (--write)
npm run format:check # Prettier (--check)
```

PR не пройдёт ревью, если:

- `npm run build` падает.
- `npm run lint` ругается на границы слоёв.
- импорт идёт в обход `index.js` слайса.

## 7. Где документация по фичам

- `CLAUDE.md` — обзор для AI-агентов и общие соглашения.
- `docs/product-creation-flow.md` — поток создания продукта (multi-step + media upload).
- `openapi/` — снимки OpenAPI backend и image backend.

## 8. Эволюция

Этот документ — живой. Если возникает паттерн, не описанный здесь, и команда договорилась — фикси правило в этом файле и в `eslint.config.mjs`. Главный принцип: **новый код подчиняется текущим правилам или меняет их явно через PR**.
