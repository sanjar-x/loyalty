# `src/app/` — Next.js routes + BFF

Только маршруты Next.js: тонкие `page.jsx`, `layout.tsx`, `loading.jsx`, `route.js`.
Бизнес-логика и состав UI **не здесь** — собирается из `widgets/`/`features/`/`entities/`.

## Что внутри

- `app/(routes)/page.jsx` — тонкая обёртка над widget'ом (5-10 строк)
- `app/api/<path>/route.js` — BFF-эндпоинты (могут реэкспортировать handlers из `shared/api/bff/`)
- `app/layout.tsx` — root layout (тонкий, импорт widget'а)
- `app/providers/` — top-level provider'ы (Store, Theme)

## Правила

- Может импортировать из: `widgets/`, `features/`, `entities/`, `shared/`
- **Только через public API slice'а** (например `@/entities/product`, не `@/entities/product/ui/ProductCard`)
- `proxy.js` (CSRF middleware) — на уровне `src/app/`, не в slice

См. `apps/frontend/mini-app/CLAUDE.md` и `apps/frontend/admin/docs/ARCHITECTURE.md`.
