# Phase 9 — God-components TODO

> Side-effect миграции на FSD: god-components **существенно уменьшились**
> (вынос hooks/blocks в `features/` и `entities/` сократил размер pages
> в 2-3 раза). Окончательное добивание остаётся как отдельный фоллоу-ап.

## Before/After (на момент завершения Phase 8)

| Файл                                       | До миграции | После миграции | Цель |
| ------------------------------------------ | ----------- | -------------- | ---- |
| `app/checkout/pickup/page.jsx`             | 1569        | **552** ↓65%   | ≤200 |
| `app/page.jsx`                             | 1160        | **759** ↓35%   | ≤200 |
| `app/checkout/page.jsx`                    | 933         | **440** ↓53%   | ≤300 |
| `app/product/[slug]/ProductPageClient.jsx` | 918         | **873** ↓5%    | ≤250 |
| `app/cart/page.jsx`                        | —           | **697**        | ≤300 |
| `app/profile/settings/page.jsx`            | —           | **565**        | ≤200 |

## Что ещё разделить

### `src/app/page.jsx` (759 строк) — главная

Вынести в `src/widgets/HomePage/`:

- `HomeFeed.jsx` — собственно лента (уже есть в `_home/`, лежит рядом)
- `FilterChipsBar.jsx` — горизонтальные чипы фильтров (тоже в `_home/`)
- `HomeSearchInput` — поисковая строка

Хуки из inline → `features/home-feed/model/`:

- `useHomeSearchPipeline` — pipe фильтров через RTKQ + локальные `useHomeSearch`
- `useFilterSheetsState` — multi-sheet open/close FSM

После — `page.jsx = <HomePage />` (5-10 строк).

### `src/app/checkout/pickup/page.jsx` (552 строк) — PVZ карта

Вынести в `widgets/PickupPage/`:

- `PickupMapView.jsx` — собственно Leaflet
- `PickupListView.jsx` — список
- `PickupSearchHeader.jsx` — поиск города + step navigation

Хуки в `features/pickup-selection/model/`:

- `useStepFSM` — map/list/search step routing (уже есть `useBackHandlerStore`
  для BackButton — связать)
- `useLeafletViewport` — viewport bounds → query параметры

### `src/app/cart/page.jsx` (697 строк) — корзина

Вынести в `widgets/CartPage/`:

- `CartItemRow.jsx` — одна строка товара с qty/удалить
- `CartBulkSelector.jsx` — мульти-выбор + bulk actions
- `CartTotalsBar.jsx` — низ с итогами и CTA

Composite hook в `features/checkout-flow/model/`:

- `useCartSelection` — multi-select FSM

### `src/app/checkout/page.jsx` (440 строк) — checkout

Вынести в `widgets/CheckoutPage/`:

- Уже есть несколько компонентов сбоку (`CheckoutItemsList`, `CheckoutSummary`,
  `CheckoutTiles`, `PayButtonFooter`, `PaymentMethodPicker`). Сейчас они в
  `src/app/checkout/`. Переехать в `widgets/CheckoutPage/`.

### `src/app/product/[slug]/ProductPageClient.jsx` (873 строк) — PDP

Вынести в `widgets/ProductPage/`:

- `ProductHero.jsx` — карусель + цена + бейджи
- `ProductDetailsSection.jsx` — атрибуты, описание
- `ProductRecommendations.jsx` — similar + also-viewed

Sections в `entities/product/ui/sections/` (если они общие).

### `src/app/profile/settings/page.jsx` (565)

Вынести forms в `features/profile-edit/ui/` + `features/profile-edit/model/`.

### `src/app/profile/reviews/[brand]/page.jsx` (449)

Брендовая страница reviews — в `widgets/BrandReviewsPage/`.

## Стратегия

- Делать по одному pages за PR — гранулярно для code review.
- Каждый рефакторинг сопровождать unit-тестом на extracted хук.
- В каждом PR: page.jsx уменьшается до ≤300 строк, новые модули в `widgets/`/`features/`/`entities/`.

## Acceptance criteria

После завершения Phase 9 каждый файл в `src/app/**/page.jsx` должен быть **≤300 строк** (мягко) или **≤200 строк** (стремление). Любая страница > 300 строк должна иметь обоснование в README ближайшего widget'а.
