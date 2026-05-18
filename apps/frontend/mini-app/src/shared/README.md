# `src/shared/` — Техника, не зависящая от домена

Переиспользуемые примитивы **без бизнес-логики**: UI-компоненты не
привязанные к сущности, утилиты, API-клиенты, технические хуки.

## Структура

```
shared/
├── api/
│   ├── base-api/       # RTKQ createApi с baseQuery, refresh, idempotency
│   ├── codegen/        # __generated__/ — schema.d.ts, api.ts
│   ├── bff/            # утилиты для BFF route handlers
│   └── errors/         # error envelope helpers
├── ui/                 # Button, BottomSheet, Toaster — без бизнес-привязки
├── lib/
│   ├── money/          # MoneyResponse helpers, format, parse, math (копейки!)
│   ├── date/           # date format/parse
│   ├── url/            # query-string, slug helpers
│   ├── hooks/          # useDebounce, useLockBodyScroll, useIsomorphicLayoutEffect
│   ├── events/         # EventTarget pub/sub (auth-events)
│   ├── ios/            # InputFocusFix — iOS Safari quirks
│   ├── dev/            # InitTelegramMock — dev-only
│   └── ui-utils/       # cn(), helpers для UI
├── config/
│   ├── env/            # env validation
│   └── feature-flags/  # feature flag helpers
└── types/              # глобальные типы (если нужно)
```

## Правила

- Может импортировать **только из `shared/`**.
- **Не может**: `entities/`, `features/`, `widgets/`, `app/`.
- Если хочется импортировать сущность → значит модуль **не shared**,
  поднимай в соответствующий entity.

## Public API

Каждая подпапка (`shared/lib/money/`, `shared/ui/Button/`, ...) экспортирует
через `index.js`. Снаружи импорт: `@/shared/lib/money`, `@/shared/ui/Button`.
