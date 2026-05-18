# Mini-App FSD Migration

> Карта миграции `frontend/mini-app` на Feature-Sliced Design (1-в-1 с
> `apps/frontend/admin/`). Ветка: `refactor/mini-app-fsd`.
> План: 13 фаз (см. внизу).

## Mapping «было → станет»

### shared (Phase 3)

| Текущий путь                          | Новый путь                             |
| ------------------------------------- | -------------------------------------- |
| `lib/format/money.js`                 | `src/shared/lib/money/`                |
| `lib/format/date.js`                  | `src/shared/lib/date/`                 |
| `lib/url/`                            | `src/shared/lib/url/`                  |
| `lib/hooks/`                          | `src/shared/lib/hooks/`                |
| `lib/api/errors.js`                   | `src/shared/api/errors/`               |
| `lib/api/server/`                     | `src/shared/api/bff/`                  |
| `lib/auth-events.js`                  | `src/shared/lib/events/`               |
| `lib/featureFlags.js`                 | `src/shared/config/feature-flags/`     |
| `components/ui/Button.jsx`            | `src/shared/ui/Button/`                |
| `components/ui/BottomSheet.jsx`       | `src/shared/ui/BottomSheet/`           |
| `components/ui/Toaster.jsx`           | `src/shared/ui/Toaster/`               |
| `components/ios/InputFocusFix.tsx`    | `src/shared/lib/ios/InputFocusFix/`    |
| `components/dev/InitTelegramMock.jsx` | `src/shared/lib/dev/InitTelegramMock/` |
| `lib/ui/`                             | `src/shared/lib/ui-utils/`             |

### shared/api (Phase 4)

| Текущий путь                          | Новый путь                                |
| ------------------------------------- | ----------------------------------------- |
| `lib/store/baseApi.js`                | `src/shared/api/base-api/baseApi.js`      |
| `lib/store/store.js`                  | `src/shared/api/base-api/store.js`        |
| `lib/store/hooks.js`                  | `src/shared/api/base-api/hooks.js`        |
| `lib/store/transformers.js`           | `src/shared/api/base-api/transformers.js` |
| `lib/store/__generated__/api.ts`      | `src/shared/api/codegen/api.ts`           |
| `lib/store/__generated__/schema.d.ts` | `src/shared/api/codegen/schema.d.ts`      |
| `lib/store/__generated__/index.ts`    | `src/shared/api/codegen/index.ts`         |

### entities (Phase 5) — разбор `lib/store/api.js` + `components/blocks/<entity>`

| Текущее                                             | Новое                                           |
| --------------------------------------------------- | ----------------------------------------------- |
| RTKQ endpoints для products + `mapProductCard`      | `src/entities/product/`                         |
| RTKQ endpoints для categories + `mapCategoryTree`   | `src/entities/category/`                        |
| RTKQ endpoints для brands                           | `src/entities/brand/`                           |
| RTKQ endpoints для cart + `lib/cart/anonymousToken` | `src/entities/cart/`                            |
| RTKQ endpoints для orders                           | `src/entities/order/`                           |
| `mapPickupPoints`, `pvzMarkerIcon`, `pvzProviders`  | `src/entities/pickup-point/`                    |
| RTKQ для recipients (если есть)                     | `src/entities/recipient/`                       |
| RTKQ для favorites + `favoriteAssets`               | `src/entities/favorite/`                        |
| RTKQ для promocodes                                 | `src/entities/promocode/`                       |
| RTKQ для referrals                                  | `src/entities/referral/`                        |
| RTKQ для reviews                                    | `src/entities/review/`                          |
| Profile / TG user types                             | `src/entities/user/`                            |
| `components/blocks/cart/useCart.js`                 | `src/entities/cart/model/useCart.js`            |
| `components/blocks/product/ProductCard.jsx`         | `src/entities/product/ui/ProductCard/`          |
| `components/blocks/product/ProductPrice.jsx`        | `src/entities/product/ui/ProductPrice/`         |
| `components/blocks/product/ProductImageCarousel`    | `src/entities/product/ui/ProductImageCarousel/` |
| `components/blocks/catalog/`                        | `src/entities/category/ui/`                     |
| `components/blocks/reviews/`                        | `src/entities/review/ui/`                       |

### features (Phase 6)

| Текущее                                                                             | Новое                                                      |
| ----------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| `lib/features/auth/` + bootstrap                                                    | `src/features/auth-telegram/`                              |
| `lib/features/telegram/` + НОВЫЙ `api.js` wrapper                                   | `src/features/telegram-api/`                               |
| `lib/checkout/` (model, FSM, hooks)                                                 | `src/features/checkout-flow/`                              |
| `lib/checkout/useLeafletPvzMap`, `usePvzData`, `usePvzUrlState`, `usePickupFromUrl` | `src/features/pickup-selection/`                           |
| `components/blocks/pickup/`                                                         | `src/features/pickup-selection/ui/`                        |
| `components/blocks/product/QuickAddSheet`, `ProductAddToCart`                       | `src/features/add-to-cart/ui/`                             |
| `components/blocks/checkout/sheets/` (recipient sheet)                              | `src/features/recipient-form/ui/`                          |
| `lib/checkout/hooks/useRecipientForm.js`                                            | `src/features/recipient-form/model/`                       |
| `lib/checkout/hooks/*` (остальные)                                                  | `src/features/checkout-flow/model/`                        |
| `components/blocks/checkout/sheets/` (остальные)                                    | `src/features/checkout-flow/ui/sheets/`                    |
| `lib/search/`                                                                       | `src/features/search/`                                     |
| `components/blocks/search/`                                                         | `src/features/search/ui/`                                  |
| `lib/hooks/useItemFavorites.js`                                                     | `src/features/favorites/model/`                            |
| `components/blocks/favorites/`                                                      | `src/features/favorites/ui/`                               |
| `app/promo/` + `components/blocks/promo/`                                           | `src/features/promocode/`                                  |
| `app/invite-friends/InviteLinkActions`, `PromoCouponCard`                           | `src/features/invite-friends/ui/`                          |
| `lib/home/` (useHomeFilters, useForYouFeed, ...)                                    | `src/features/home-feed/model/`                            |
| `components/blocks/home/`, `app/_home/`                                             | `src/features/home-feed/ui/`                               |
| `lib/product/` (если есть бизнес-хуки PDP)                                          | внутри `src/features/*/` или `src/entities/product/model/` |

### widgets (Phase 7) — плоская структура, без slice/index.js

| Текущее                                          | Новое                                                     |
| ------------------------------------------------ | --------------------------------------------------------- |
| `components/layout/Header.jsx`                   | `src/widgets/Header.jsx`                                  |
| `components/layout/Footer.jsx`                   | `src/widgets/Footer.jsx`                                  |
| `components/layout/Container.jsx`                | `src/widgets/Container.jsx`                               |
| `components/providers/TelegramAppShell.jsx`      | `src/widgets/TelegramAppShell.jsx`                        |
| `lib/features/auth/components/auth-gate.jsx`     | `src/widgets/AuthGate.jsx`                                |
| `components/blocks/telegram/TelegramNavButtons`  | `src/widgets/TelegramNavButtons.jsx`                      |
| `components/blocks/telegram/WebViewErrorAlert`   | `src/widgets/WebViewErrorAlert.jsx`                       |
| Композиция главной (из `app/page.jsx`)           | `src/widgets/HomePage/`                                   |
| Композиция каталога (`app/catalog/...`)          | `src/widgets/CatalogPage/`                                |
| Композиция PDP (`ProductPageClient`)             | `src/widgets/ProductPage/`                                |
| Композиция cart (`app/cart/page`)                | `src/widgets/CartPage/`                                   |
| Композиция checkout (`app/checkout/...`)         | `src/widgets/CheckoutPage/`                               |
| Композиция pickup (`app/checkout/pickup/page`)   | `src/widgets/PickupPage/`                                 |
| Композиция profile (`app/profile/...`)           | `src/widgets/ProfilePage/`                                |
| Композиция search/favorites/invite-friends/promo | `src/widgets/{Search,Favorites,InviteFriends,Promo}Page/` |

### app (Phase 8) — тонкие routes

| Текущее                                                                  | Новое                                                    |
| ------------------------------------------------------------------------ | -------------------------------------------------------- |
| `app/layout.tsx`                                                         | `src/app/layout.tsx` (тонкий)                            |
| `app/page.jsx` (1160 строк!)                                             | `src/app/page.jsx` (5-10 строк → HomePage)               |
| `app/checkout/pickup/page.jsx` (1569 строк!)                             | `src/app/checkout/pickup/page.jsx` (тонкий → PickupPage) |
| `app/product/[slug]/page.jsx` + `ProductPageClient.jsx`                  | `src/app/product/[slug]/page.jsx` (тонкий)               |
| `app/api/auth/`, `app/api/backend/`, `app/api/checkout/`, `app/api/geo/` | `src/app/api/*` (или реэкспорт из `src/shared/api/bff/`) |
| `app/TelegramViewportManager.tsx`                                        | `src/widgets/TelegramViewportManager.jsx`                |
| `app/globals.css`                                                        | `src/app/globals.css`                                    |
| `proxy.js` (edge middleware)                                             | `src/app/proxy.js` или корень (Next.js convention)       |
| `next.config.js`, `package.json`, `tsconfig.json`                        | остаются в корне                                         |

### god-components (Phase 9) — разбиение

| Файл                                             | Куда                                                                                                                                                                  |
| ------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `app/checkout/pickup/page.jsx` (1569)            | `widgets/PickupPage` + `features/pickup-selection/{model,lib,ui}/` (useLeafletMap, useViewportQuery, useGeolocation, useStepFSM, PickupMap, PickupList, PickupSearch) |
| `app/page.jsx` (1160)                            | `widgets/HomePage` + `features/home-feed/{model,ui}/` (useHomeSearchPipeline, FilterChipsBar, HomeFeed)                                                               |
| `lib/store/api.js` (1309)                        | разнести по `entities/*/api/` (Phase 5)                                                                                                                               |
| `app/checkout/page.jsx` (933)                    | `widgets/CheckoutPage` + `features/checkout-flow/`                                                                                                                    |
| `app/product/[slug]/ProductPageClient.jsx` (918) | `widgets/ProductPage` + секции `entities/product/ui/sections/`                                                                                                        |

## 13 фаз — обзор

| #   | Phase           | Описание                                                   |
| --- | --------------- | ---------------------------------------------------------- |
| 1   | Pre-work        | docs, ветка, ESLint draft, CLAUDE.md                       |
| 2   | Скаффолд `src/` | пустая структура, tsconfig/jsconfig paths                  |
| 3   | shared          | техника (format, hooks, ui, lib, events)                   |
| 4   | shared/api      | baseApi + codegen                                          |
| 5   | entities        | бизнес-сущности (разбор api.js)                            |
| 6   | features        | user actions + НОВЫЙ telegram-api wrapper                  |
| 7   | widgets         | composite blocks                                           |
| 8   | app тонкий      | переезд app/ → src/app/, pages = 5-10 строк                |
| 9   | god-components  | разбиение pickup/page, page.jsx, ProductPageClient         |
| 10  | ESLint enforce  | переключить на FSD config, fix violations                  |
| 11  | Тесты           | миграция + новое покрытие                                  |
| 12  | Verification    | npm validate, smoke Chrome + Telegram Desktop, docs update |
| 13  | PR + merge      | squash в main, координация                                 |

## Правила в процессе миграции

- **Старая структура работает до Phase 8** — пока полностью не переехали, импорты `@/components/*`, `@/lib/*` остаются валидными
- **Новые модули создаются сразу в `src/`** — не в `lib/` или `components/`
- **Внутренние импорты slice** — относительные (`./model/store`, не `@/entities/X/model/store`)
- **Cross-slice импорты** — только через `@/entities/X` (public API через index.js)
- **Codemod скрипты** для bulk-rename импортов — лежат в `scripts/migration/` (если будут)
