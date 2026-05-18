# Architecture Code Review — Mini-App

> Дата: **2026-05-17** · Ветка: `refactor/mini-app-fsd` (после Phase 12)
> Стандарт: **Feature-Sliced Design** (см. `apps/frontend/admin/eslint.config.mjs` как референс)
> Метод: 4 параллельных explorer-агента + ручная инвентаризация
> Объём кода: **64 176 строк** в 277 файлах (без codegen — ~30 000)
>
> ## Статус выполнения (обновлено 2026-05-17, 10 коммитов)
>
> | Sprint | Статус | Эффект |
> |---|---|---|
> | 1.1 Dead code removal | ✅ Done | 6 stub-slices + 4 пустых каталога + 3 server.js + 3 UI удалены |
> | 1.2 formatRub дедуп | ✅ Done | 11 локальных копий → 1 shared/lib/money/formatRub |
> | 1.3 pluralize/numberFmt дедуп | ✅ Done | 7 функций FiltersSheet ≡ PriceSheet → features/search/lib/priceInput |
> | 1.4 resolveI18N → shared | ✅ Done | 3 cross-entity deep imports устранены |
> | 1.5 ESLint clsx + naming | ✅ Done | 36 файлов мигрированы на `cn`, BrandCard rename, ESLint rule добавлен |
> | 2.1 validators split | ✅ Done | 375 строк бизнес-логики разнесены: shared/lib/{phone,card}, entities/recipient, features/checkout-flow/lib/validators |
> | 2.1 FormField rename | ✅ Done | CheckoutFormField → FormField (generic) |
> | 2.2 errors codes split | ✅ Done | Checkout-codes → features/checkout-flow/lib/errors |
> | 2.2 backendAssets → entities | ✅ Done | buildProductPhotoUrl, buildBrandLogoUrl в entities |
> | 3a authStatus DI | ✅ Done | Lazy require устранён, getter seam |
> | 3b sheet slots DI | ✅ Done | entity → feature warning ушло, useSyncExternalStore-based slots |
> | 4 *Client → widgets | ✅ Done | 8 файлов + co-located checkout/_home переехали (~2700 строк) |
> | 5 god-pages dead code | ✅ Partial | Удалены закомментированные блоки (ProductPage: -75 строк, checkout: -60 строк) |
> | 6 god-components разбор | ⏭ Backlog | Требует careful UI рефакторинга, отдельные PR'ы |
> | 7 tests + ESLint error level | ⏭ Backlog | Требует написания тестов для 18/25 slice'ов |
>
> **Метрики после Sprint 1-5**:
> - ESLint: **0 errors, 122 warnings** (без Sprint 3 cross-feature lift)
> - Tests: **288 passed, 9 skipped** (все зелёные после каждого коммита)
> - Removed: ~700 строк dead code, 11 копий formatRub, 7 дублей priceInput helpers
> - Moved: ~2700 строк *Client.jsx в widgets/
> - Created: 5 новых shared/entity модулей (phone, card, photoUrl, logoUrl, sheetSlots, authStatus)
>
> **Оставшиеся cross-feature warnings (6, для Sprint 3c)**:
> - features/auth-telegram → features/telegram-api (TelegramProvider)
> - features/favorites → features/auth-telegram (useAuthStore + AuthStatus)
> - features/pickup-selection → features/checkout-flow (useCheckoutStore + geo)
>
> **Оставшиеся god-pages (для Sprint 6)**:
> - app/page.jsx (759), app/cart/page.jsx (682), profile/settings (565),
>   checkout/pickup (552), profile/reviews/[brand] (449)
> - widgets/ProductPage (801, после -75), widgets/OrderDetailsPage (437)

## TL;DR — Health Score

| Аспект | Оценка | Комментарий |
| --- | --- | --- |
| **FSD-структура** | 7/10 | Каркас правильный, миграция Phase 1-12 успешна |
| **Public API hygiene** | 4/10 | 104 deep-imports, 8 cross-layer violations |
| **Cross-layer purity** | 3/10 | `features → app/providers/store` (10 файлов), `entities → features`, `shared → features` lazy require |
| **God-components** | 4/10 | 7 файлов >440 строк, итого ~3 500 строк надо разбить |
| **shared/ чистота** | 5/10 | Бизнес-логика в shared (validators 375 строк), хардкод-привязки |
| **Code duplication** | 3/10 | `formatRub` × 11 копий с разным поведением, `pluralizeItemsRu` дубль |
| **Dead code** | 6/10 | 6 пустых slice'ов, 3 неиспользуемых server.js, 3 мёртвых UI |
| **Tests coverage** | 5/10 | 288 тестов, но 18/25 slice'ов без тестов; widgets — 0 |
| **Naming consistency** | 9/10 | Почти безупречно |
| **ESLint health** | — | 0 errors, **118 warnings** |

**Общий вердикт**: FSD-каркас построен правильно, но **миграция не завершена** в нескольких ключевых точках:
1. RTKQ-хуки централизованы в `app/providers/store` — нарушает слой
2. `*Client.jsx` pattern застрял в `app/` — должны быть в `widgets/`
3. Бизнес-валидация осела в `shared/` вместо `features/`
4. 6 «зарезервированных» пустых slice'ов создают иллюзию полноты

---

## 1. P0 — Critical (архитектурные нарушения FSD)

### 1.1 `shared/api/base-api/baseApi.js:11-25` — lazy require обходит ESLint

```js
let _useAuthStore = null;
function getAuthStatus() {
  if (!_useAuthStore) {
    _useAuthStore = require('@/features/auth-telegram/model/store').useAuthStore;
  }
  // ...
}
```

Сам комментарий в файле признаёт нарушение («FSD: shared/* не должен импортировать features/*»). Это **единственный** обход в проекте, но он нивелирует чистоту всего `shared/`.

**Fix**: Заменить на event-bus pattern (`shared/lib/events` уже есть) — features подписываются и публикуют status; baseQuery читает только из event'а. Альтернатива: dependency injection через RTKQ `extraArgument` в `configureStore`.

---

### 1.2 `features → app/providers/store` — 10 файлов нарушают слой

```
src/features/auth-telegram/ui/TelegramAuthBootstrap.jsx:10
src/features/search/ui/SearchOverlay.jsx:10
src/features/checkout-flow/model/useCheckoutFlow.js:15,34
src/features/pickup-selection/model/usePvzData.js:5
src/features/home-feed/ui/CategoryTabs.jsx:4
src/features/home-feed/model/useForYouFeed.js:5
src/features/home-feed/model/useHomeFilters.js:9
src/features/favorites/model/useItemFavorites.js:11
src/features/favorites/model/useFavoriteLists.js:5
```

По FSD `features` может импортировать из `entities`, `shared`, своих внутренностей — НЕ из `app`. Сейчас RTKQ-хуки (`useGetProductsQuery`, `useAddCartItemMutation`, etc.) собраны в **monolith barrel** `app/providers/store/hooks.js` (402 строки), который реэкспортирует ВСЁ.

**ESLint не ловит** это нарушение — в `eslint.config.mjs` нет правила запрета `@/app/*` в features (только в shared/entities).

**Fix (2 опции)**:
- **A. Канонический FSD**: разнести `hooks.js` по доменам — `entities/cart/api/hooks.js`, `entities/order/api/hooks.js`, `features/checkout-flow/api/hooks.js`. Каждый entity `injectEndpoints` свои хуки. `app/providers/store/configure.js` остаётся только assembly.
- **B. Прагматичный**: переместить hooks barrel в `shared/api/store/hooks.js` (formally — это thin adapter над codegen). Тогда features могут импортировать без нарушения слоя. Минус: assembly endpoints из entities остаётся в `instance.js`, что либо в shared, либо в app — компромисс.

Рекомендую **(A)** — это правильный FSD-путь и убирает централизованную «точку отказа».

---

### 1.3 `entities → features` — entity знает о feature (2 файла)

```
src/entities/product/ui/ProductCard.jsx:10 → @/features/add-to-cart (QuickAddSheet)
src/entities/product/ui/ProductPrice.jsx:5 → @/features/add-to-cart (SplitPaymentSheet)
```

Entity (пассивное представление сущности) не должен знать о user-action (feature). Это инвертирует pyramid FSD.

**Fix**: render-prop / slot composition. `ProductCard` принимает `actionSlot` пропом, который вызывающий widget (например, `widgets/CatalogPage`) заполняет нужным `QuickAddSheet`.

---

### 1.4 Cross-feature imports — 5 файлов (ESLint warn)

```
features/auth-telegram/ui/TelegramAuthBootstrap.jsx:5 → @/features/telegram-api/model/provider
features/favorites/model/useFavoriteLists.js:6,7      → @/features/auth-telegram/model/{store,types}
features/pickup-selection/model/useLeafletPvzMap.js:5  → @/features/checkout-flow
features/pickup-selection/model/usePickupFromUrl.js:6  → @/features/checkout-flow
features/pickup-selection/model/usePvzData.js:7        → @/features/checkout-flow
```

**Fix**:
- `useAuthStore` и `AuthStatus` нужны 3+ features → **поднять в `entities/user/`** (или `shared/lib/auth-state/` если предпочтительнее).
- `useCheckoutStore` нужен `pickup-selection` → **выделить «pickup-context» в entity** (`entities/checkout-context/`) либо в shared event-bus.
- `TelegramProvider` контекст → `entities/user/` (telegram user — это сущность пользователя).

---

### 1.5 `shared/lib/validators/validators.js` — 375 строк бизнес-логики в shared

Файл содержит:
- `validateCardDraft` — **checkout/payment domain**
- `validateRecipient`, `validateRecipientForOrder` — **recipient-form domain** (CHK-002)
- `validateCustoms`, `validateCustomsStrict` — **международная доставка domain**
- `PHONE_FORMATS`, `normalizePhoneDigits`, `formatPhone` — **OK для shared** (5 country definitions)

**Fix — разнести**:
- `features/checkout-flow/lib/validators/card.js` (Luhn, expiry, holder)
- `features/recipient-form/lib/validators/recipient.js`
- `features/checkout-flow/lib/validators/customs.js`
- `shared/lib/phone/` (только phone helpers)

---

### 1.6 `shared/ui/CheckoutFormField/` — checkout-привязка в имени

JSDoc сам признаёт: «CHK-022 Layer 2: shared floating-label form field for **checkout sheets**».

**Fix**: переименовать в `shared/ui/FormField/` или `FloatingInput/`, убрать `Checkout` из имени, CSS-классов и JSDoc. Реализация generic — это просто floating label input.

---

## 2. P1 — High (бизнес в shared + дубликаты)

### 2.1 `shared/lib/anonymous-token/anonymousToken.js:68-99` — fetch в shared

`ensureAnonymousToken()` делает прямой `fetch('/api/backend/api/v1/cart/anonymous-token')` — это часть auth-flow, не «storage helper».

**Fix**: вынести fetch в `entities/cart/api/` или `features/auth-telegram/`. Storage-обёртка (`getAnonymousToken/setAnonymousToken/clearAnonymousToken`) остаётся в shared.

### 2.2 `shared/api/errors/errors.js:24-45` — checkout error codes в shared

`QUOTE_EXPIRY_CODES`, `PROVIDER_RETRY_CODES`, `CURRENCY_MISMATCH_CODES` — checkout-домен.

**Fix**: перенести в `features/checkout-flow/lib/errors.js`. В shared остаётся `normalizeApiError` + `isTokenExpiredError`.

### 2.3 `shared/lib/url/backendAssets.js` — product/brand хелперы в shared

`buildProductPhotoUrl`, `buildBrandLogoUrl` — бизнес-привязка к сущностям.

**Fix**: в `entities/product/lib/photoUrl.js` и `entities/brand/lib/logoUrl.js`. Generic `buildBackendAssetUrl` остаётся.

### 2.4 `shared/ui/BottomSheet.jsx` — feature-aware пропсы

Props `isReview`, `isPromocodePage`, `isTypeModule`, `isFilter` (lines 12-25) + CSS-классы `styles.isReview` — feature утекает в shared через boolean-props. Hardcoded `<img src="/icons/global/markXBlack.svg">` (line 138).

**Fix**: заменить boolean-props на `variant: 'review'|'filter'|'default'` (если эти варианты вообще нужны — вероятно нет, можно через composition). Иконку — через prop `closeIcon`.

### 2.5 `formatRub` — 11 копий с расхождением поведения

| Файл | NaN | Separator |
| --- | --- | --- |
| `app/cart/page.jsx:20` | `${NaN} ₽` | space-thin |
| `app/favorites/page.jsx:44` | `''` | space |
| `app/product/[slug]/ProductPageClient.jsx:69` | `'—'` | space |
| `app/profile/orders/OrdersClient.jsx:12` | `' ₽'` без пробела | `₽` |
| `app/profile/orders/[id]/OrderDetailsClient.jsx:13` | `' ₽'` | space |
| `app/profile/returns/page.jsx:21` | `' ₽'` | space |
| `app/profile/returns/create/CreateReturnClient.jsx:11` | `' ₽'` | space |
| `app/profile/returns/request/[id]/ReturnRequestClient.jsx:11` | `' ₽'` | space |
| `app/profile/reviews/[brand]/page.jsx:25` | `''` если ≤0 | space |
| `features/add-to-cart/ui/QuickAddSheet.jsx:99` | `'—'` если ≤0 | space |
| `features/add-to-cart/ui/SplitPaymentSheet.jsx:17` | `''` если ≤0 | space |

В `shared/lib/money/price.js:18` уже есть `formatRubFloat` — никто им не пользуется.

**Fix**: один `shared/lib/money/format.js#formatRub(value, opts)` с явными опциями (`emptyAs`, `currency`). Удалить все локальные. Этой же миграцией:
- `pluralizeItemsRu` в `app/cart/page.jsx:28` (дубль `shared/lib/i18n/plural.js`)
- `formatNumber`/`formatNumberFromDigits`/`buildCurrencyValue` в `FiltersSheet.jsx:22-37` ≡ `PriceSheet.jsx:21-36` (побайтовый дубль)
- `formatRuPhone` в `app/profile/settings/page.jsx:164` (есть `shared/lib/validators/formatPhone`)
- `asNonEmptyTrimmedString`, `asSafeImageSrc` дублируется в `profile/page.jsx` и `profile/settings/page.jsx`

### 2.6 `resolveI18N` — sibling deep-entity import

`entities/category/api/taxonomy.endpoints.js:5` и `entities/category/lib/mapCategoryTree.js:1` импортируют `resolveI18N` из `@/entities/product/lib/mapStorefrontProduct` — это generic i18n helper, не product-specific.

**Fix**: поднять в `shared/lib/i18n/resolveI18N.js`. Заодно решит cross-entity deep-import.

---

## 3. P2 — Medium (god-components)

### 3.1 7 god-pages → план разбиения (детальный план в Phase-9 TODO)

| Файл | Сейчас | Цель | Куда выносить |
| --- | --- | --- | --- |
| `app/product/[slug]/ProductPageClient.jsx` | 888 | ~140 | helpers → `entities/product/lib/`, breadcrumbs → `entities/product/ui/`, `handleBuyNow` → `features/add-to-cart/model/`, clipboard → `shared/lib/`, **75 строк закомментированного InfoCards удалить** |
| `app/page.jsx` | 759 | ~180 | sheet states → `features/home-feed/model/useHomeSheets`, 6 BottomSheets (~120 строк) → `widgets/HomePage/HomeFilterSheets`, scroll-hide → `shared/lib/hooks/` |
| `app/cart/page.jsx` | 697 | ~100 | `CartItemRow` (~133) → `entities/cart/ui/`, promo input → `features/promocode/`, summary → `features/cart/`, sticky bar → `features/checkout-flow/ui/`, **TEST_PROMO_CODES хардкод убрать** |
| `app/profile/settings/page.jsx` | 565 | ~90 | RecipientSheet → **переиспользовать существующий** `features/recipient-form/ui/RecipientSheet.jsx` (-111 строк), validators дубль → удалить (-50 строк), pickup sheet → feature |
| `app/checkout/pickup/page.jsx` | 552 | ~120 | 3 step branches → `features/pickup-selection/ui/{Pvz{Map,AddressSearch,List}View}.jsx`, callbacks → `usePvzPageActions` |
| `app/profile/reviews/[brand]/page.jsx` | 449 | ~90 | 6 локальных компонентов (`Stars`, `ReviewCard`, ...) → `entities/review/ui/`, SortSheet → `features/search/ui/` |
| `app/profile/orders/[id]/OrderDetailsClient.jsx` | 444 | ~80 | `TrackingTimeline` (113) → `entities/order/ui/`, 5 subcomponents → `entities/order/ui/`, totals card → `entities/order/ui/` |

**Эффект**: ~3 500 → ~800 строк в god-pages, ~2 700 строк уйдут в widgets/features/entities.

### 3.2 `*Client.jsx` pattern застрял в `app/` (8 файлов)

```
app/product/[slug]/ProductPageClient.jsx       (888)
app/profile/orders/[id]/OrderDetailsClient.jsx (444)
app/profile/returns/create/CreateReturnClient  (394)
app/profile/purchased/review/[id]/ReviewClient (369)
app/profile/orders/OrdersClient                 (250)
app/profile/returns/request/[id]/ReturnRequestClient (152)
app/catalog/[...path]/CategoryPageClient        (113)
app/catalog/CatalogPageClient                   (60)
```

Это полу-готовый рефакторинг: page.jsx тонкие (10-19 строк), но `*Client.jsx` — толстые «client component body» — лежат в route folder вместо `widgets/`.

**Особо плохо**: `OrderDetailsClient` импортируется из других routes (`../../[id]/OrderDetailsClient`) — cross-route relative imports.

**Fix**: переезд всех 8 файлов в `widgets/{PageName}/{PageName}.jsx`. Уберёт ~2 700 строк из `app/`.

### 3.3 `app/_home/` + `app/checkout/{Items,Summary,...}.jsx` — co-located не там

- `app/_home/FilterChipsBar.jsx` (250) + `HomeFeed.jsx` (92) → `widgets/HomePage/`
- `app/checkout/{CheckoutItemsList,CheckoutSummary,CheckoutTiles,PaymentMethodPicker,PayButtonFooter}.jsx` (432 строки в 5 файлах) → `widgets/CheckoutPage/`
- `app/checkout/pickup/{ProviderChips,PickupModeToggle}.jsx` → `features/pickup-selection/ui/`

JSDoc каждого файла уже говорит «Audit #1: god-komponentidan ajratilgan» — миграция начата, но не завершена.

### 3.4 Толстые non-god файлы (>400 строк)

```
features/checkout-flow/model/useCheckoutFlow.js   815
features/pickup-selection/model/useLeafletPvzMap  667
features/search/ui/FiltersSheet.jsx              653
features/add-to-cart/ui/QuickAddSheet.jsx        541
app/providers/store/hooks.js                     402
```

`useCheckoutFlow.js` — orchestrator FSM (приемлемо для центра домена, но 815 — много). `useLeafletPvzMap` — Leaflet imperative API (тоже сложно разбить). `FiltersSheet` — кандидат на дробление.

---

## 4. P3 — Low (dead code + cleanup)

### 4.1 Безопасно удалить ПРЯМО СЕЙЧАС

**Пустые stub-slice'ы (6)** — `export {}` без импортов:
- `src/features/{invite-friends,promocode,profile-edit}/` (включая папки)
- `src/entities/{recipient,referral,user}/`

**Пустые каталоги (4)**:
- `src/shared/config/env/`
- `src/shared/types/`
- `src/shared/lib/date/` (конфликт с `date-format/`)
- `src/shared/lib/icons/`

**Мёртвые server.js (3)** — нет импортов:
- `entities/product/server.js`
- `entities/category/server.js`
- `features/auth-telegram/server.js` (использующие импортируют напрямую из `lib/cookie-helpers`)

**Мёртвые UI компоненты**:
- `entities/review/ui/ReviewCard.jsx` (есть в barrel, никто не импортирует; в page.jsx определяют свои локальные)
- `entities/product/ui/ProductReviews.jsx` (есть в barrel, нигде не импортируется)
- `features/home-feed/ui/ArticlesRow.jsx` (есть в barrel, нигде не импортируется)

**Мёртвые экспорты**:
- `FEATURES` в `shared/config/feature-flags/featureFlags.js` — упомянуто только в комментарии
- `moneyResponseToMoney` в `entities/cart/lib/cartHelpers.js:34` — сам комментарий: «Hozir bu fayl ichida hech qaerda chaqirilmaydi»

### 4.2 Раздутые barrels (>10 экспортов = плохая инкапсуляция)

| Slice | Экспорты | Проблема |
| --- | --- | --- |
| `entities/product` | **24** | 10 UI + 5 lib групп через `export *` (показывает `resolveI18N`, `getVariantThumbnail`, mappers — детали реализации) |
| `features/checkout-flow` | **~50** | 8 lib через `export *` — десятки функций/констант наружу |
| `features/home-feed` | 10 | 4 хука + utils + 5 UI компонентов (граница) |

**Fix**: явные named-экспорты только нужных snaружи имён, без `export *`. Lib-функции выставлять только если другие slice'ы их зовут.

### 4.3 Косметика

- `entities/cart/api/cart.endpoints.js` — `import { ... } from '@/entities/cart/lib/cartHelpers'` (deep self-alias). Заменить на `from './lib/cartHelpers'`.
- `entities/cart/lib/cartHelpers.js` экспортит через `export *` — раскрывает деталь `moneyResponseToMoney`.
- `app/profile/_shared/comingSoon.module.css` — единственное расхождение naming: `camelCase` для CSS-модуля, тогда как компонент `ComingSoon.jsx`. Переименовать в `ComingSoon.module.css`.
- Стилевой разнобой `cn` vs `cx` vs `clsx` — добавить ESLint правило: запретить `from 'clsx'` напрямую, требовать `@/shared/lib/ui-utils`.
- 2 разных `BrandCard.jsx` в `features/favorites/ui/` — переименовать в `FavoriteBrandCard` и `CatalogBrandCard`.
- `features/favorites/ui/brands/*` (4 файла: `AllBrandsList`, `BrandCard`, `BrandsSearch`, `FavoriteBrandsSection`) импортируются из `app/favorites/brands/page.jsx:6-8` напрямую через deep-paths — добавить в `index.js`.
- `shared/api/codegen/` → переименовать в `__generated__/` (явность авто-генерации).
- `shared/api/bff/backendBaseUrl.js` → переехать в `shared/config/env/` (логичнее).
- `src/proxy.js` — корректное расположение для Next.js 16 (нового convention).

---

## 5. Tests coverage — перекос

```
features: 16 test files  (12 в checkout-flow!)
entities:  2 test files  (product/lib, pickup-point/lib)
widgets:   0 test files
shared:    6 test files
app:       0 test files
```

**288 тестов, 18 из 25 slice'ов без тестов**:

| Категория | Без тестов |
| --- | --- |
| features | auth-telegram, favorites, home-feed, invite-friends, profile-edit, promocode, search, telegram-api |
| entities | brand, cart (!), category, favorite, order, promocode, recipient, referral, review, user |
| widgets | все |

**Критично**: `entities/cart/model/useCart.js` — нет тестов, хотя содержит бизнес-логику добавления/удаления + sync с RTKQ.

**Fix**: добавить тесты на:
- `entities/cart/model/useCart` — `add`, `remove`, `updateQty`, `merge` flow
- `features/auth-telegram/model/store` — FSM transitions
- `features/home-feed/model/useHomeFilters` — фильтр-логика
- `features/search/model/history` — localStorage CRUD

---

## 6. ESLint health

```
✖ 118 problems (0 errors, 118 warnings)
   104 — deep imports (обход public API через index.js)
     8 — cross-feature/cross-layer (5 ОПИСАНЫ В P0/P1)
     6 — react-hooks (refs in render + exhaustive-deps)
```

**Текущая стратегия**: уровень `warn`, обоснованно — фон god-components не позволяет включить `error` без массового рефакторинга. Это **временная норма до Phase 9**.

**Цель**: после P0+P1+P2 — переключить `no-restricted-imports` на `error`. Добавить в config:
1. Запрет `features → @/app/*` (сейчас ESLint этого не ловит)
2. Запрет `from 'clsx'` напрямую → `@/shared/lib/ui-utils`
3. Запрет `require()` в src/ (закрытие лазейки в baseApi.js)

---

## 7. Roadmap — порядок работ

### Sprint 1 — Quick wins (1-2 дня)

1. **Удалить мёртвый код** (раздел 4.1) — 6 stub-slice'ов, 4 пустых каталога, 3 server.js, 3 UI, 2 экспорта.
2. **Удалить закомментированные блоки** в `ProductPageClient.jsx:729-764` и `checkout/page.jsx:328-388`.
3. **`formatRub` дедуп** (раздел 2.5) — 11 → 1 в `shared/lib/money/format.js`. Сразу же `pluralizeItemsRu`, `formatNumber`.
4. **`resolveI18N`** → `shared/lib/i18n/` (раздел 2.6).
5. **Косметика** (раздел 4.3) — naming, ESLint clsx-правило, переименование 2 `BrandCard`.

### Sprint 2 — Shared cleanup (2-3 дня)

1. **`shared/lib/validators/validators.js`** разнести по features (раздел 1.5).
2. **`shared/ui/CheckoutFormField/`** → `FormField/` (раздел 1.6).
3. **`shared/lib/anonymous-token`** — fetch в `entities/cart/api/` (раздел 2.1).
4. **`shared/api/errors`** — checkout codes в `features/checkout-flow/lib/errors` (раздел 2.2).
5. **`shared/lib/url/backendAssets`** — split по entities (раздел 2.3).
6. **`shared/ui/BottomSheet`** — убрать boolean-props (раздел 2.4).

### Sprint 3 — Layer purity (3-5 дней)

1. **RTKQ-hooks refactor** (раздел 1.2) — option A: разнести по `entities/*/api/hooks.js` и `features/*/api/hooks.js`. Уберёт 10 нарушений features → app.
2. **`baseApi.js` lazy require** (раздел 1.1) — заменить на event-bus.
3. **`entities → features`** (раздел 1.3) — `ProductCard`/`ProductPrice` через slot composition.
4. **Cross-feature** (раздел 1.4) — `useAuthStore`, `useCheckoutStore`, `TelegramProvider` поднять в entities/shared.
5. Добавить ESLint правило `features → @/app/*` запрет; включить `error` уровень.

### Sprint 4-6 — God-components (Phase 9)

Идти по таблице раздела 3.1 + 3.2 + 3.3 — по 1-2 god-page'а за PR:

1. PR1: переезд 8 `*Client.jsx` в `widgets/` (~2700 строк перемещаем без логических изменений).
2. PR2: `app/_home/` → `widgets/HomePage/`; `app/checkout/*` → `widgets/CheckoutPage/`.
3. PR3-7: разбор каждого god-page по плану раздела 3.1 (по 1 PR на page).
4. Добавить тесты на extracted хуки.

### Sprint 7 — Test coverage

1. **`entities/cart/model/useCart`** — критично, есть бизнес-логика.
2. Покрыть auth-telegram store FSM, home-feed filters, search history.
3. Сделать минимум 1 widget test (`HomePage` или `CheckoutPage`).

---

## 8. Acceptance criteria (после roadmap)

- ✅ 0 ESLint warnings
- ✅ Все `src/app/**/page.jsx` ≤ 50 строк
- ✅ Ни одного файла > 400 строк (кроме автогенерата codegen)
- ✅ Ни одного `require()` в `src/`
- ✅ Ни одного импорта `@/app/*` из `features/entities/widgets/shared`
- ✅ Ни одного импорта `@/features/*` из `entities/shared`
- ✅ Ни одного `formatRub`/`pluralizeItemsRu` определения вне `shared/lib/`
- ✅ Все 25 slice'ов либо имеют тесты, либо удалены
- ✅ `ESLint no-restricted-imports` уровня `error`

---

## Приложение A — Метрики

```
Файлов:      277 (без node_modules, .next)
Строк:       64 176 (codegen api.ts: 9356, schema.d.ts: 23919)
По слоям:
  app:     73 файла, 11 561 строк
  widgets: 10 файлов,    957 строк
  features: 89 файлов, 10 871 строк
  entities: 54 файла,   4 815 строк
  shared:  50 файлов,  35 904 строк (из них ~33 000 codegen)

Tests: 24 файла, 288 passed, 9 skipped
Slices: 12 features + 13 entities = 25
ESLint: 0 errors, 118 warnings (104 deep + 8 cross-layer + 6 react-hooks)
```

## Приложение B — Изменённые правила ESLint (для финализации)

```js
// eslint.config.mjs — после Sprint 3
{
  rules: {
    'no-restricted-imports': ['error', /* ... */],  // warn → error
    'no-restricted-syntax': ['error', {
      selector: 'CallExpression[callee.name="require"]',
      message: 'Use ES imports. require() is forbidden in src/.',
    }],
  },
},
{
  files: ['src/features/**'],
  rules: {
    'no-restricted-imports': ['error', {
      patterns: [
        { group: ['@/app/*'], message: 'features must not depend on app/* — see FSD' },
      ],
    }],
  },
},
{
  rules: {
    'no-restricted-imports': ['error', {
      paths: [{ name: 'clsx', message: 'Use cn() from @/shared/lib/ui-utils' }],
    }],
  },
},
```
