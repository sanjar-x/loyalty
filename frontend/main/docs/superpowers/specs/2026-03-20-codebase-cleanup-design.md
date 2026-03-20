# Codebase Cleanup & Preparation for Integration

**Date:** 2026-03-20
**Goal:** Clean the frontend codebase after API removal, prepare it for future integration with the FastAPI backend.
**Approach:** Layer-by-Layer (Infrastructure → Components → Pages)

---

## Context

- **Frontend:** Next.js 16, React 19, RTK Query, CSS Modules, Telegram Mini App
- **Backend:** FastAPI, PostgreSQL, JWT auth (HS256), RBAC, camelCase responses (via `CamelModel` presentation schemas), paginated `{items, total, offset, limit}`
- **Current state:** All API endpoints removed, UI foundation preserved (34 routes, 0 build errors). 10 bugs fixed post-cleanup. Mix of `.js`, `.jsx`, `.tsx` with `strict: false`.
- **Backend modules implemented:** Catalog (products, brands, categories, attributes, SKUs), Identity (auth, RBAC, sessions)
- **Backend modules NOT implemented:** Cart, Orders, Favorites, Referrals, Search
- **Note:** Frontend types must derive from backend **presentation schemas** (`CamelModel` subclasses), not from read models which use snake_case.

---

## Phase 1: Infrastructure

### 1.1 TypeScript Strict Mode

- `tsconfig.json` → `"strict": true`
- `allowJs: true` remains during migration (existing `.js`/`.jsx` are imported by `.ts`/`.tsx`)
- All new files: `.tsx` / `.ts`
- Convert `next.config.js` → `next.config.ts` (Next.js 16 supports natively)
- Convert `postcss.config.mjs` → `postcss.config.ts` or keep `.mjs`
- Convert `eslint.config.mjs` → keep `.mjs` (ESLint flat config standard)

### 1.2 API Types

Source of truth: backend FastAPI **presentation schemas** (CamelModel → camelCase serialization).

```
lib/types/
├── api.ts          # PaginatedResponse<T>, ApiError, SortOrder
├── auth.ts         # LoginRequest, LoginResponse, TokenPair, Identity, Session
├── catalog.ts      # Brand, Category, CategoryTree, Product, SKU, Money, Attribute, AttributeValue, AttributeGroup
├── user.ts         # UserProfile
├── telegram.ts     # TelegramWebApp, TelegramUser, TelegramInitData
└── index.ts        # Re-exports
```

Key type decisions:
- All types in **camelCase** (matching backend CamelModel presentation schemas)
- `PaginatedResponse<T> = { items: T[]; total: number; offset: number; limit: number }`
- `Money = { amount: number; currency: string }` — `amount` is in smallest currency unit (e.g., cents/kopecks), `currency` is ISO 4217 3-letter code (matches backend `MoneySchema`)
- i18n fields: `Record<string, string>` (locale key → value)
- Product `status`: `'DRAFT' | 'ACTIVE' | 'ARCHIVED' | 'DELETED'` (verify against backend domain enum during implementation)

### 1.3 Shared Utilities Consolidation

Current duplication:
- `getProductPhotoCandidates` — 4 files with different implementations (search, trash, product/[id], favorites)
- `getBrandLogoCandidates` — 3 files (favorites, favorites/brands, product/[id])
- `formatRubPrice` / `formatRub` — variations across pages
- `formatRuDateTime`, `formatUntilDate` — in invite-friends/page.jsx (extracted to shared)

```
lib/format/
├── price.ts            # formatRubPrice(), formatSplitPayment()
├── product-image.ts    # getProductPhotoCandidates(), buildImageUrl()
├── brand-image.ts      # getBrandLogoCandidates()
├── date.ts             # formatRuDateTime(), formatUntilDate() — extracted from app/invite-friends/page.jsx
├── cn.ts               # exists — keep as-is, add types
└── backendAssets.ts    # DELETE in Phase 3.5 — replaced by product-image.ts + brand-image.ts
```

**Important:** `backendAssets.ts` is deleted only AFTER all 5 importing files are updated to use the new utilities in Phases 2-3.

### 1.4 Redux Store Simplification

- Remove unused tagTypes: `Cart`, `Orders`, `Favorites`, `Shipments`, `Referrals`, `PVZ`, `SearchHistory`, `Payments`, `Types`
- Keep: `User`, `Products`, `Product`, `Categories`, `Brands`
- Type the store: `RootState`, `AppDispatch` in `store.ts`
- Type hooks: `useAppDispatch`, `useAppSelector` in `hooks.ts`
- `api.ts` stays with empty `endpoints` — skeleton for future integration

### 1.5 Auth Abstraction

```
lib/auth/
├── types.ts            # AuthState, AuthProvider ('telegram' | 'email')
├── session.ts          # getAccessToken(), isAuthenticated(), logout()
└── telegram.ts         # moved from lib/telegram/ — parseTelegramInitData(), validateInitData()
```

- `TelegramAuthBootstrap.tsx` — stays at `components/blocks/telegram/` (noop, typed interface). Import path in `layout.tsx` unchanged.
- `browserDebugAuth.ts` → `.ts` with types, keep for dev
- BFF proxy `app/api/backend/[...path]/route.ts` — convert to `.ts`, no logic changes
- `app/api/auth/telegram/_handoffStore.js` → `.ts` — server-only utility used by exchange/consume routes

### 1.6 Error Handling Foundation

- `app/error.tsx` — global React Error Boundary
- `app/not-found.tsx` — custom 404 page in app style
- `lib/errors.ts` — `AppError`, `ApiError`, `NetworkError` classes

### 1.7 Telegram Window Globals

Create `lib/types/telegram-globals.d.ts`:
```ts
interface Window {
  __LM_TG_INIT_DATA__?: string;
  __LM_TG_INIT_DATA_UNSAFE__?: { user?: TelegramUser };
  __LM_BROWSER_DEBUG_AUTH__?: boolean;
  __LM_BROWSER_DEBUG_USER__?: DebugUser | null;
  Telegram?: { WebApp?: TelegramWebApp };
}
```

---

## Phase 2: Components

### 2.1 Shared UI Type: ProductCardData

Single contract replacing 4 different mapper functions:

```ts
type ProductCardData = {
  id: number | string;
  name: string;
  price: string;
  image: string;
  imageFallbacks?: string[];
  isFavorite?: boolean;
  brand?: string;
  deliveryText?: string;
};
```

### 2.2 UI Primitives → `.tsx`

| Component | Key Props |
|-----------|-----------|
| `Button.tsx` | `variant, size, disabled, loading, onClick, children` |
| `BottomSheet.tsx` | `open, onClose, title?, header?, footer?, children` |
| `InputFocusFix.tsx` | Already `.tsx` — add types |

### 2.3 Layout → `.tsx`

`Header.tsx` (`title: string`), `Footer.tsx`, `Layout.tsx` (`className?, children`)

### 2.4 Feature Blocks → `.tsx`

All components in `components/blocks/` converted to TypeScript with typed props interfaces.

**Product:** ProductCard, ProductSection, ProductImageGallery, ProductInfo, ProductPrice, ProductSizes, ProductAddToCart, ProductReviews, ProductShippingOptions, ProductBrandsCarousel, SplitPaymentSheet

**Catalog:** CatalogTabs, BrandsList, CategoryTabs

**Favorites:** BrandsSection, EmptyState, FavoriteBrandsSection (+ `brands = []` default), AllBrandsList, BrandsSearch, BrandCard

**Search:** SearchBar, FiltersSheet, PriceSheet, SelectSheet

**Profile:** ProfileHeader, ProfileMenuItem, ProfileMenuSection

**Telegram:** TelegramInit, TelegramAuthBootstrap, TelegramNavButtons, WebViewErrorAlert

**Home:** CategoryTabs, FriendsSection, HomeDeliveryStatusCard, InfoCard

**Reviews:** ReviewCard

**Promo:** PromoInfoModal, promo-points

**Cart:** useCart hook (already stub — add types)

### 2.5 CSS Cleanup

- Remove Google Fonts `@import` from `globals.css` (keep only local `@font-face`)
- No other CSS changes — CSS Modules structure stays

### 2.6 Dependency Audit

**lucide-react:** Used across ~10 import sites with 7+ icons (`Search`, `Trash2`, `Check`, `Minus`, `Star`, `Info`, `X`). Stays — removing would require replacing all with inline SVGs for marginal benefit.

**leaflet + leaflet.markercluster:** Used only in `app/checkout/pickup/page.jsx` for PVZ map selection (leaflet CSS selectors also in `globals.css`). These pages depend on unimplemented backend modules (Orders/PVZ). Keep for now — the pages themselves stay as stubs; removing leaflet would break them. Review when those backend modules are implemented.
---

## Phase 3: Pages

### 3.1 All Pages → `.tsx`

All 34 routes converted. Each page:
- Removes local mapper functions (use shared `lib/format/`)
- Removes dead `backendAssets` imports (update to `product-image.ts` / `brand-image.ts`)
- Uses typed components from Phase 2
- Stub data remains but typed: `const products: ProductCardData[] = []`

### 3.2 Mock Data Removal

- Delete `app/profile/orders/mockOrders.js`
- Delete `app/profile/purchased/mockPurchasedProducts.js`
- Client components → `.tsx` with empty state UI:
  - `OrdersClient.tsx`
  - `OrderDetailsClient.tsx`
  - `ReviewClient.tsx`
  - `CreateReturnClient.tsx`
  - `ReturnRequestClient.tsx`

### 3.3 BFF API Routes → `.ts`

- `app/api/backend/[...path]/route.ts`
- `app/api/session/telegram/init/route.ts`
- `app/api/auth/telegram/exchange/route.ts`
- `app/api/auth/telegram/consume/route.ts`
- `app/api/auth/telegram/_handoffStore.ts`
- `app/api/dadata/suggest/address/route.ts`
- `app/api/dadata/clean/address/route.ts`
- `app/api/session/logout/route.ts`

### 3.4 Additional Files → `.tsx`/`.ts`

Files not in page routes or components but still need conversion:
- `app/invite-friends/InviteLinkActions.tsx`
- `app/invite-friends/PromoCouponCard.tsx`
- `app/profile/_shared/ComingSoon.tsx`
- `lib/hooks/useItemFavorites.ts`

### 3.5 Loading States

Add `loading.tsx` for all main routes missing them (currently only catalog, catalog/[category], invite-friends have them). Each renders a skeleton matching the page layout.

### 3.6 Final Cleanup

- Delete `lib/format/backendAssets.ts` (all imports already updated in earlier steps)
- Convert `next.config.js` → `next.config.ts`, add backend S3 domain to `remotePatterns`
- Create `.env.example` with all required variables documented
- Confirm no `.js`/`.jsx` files remain in `app/`, `components/`, `lib/`

---

## Files Created / Modified / Deleted Summary

### Created (new files)
- `lib/types/api.ts`, `auth.ts`, `catalog.ts`, `user.ts`, `telegram.ts`, `index.ts`
- `lib/types/telegram-globals.d.ts`
- `lib/auth/types.ts`, `session.ts`, `telegram.ts`
- `lib/format/price.ts`, `product-image.ts`, `brand-image.ts`, `date.ts`
- `lib/errors.ts`
- `app/error.tsx`, `app/not-found.tsx`
- `loading.tsx` files for routes missing them
- `.env.example`

### Deleted
- `lib/format/backendAssets.ts` (after all imports updated)
- `app/profile/orders/mockOrders.js`
- `app/profile/purchased/mockPurchasedProducts.js`

### Converted `.js`/`.jsx` → `.tsx`/`.ts`
- All 34 page files
- All ~48 component files (including SplitPaymentSheet, InviteLinkActions, PromoCouponCard, ComingSoon)
- All `lib/` utility files (including useItemFavorites, browserDebugAuth)
- All `app/api/` route files (including _handoffStore)
- `lib/store/api.ts`, `store.ts`, `hooks.ts`
- `components/providers/StoreProvider.tsx` (already `.tsx`)
- `next.config.js` → `next.config.ts`

---

## Success Criteria

1. `next build` passes with 0 errors
2. `tsc --noEmit` passes with 0 errors
3. No `.js` or `.jsx` files remain in `app/`, `components/`, or `lib/`
4. No duplicate utility functions across files
5. No dead imports or dead code
6. All components have typed props interfaces
7. Error Boundary and 404 page render correctly
8. `strict: true` in tsconfig
9. `next.config.ts` used instead of `.js`
