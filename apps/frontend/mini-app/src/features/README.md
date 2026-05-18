# `src/features/` — User-facing actions

Слой пользовательских действий и бизнес-флоу. «Что пользователь **делает** с
сущностью» (фильтрует, добавляет в корзину, заполняет форму, оформляет заказ).

## Анатомия слайса

```
features/<slice-name>/
├── ui/         # React-компоненты
├── model/      # хуки, бизнес-стейт (Zustand, reducers)
├── api/        # RTKQ injectEndpoints (если фича добавляет endpoints)
├── lib/        # чистые утилиты, константы
├── config/     # статическая конфигурация (редко)
└── index.js    # PUBLIC API — единственный валидный путь импорта снаружи
```

## Правила

- Может импортировать из: `entities/` (через index), `shared/`, свои внутренности
- **Не может**: другие `features/` (cross-feature запрещён — поднимать в `entities/`/`shared/`)
- Внутри slice: относительные пути (`./model/store`), не `@/features/X/model/store`
- Снаружи: только `@/features/X` (public API)

## Текущие slice'ы (заполняется по мере миграции)

- `auth-telegram/` — Telegram initData → JWT bootstrap, AuthGate
- `telegram-api/` — wrapper над `window.Telegram.WebApp` (haptic, openLink, ...)
- `add-to-cart/` — QuickAddSheet + ProductAddToCart
- `checkout-flow/` — FSM, оркестратор, sheets
- `pickup-selection/` — Leaflet map + viewport + URL-state
- `recipient-form/` — useRecipientForm + RecipientSheet
- `search/`, `favorites/`, `promocode/`, `invite-friends/`, `home-feed/`, `profile-edit/`
