# Mini-App — Loyality Project

**Component:** `frontend-main` | **Vault tag:** `[project/loyality, frontend-main]`

Customer-facing Telegram Mini App (`apps/frontend/mini-app/`, package `loyaltymarket`).
Next.js 16 + React 19 + Redux Toolkit/RTK Query + Zustand + native `fetch`.
JS/JSX основой; точечный TS (`layout.tsx`, codegen). Tests: Vitest + jsdom.

> [!success] FSD-миграция завершена (Phase 1-12, 2026-05-17)
> Структура полностью в `src/{app,widgets,features,entities,shared}/`.
> Корневые `app/ components/ lib/` удалены. См. `docs/FSD-MIGRATION.md`
> для карты «было → станет».
> Cross-feature нарушения временно warns (118 шт), полный error-уровень
> ESLint — после Phase 9 god-component refactor (`docs/PHASE-9-TODO.md`).

## Стек

| Слой         | Технология                                                              |
| ------------ | ----------------------------------------------------------------------- |
| Routing      | Next.js 16 (App Router)                                                 |
| UI           | React 19, CSS Modules + CSS-переменные (НЕ Tailwind, хотя postcss есть) |
| Server-state | Redux Toolkit + RTK Query                                               |
| Client-state | Zustand (auth, checkout, ui/toast, back-handler)                        |
| HTTP         | `fetch` (browser) + BFF (`/api/backend/[...path]`)                      |
| Auth         | Telegram initData → HMAC-валидация на бэке → JWT в httpOnly cookies     |
| Types        | `tsconfig: strict: false, allowJs: true` — JS первичен, TS как dialect  |
| Tests        | Vitest + jsdom + @testing-library/react                                 |
| Dev TLS      | `next dev --experimental-https` + mkcert (auto); `dev:lan` для LAN-IP   |

## Целевая структура (FSD, как admin)

```
src/
├── app/          ← Next.js routes + BFF (тонкие; вся бизнес-логика — выше)
│   ├── providers/
│   ├── api/      ← BFF endpoints (auth, backend proxy, checkout, geo)
│   ├── (routes)/ ← page.jsx импортирует widget'ы
│   └── layout.tsx
├── widgets/      ← composite UI блоки (header, footer, telegram-app-shell, *-page)
│                   ПЛОСКАЯ структура без slice/index.js — как в admin
├── features/     ← user-facing actions (auth-telegram, telegram-api, checkout-flow, ...)
│                   slice: ui/ model/ api/ lib/ + index.js
├── entities/     ← business entities (product, cart, order, pickup-point, ...)
│                   slice: ui/ model/ api/ lib/ + index.js [+ server.js если нужно]
└── shared/       ← техника (api, ui, lib, config, types)
    ├── api/      ← base-api (RTKQ), codegen, bff utils
    ├── ui/       ← Button, BottomSheet, Toaster — без бизнес-привязки
    ├── lib/      ← money, date, url, hooks, events, ios, dev utilities
    └── config/   ← env, feature-flags
```

## Правила импорта (enforce: ESLint `no-restricted-imports`)

| Слой        | Может импортировать из                                  |
| ----------- | ------------------------------------------------------- |
| `app/`      | `widgets/`, `features/`, `entities/`, `shared/`         |
| `widgets/`  | `features/`, `entities/`, `shared/`                     |
| `features/` | `entities/` (через index), `shared/`, свои внутренности |
| `entities/` | другие `entities/` (через index), `shared/`             |
| `shared/`   | только `shared/`                                        |

**Sibling import запрещён**: `features/checkout-flow` не импортирует `features/pickup-selection`. Общее → поднимается в `entities/` или `shared/`.

**Public API**: каждый slice имеет `index.js` — единственный валидный путь импорта снаружи. Внутри slice — относительные пути. Запрет deep-import через ESLint.

## Чеклист «куда положить новый код»

1. **Компонент?**
   - Read-only / карточка / бейдж сущности → `entities/<x>/ui/`
   - Действие (модалка, форма, флоу) → `features/<x>/ui/`
   - Композиция нескольких features → `widgets/<page>/ui/`
   - Без бизнес-привязки → `shared/ui/`
2. **Хук?**
   - С Zustand-store / бизнес-FSM → `<slice>/model/`
   - Чистая утилита-хук → `<slice>/lib/` или `shared/lib/hooks/`
3. **RTKQ endpoint?**
   - Принадлежит сущности → `entities/<x>/api/`
   - Cross-entity (например `/cart/checkout`) → `features/<x>/api/`
4. **Чистая функция?**
   - Бизнес (totals, idempotency) → `<slice>/lib/`
   - Техника (cn, formatMoney) → `shared/lib/<topic>/`
5. **Страница?**
   - `src/app/<route>/page.jsx` — тонкая, 5-10 строк, импорт widget
6. **BFF endpoint?**
   - `src/app/api/<path>/route.js`
7. **Server-only entry slice'а?**
   - Доп. файл рядом с `index.js` (например `entities/user/server.js`), импорт через `@/entities/user/server`

## Имена и стиль

- **Файлы**: `PascalCase.jsx` для UI, `camelCase.js` для всего остального
- **Папки слайсов**: `kebab-case` (`auth-telegram`, `checkout-flow`, `pickup-selection`)
- **Barrel `index.js`**: named-экспорты; default допустим для хуков
- **CSS**: CSS Modules (`<Name>.module.css` рядом с компонентом). Tailwind НЕ используется (отличие от admin)
- **Цвета**: CSS-переменные из `app/globals.css` (`--lm-*`). Не хардкодить hex
- **Деньги**: всегда в копейках (integer math, без float). Helpers: `shared/lib/money/`
- **Комментарии**: узбекский или русский, как сейчас в коде — единый стиль не enforce

## Команды

```bash
npm install
npm run dev          # next dev --experimental-https
npm run dev:http     # без HTTPS (для туннеля)
npm run dev:lan      # mkcert + LAN-IP
npm run dev:clean    # rm .next + dev (при странных bugs)
npm run build        # production build
npm run lint         # eslint
npm run lint:fix     # eslint --fix
npm run typecheck    # tsc --noEmit
npm test             # vitest run
npm run format       # prettier --write
npm run validate     # typecheck + lint + format:check
npm run api:gen      # rtk-query-codegen-openapi
npm run api:types    # openapi-typescript
npm run api:check    # api:gen + api:types + git diff fail
```

## Архитектурные решения, которые **не** меняются миграцией

- **Plain Redux + RTK Query**, НЕ TanStack Query (отличие от admin)
- **CSS Modules**, НЕ Tailwind (отличие от admin)
- **JS/JSX**, НЕ TS (отличие от admin, который тоже JSX)
- **BFF layer** (`app/api/*`) — токены и backend URL изолированы server-side
- **Codegen-first для RTKQ** — `openapi.json` → `__generated__/api.ts` → ручная обвязка
- **Money в копейках** через `shared/lib/money/`
- **Zustand-FSM для checkout** (idle→quoting→ready→initiating→frozen→confirming→confirmed)
- **EventTarget-шина** (`shared/lib/events/`) — без `window.__LM_*` глобалов

## Известные edge cases

- **HMAC validation на бэке временно убрана** (dev branch). Перед merge в main вернуть или положить за env-флаг
- **`InitTelegramMock` (`shared/lib/dev/`)** активируется только в `NODE_ENV !== 'production'`; в Telegram-клиенте сам отключается (guard `if (initData) return`)
- **`certificates/lan.pem`** регенерируется при смене LAN-IP — `mkcert -key-file certificates/lan-key.pem -cert-file certificates/lan.pem localhost 127.0.0.1 <new-ip> ::1`
- **BotFather не принимает `localhost`** — для local Telegram Desktop test использовать `https://127.0.0.1:3000`

## Документы в Knowledge Base

- [[Loyality Project]] — дашборд проекта
- [[Frontend Main]] — обзор фронта-кастомера
- [[Audit - Mini App Architecture]] — pre-FSD аудит (2026-05-15)
- [[Research - Mini App Debugging & Testing]] — dev + debug guide
- [[Research - Telegram TLS Certificate in Local Dev]] — фикс `Unacceptable TLS certificate`

## Парент-документация

- `apps/frontend/CLAUDE.md` — фронтенд-общее (admin + mini-app)
- `CLAUDE.md` (root) — обзор Loyality monorepo
- `apps/frontend/admin/docs/ARCHITECTURE.md` — **базовый стандарт FSD**, который мы воспроизводим
- `apps/frontend/admin/eslint.config.mjs` — **референс для FSD eslint**
