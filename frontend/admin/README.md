# Loyality Admin

Админ-панель маркетплейса Loyality.

[![CI](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)

## Стек

- **Next.js 16** (App Router) + **React 19** + JSX (TypeScript подключён для LSP/IntelliSense, но код на JS)
- **Tailwind CSS 4** + CSS Modules для сложных layout
- **dayjs** для дат, **clsx + tailwind-merge** для классов
- **Vitest** + **Testing Library** для тестов
- **ESLint 9** (flat config) + **Prettier** + **Husky** pre-commit
- **Webpack** (`@svgr/webpack` требует webpack, не Turbopack)

## Quick Start

```bash
# Требования: Node.js 24+, npm 10+
npm install

# Создать .env.local на основе .env.example
cp .env.example .env.local

# Dev server (http://localhost:3000)
npm run dev
```

## Скрипты

| Скрипт                            | Описание                                 |
| --------------------------------- | ---------------------------------------- |
| `npm run dev`                     | dev server (Next.js + webpack)           |
| `npm run build`                   | production build                         |
| `npm start`                       | прод server (после build)                |
| `npm run lint` / `lint:fix`       | ESLint + FSD-границы                     |
| `npm run typecheck`               | TypeScript LSP-проверка (`tsc --noEmit`) |
| `npm test`                        | Vitest (одноразово)                      |
| `npm run test:watch` / `test:ui`  | Vitest watch / UI                        |
| `npm run test:coverage`           | Coverage отчёт                           |
| `npm run format` / `format:check` | Prettier                                 |

## Структура (Feature-Sliced Design)

```
src/
├── app/        Next.js routes (тонкие page/layout/route + /api BFF)
├── widgets/    композиция UI (Sidebar, PageStub)
├── features/   действия пользователя (auth, product-form, …)
├── entities/   бизнес-сущности (product, order, …)
├── shared/     ui/lib/api/auth/hooks/mocks
├── assets/     SVG-иконки
└── middleware.js  Edge: JWT refresh для /admin/*
```

Импорт **только через `index.js`** слайса — ESLint завалит deep-paths.

## Документация

| Файл                                                             | О чём                                                         |
| ---------------------------------------------------------------- | ------------------------------------------------------------- |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)                   | FSD-слои, правила импортов, чеклист «куда положить новый код» |
| [`docs/ONBOARDING.md`](docs/ONBOARDING.md)                       | Старт за 5 минут — для новых разработчиков                    |
| [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md)                     | Соглашения: имена, стили, i18n, обработка ошибок, PR-чеклист  |
| [`docs/product-creation-flow.md`](docs/product-creation-flow.md) | Multi-step создание продукта (SKU + media)                    |
| `openapi/`                                                       | Снимки backend и image-backend OpenAPI                        |

## Контракт с backend

Browser **никогда не ходит в backend напрямую** — всё через BFF (`src/app/api/*`):

```
Browser ──cookie──► BFF (Next.js) ──Bearer──► Backend API (/api/v1/*)
                    BFF ──API-Key──► Image Backend (/api/v1/media/*)
```

JWT хранится в httpOnly cookies, refresh обрабатывает Edge middleware.

## Pre-commit

При `git commit` автоматически запускается `eslint --fix` + `prettier --write` для staged-файлов.
Не использовать `--no-verify` без явной причины.

## Перед PR

- [ ] `npm run lint` — 0 errors
- [ ] `npm run typecheck` — 0 errors
- [ ] `npm test` — все зелёные
- [ ] `npm run build` — успешный production build
- [ ] Новые слайсы экспортируют через `index.js`

## Лицензия

Внутренний проект, не публичный.
