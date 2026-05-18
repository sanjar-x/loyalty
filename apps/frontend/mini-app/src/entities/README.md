# `src/entities/` — Business entities

Бизнес-сущности проекта: «как **выглядит** заказ», «как достать пользователя
по id». Карточки, бейджи, read-only API, модель.

## Анатомия слайса

```
entities/<entity-name>/
├── ui/         # ProductCard, ProductBadge, OrderRow — read-only
├── model/      # типы (из codegen), селекторы, базовые хуки
├── api/        # RTKQ injectEndpoints для своего домена (cart endpoints,
│               # product endpoints — из старого lib/store/api.js)
├── lib/        # мапперы wire→UI, чистые utilities (из lib/adapters/)
├── server.js   # (опционально) server-only entry, если есть код с next/headers
└── index.js    # PUBLIC API
```

## Правила

- Может импортировать из: другие `entities/` (через index), `shared/`
- **Не может**: `features/`, `widgets/`, `app/`
- Cross-entity импорты разрешены через public API: `@/entities/cart` ✓,
  `@/entities/cart/api/cart-slice` ✗

## entity vs feature

- **`entities/<x>`** — read-only, описательное. «Карточка продукта», «бейдж
  статуса заказа», «RTKQ getProduct». **Не** делает мутации, **не** управляет
  процессом.
- **`features/<x>`** — active action. «Добавить в корзину», «оформить заказ»,
  «изменить статус». Композирует entities.

Грубое правило: если в компоненте есть **кнопка-действие** или
**multi-step флоу** → `features/`. Иначе → `entities/`.

## Текущие entity (заполняется по мере миграции)

- `product/`, `category/`, `brand/` — каталог
- `cart/`, `order/` — покупки
- `pickup-point/`, `recipient/` — логистика
- `favorite/`, `promocode/`, `referral/`, `review/` — engagement
- `user/` — профиль + TG-юзер
