# Codebase Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the entire frontend codebase to strict TypeScript, consolidate duplicated utilities, simplify the Redux store, add error handling, and prepare for future backend integration.

**Architecture:** Layer-by-layer: infrastructure first (types, utilities, store), then components (typed props), then pages (conversion + dead code removal). Each task produces a buildable state.

**Tech Stack:** Next.js 16, React 19, TypeScript 5 (strict), RTK Query, CSS Modules

**Spec:** `docs/superpowers/specs/2026-03-20-codebase-cleanup-design.md`

**Total files to convert:** 108 (55 in `app/`, 45 in `components/`, 8 in `lib/`) + 3 existing `.tsx` files to audit under strict mode

---

## Phase 1: Infrastructure

### Task 1: Enable TypeScript Strict Mode

**Files:**
- Modify: `tsconfig.json`

- [ ] **Step 1: Update tsconfig.json**

Set `"strict": true`. Add `"**/*.js"` and `"**/*.jsx"` to `include` so existing files are checked during migration. Ensure `allowJs: true` and `skipLibCheck: true` remain.

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": { "@/*": ["./*"] },
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "incremental": true,
    "module": "esnext",
    "esModuleInterop": true,
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "react-jsx",
    "plugins": [{ "name": "next" }]
  },
  "include": [
    "next-env.d.ts",
    ".next/types/**/*.ts",
    ".next/dev/types/**/*.ts",
    "**/*.mts",
    "**/*.ts",
    "**/*.tsx",
    "**/*.js",
    "**/*.jsx"
  ],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 2: Audit existing `.tsx` files under strict mode**

Three files were written under `strict: false` and may have type errors now:
- `app/layout.tsx`
- `app/TelegramViewportManager.tsx`
- `components/ios/InputFocusFix.tsx`

Run `npx tsc --noEmit 2>&1 | grep -E "(layout|TelegramViewport|InputFocusFix)"` and fix any errors.

- [ ] **Step 3: Delete `jsconfig.json` if it exists** (redundant with tsconfig.json under strict mode)

- [ ] **Step 4: Verify build still passes**

Run: `npx next build 2>&1 | head -5`
Expected: `✓ Compiled successfully` (allowJs + skipLibCheck means existing JS files won't block the build)

- [ ] **Step 5: Commit**

```bash
git add tsconfig.json
git commit -m "chore: enable TypeScript strict mode"
```

---

### Task 2: Create API Type Definitions

**Files:**
- Create: `lib/types/api.ts`
- Create: `lib/types/auth.ts`
- Create: `lib/types/catalog.ts`
- Create: `lib/types/user.ts`
- Create: `lib/types/telegram.ts`
- Create: `lib/types/index.ts`

Types derived from backend presentation schemas (CamelModel → camelCase). See backend at `~/Desktop/loyality/backend/src/modules/*/presentation/schemas.py`.

- [ ] **Step 1: Create `lib/types/api.ts`**

```ts
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
}

export interface ApiError {
  detail: string;
  status: number;
}

export type SortOrder = "asc" | "desc";
```

- [ ] **Step 2: Create `lib/types/auth.ts`**

```ts
export type AuthProvider = "telegram" | "email";

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenPair {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
}

export interface Identity {
  identityId: string;
  email: string;
  authType: string;
  isActive: boolean;
  createdAt: string;
}

export interface Session {
  id: string;
  ipAddress: string;
  userAgent: string;
  createdAt: string;
  isCurrent: boolean;
}
```

- [ ] **Step 3: Create `lib/types/catalog.ts`**

```ts
export interface Money {
  /** Amount in smallest currency unit (e.g., kopecks for RUB) */
  amount: number;
  /** ISO 4217 3-letter currency code */
  currency: string;
}

export type ProductStatus = "DRAFT" | "ACTIVE" | "ARCHIVED" | "DELETED";

export interface Brand {
  id: string;
  name: string;
  slug: string;
  logoUrl: string | null;
  logoStatus: string;
}

export interface Category {
  id: string;
  name: string;
  slug: string;
  fullSlug: string;
  level: number;
  sortOrder: number;
  parentId: string | null;
}

export interface CategoryTreeNode extends Category {
  children: CategoryTreeNode[];
}

export interface Product {
  id: string;
  slug: string;
  titleI18n: Record<string, string>;
  descriptionI18n: Record<string, string>;
  status: ProductStatus;
  brandId: string;
  primaryCategoryId: string;
  tags: string[];
  version: number;
  createdAt: string;
  updatedAt: string;
}

export interface SKU {
  id: string;
  productId: string;
  skuCode: string;
  price: Money;
  compareAtPrice: Money | null;
  isActive: boolean;
  version: number;
  variantAttributes: VariantAttribute[];
}

export interface VariantAttribute {
  attributeId: string;
  attributeValueId: string;
}

export interface Attribute {
  id: string;
  code: string;
  slug: string;
  nameI18n: Record<string, string>;
  dataType: string;
  uiType: string;
  isDictionary: boolean;
  isFilterable: boolean;
  isSearchable: boolean;
  isComparable: boolean;
}

export interface AttributeValue {
  id: string;
  attributeId: string;
  code: string;
  slug: string;
  valueI18n: Record<string, string>;
  sortOrder: number;
}

export interface AttributeGroup {
  id: string;
  code: string;
  nameI18n: Record<string, string>;
  sortOrder: number;
}
```

- [ ] **Step 4: Create `lib/types/user.ts`**

```ts
export interface UserProfile {
  id: string;
  profileEmail: string | null;
  firstName: string | null;
  lastName: string | null;
  phone: string | null;
}
```

- [ ] **Step 5: Create `lib/types/telegram.ts`**

```ts
export interface TelegramUser {
  id: number;
  first_name?: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  photo_url?: string;
  is_premium?: boolean;
}

export interface TelegramInitDataUnsafe {
  user?: TelegramUser;
  auth_date?: number;
  hash?: string;
  start_param?: string;
}

export interface TelegramWebApp {
  initData: string;
  initDataUnsafe: TelegramInitDataUnsafe;
  version: string;
  platform: string;
  ready: () => void;
  expand: () => void;
  close: () => void;
  disableVerticalSwipes?: () => void;
  requestFullscreen?: () => void;
  requestFullScreen?: () => void;
  setBackgroundColor: (color: string) => void;
  setHeaderColor: (color: string) => void;
  BackButton: {
    show: () => void;
    hide: () => void;
    onClick: (cb: () => void) => void;
    offClick: (cb: () => void) => void;
    isVisible: boolean;
  };
  MainButton: {
    show: () => void;
    hide: () => void;
    setText: (text: string) => void;
    onClick: (cb: () => void) => void;
    offClick: (cb: () => void) => void;
    isVisible: boolean;
  };
}

export interface DebugUser {
  tg_id: string;
  username: string;
  id: number;
  registration_date?: string;
  points?: number;
  level?: string;
}
```

- [ ] **Step 6: Create `lib/types/index.ts`**

```ts
export * from "./api";
export * from "./auth";
export * from "./catalog";
export * from "./user";
export * from "./telegram";
```

- [ ] **Step 7: Verify build**

Run: `npx next build 2>&1 | head -5`
Expected: `✓ Compiled successfully`

- [ ] **Step 8: Commit**

```bash
git add lib/types/
git commit -m "feat: add API type definitions from backend schemas"
```

---

### Task 3: Create Telegram Window Globals Declaration

**Files:**
- Create: `lib/types/telegram-globals.d.ts`

- [ ] **Step 1: Create the declaration file**

```ts
import type { TelegramUser, TelegramWebApp, DebugUser } from "./telegram";

declare global {
  interface Window {
    __LM_TG_INIT_DATA__?: string;
    __LM_TG_INIT_DATA_UNSAFE__?: { user?: TelegramUser };
    __LM_BROWSER_DEBUG_AUTH__?: boolean;
    __LM_BROWSER_DEBUG_USER__?: DebugUser | null;
    Telegram?: { WebApp?: TelegramWebApp };
  }
}

export {};
```

- [ ] **Step 2: Commit**

```bash
git add lib/types/telegram-globals.d.ts
git commit -m "feat: add Window global type declarations for Telegram SDK"
```

---

### Task 4: Create Shared Format Utilities

**Files:**
- Create: `lib/format/price.ts`
- Create: `lib/format/product-image.ts`
- Create: `lib/format/brand-image.ts`
- Create: `lib/format/date.ts`
- Modify: `lib/format/cn.js` → rename to `lib/format/cn.ts`

These replace duplicated functions across 4+ page files and will replace `lib/format/backendAssets.js`.

- [ ] **Step 1: Create `lib/format/price.ts`**

```ts
export function formatRubPrice(value: number | string | null | undefined): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "";
  const rounded = Math.trunc(n);
  const formatted = rounded.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `${formatted} ₽`;
}

export function formatSplitPayment(
  totalPrice: number,
  installments: number = 4,
): string {
  if (!Number.isFinite(totalPrice) || totalPrice <= 0) return "0";
  return String(Math.ceil(totalPrice / installments));
}
```

- [ ] **Step 2: Create `lib/format/product-image.ts`**

Consolidates the 4 different `getProductPhotoCandidates` implementations. Uses the most complete variant (from `trash/page.jsx` which handles `image`, `image_url`, `photo`, `photo_url`, and `photos[0].filename`).

```ts
interface ProductLike {
  image?: string;
  image_url?: string;
  photo?: string;
  photo_url?: string;
  photos?: Array<string | { filename?: string; file?: string; path?: string; url?: string }>;
}

function isHttpUrl(value: string): boolean {
  return /^https?:\/\//i.test(value.trim());
}

function safeEncodePathParam(value: string): string {
  const raw = value.trim();
  if (!raw) return "";
  const cleaned = raw.replace(/^\/+/, "");
  if (/%[0-9A-Fa-f]{2}/.test(cleaned)) return cleaned;
  return encodeURIComponent(cleaned);
}

export function buildProductPhotoUrl(filename: string): string {
  const raw = filename.trim();
  if (!raw) return "";
  if (isHttpUrl(raw)) return raw;
  const encoded = safeEncodePathParam(raw);
  return encoded ? `/api/backend/api/v1/products/get_photo/${encoded}` : "";
}

export function buildBackendAssetUrl(path: string, prefixSegments: string[] = []): string {
  const raw = path.trim();
  if (!raw) return "";
  if (isHttpUrl(raw)) return raw;
  const cleaned = raw.replace(/^\/+/, "");
  const encoded = cleaned.split("/").map((p) => encodeURIComponent(p)).join("/");
  const prefix = prefixSegments.length
    ? `${prefixSegments.map((s) => encodeURIComponent(s)).join("/")}/`
    : "";
  return `/api/backend/${prefix}${encoded}`;
}

export function getProductPhotoCandidates(product: ProductLike | null | undefined): string[] {
  if (!product) return [];
  const candidates: string[] = [];

  const rawDirect =
    (typeof product.image === "string" ? product.image : "") ||
    (typeof product.image_url === "string" ? product.image_url : "") ||
    (typeof product.photo === "string" ? product.photo : "") ||
    (typeof product.photo_url === "string" ? product.photo_url : "");
  if (rawDirect?.trim()) candidates.push(rawDirect.trim());

  const photos = Array.isArray(product.photos) ? product.photos : [];
  const first = photos[0];
  const filename =
    typeof first === "string"
      ? first
      : first && typeof first === "object"
        ? (first.filename ?? first.file ?? first.path ?? first.url)
        : null;

  const raw = typeof filename === "string" ? filename.trim() : "";
  if (raw) {
    candidates.push(
      buildProductPhotoUrl(raw),
      buildBackendAssetUrl(raw, ["media"]),
      buildBackendAssetUrl(raw, ["static"]),
      buildBackendAssetUrl(raw, ["uploads"]),
      buildBackendAssetUrl(raw),
    );
  }

  return candidates.filter(Boolean);
}
```

- [ ] **Step 3: Create `lib/format/brand-image.ts`**

```ts
import { buildBackendAssetUrl } from "./product-image";

function uniqStrings(arr: string[]): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const v of arr) {
    if (!v || seen.has(v)) continue;
    seen.add(v);
    out.push(v);
  }
  return out;
}

export function buildBrandLogoUrl(filename: string | null | undefined): string {
  const raw = typeof filename === "string" ? filename.trim() : "";
  if (!raw) return "";
  if (/^https?:\/\//i.test(raw)) return raw;
  const cleaned = raw.replace(/^\/+/, "");
  if (/%[0-9A-Fa-f]{2}/.test(cleaned)) return `/api/backend/api/v1/brands/logo/${cleaned}`;
  return `/api/backend/api/v1/brands/logo/${encodeURIComponent(cleaned)}`;
}

interface BrandLike {
  id?: number | string | null;
  logo?: string | null;
  logo_path?: string | null;
  logoUrl?: string | null;
  image?: string | null;
  image_url?: string | null;
}

export function getBrandLogoCandidates(brand: BrandLike | null | undefined): string[] {
  if (!brand) return [];
  const id = brand.id;
  const logo = brand.logo ?? brand.logo_path ?? brand.logoUrl ?? brand.image ?? brand.image_url;

  const byPath = typeof logo === "string" ? buildBrandLogoUrl(logo) : "";
  const byId =
    id != null
      ? `/api/backend/api/v1/brands/${encodeURIComponent(String(id))}/logo`
      : "";

  return uniqStrings([
    byPath,
    byId,
    typeof logo === "string" ? buildBackendAssetUrl(logo) : "",
    typeof logo === "string" ? buildBackendAssetUrl(logo, ["media"]) : "",
    typeof logo === "string" ? buildBackendAssetUrl(logo, ["static"]) : "",
    typeof logo === "string" ? buildBackendAssetUrl(logo, ["uploads"]) : "",
  ]);
}
```

- [ ] **Step 4: Create `lib/format/date.ts`**

Extracted from `app/invite-friends/page.jsx`.

```ts
export function formatRuDateTime(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatUntilDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const yyyy = String(d.getFullYear());
  return `До ${dd}.${mm}.${yyyy}`;
}
```

- [ ] **Step 5: Convert `lib/format/cn.js` → `lib/format/cn.ts`**

Rename file and add type annotation. Read the current content first, then rewrite with types.

- [ ] **Step 6: Verify build**

Run: `npx next build 2>&1 | head -5`
Expected: `✓ Compiled successfully`

- [ ] **Step 7: Commit**

```bash
git add lib/format/price.ts lib/format/product-image.ts lib/format/brand-image.ts lib/format/date.ts lib/format/cn.ts
git rm lib/format/cn.js
git commit -m "feat: consolidate shared format utilities into typed modules"
```

---

### Task 5: Simplify Redux Store + Type It

**Files:**
- Rename + rewrite: `lib/store/api.js` → `lib/store/api.ts`
- Rename + rewrite: `lib/store/store.js` → `lib/store/store.ts`
- Rename + rewrite: `lib/store/hooks.js` → `lib/store/hooks.ts`

- [ ] **Step 1: Convert `lib/store/api.js` → `lib/store/api.ts`**

Remove dead tagTypes (`Cart`, `Orders`, `Favorites`, `Shipments`, `Referrals`, `PVZ`, `SearchHistory`, `Payments`, `Types`). Keep only tags for implemented backend modules.

```ts
import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import type { BaseQueryFn, FetchArgs, FetchBaseQueryError } from "@reduxjs/toolkit/query";

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "/api/backend";

const backendBaseQuery = fetchBaseQuery({
  baseUrl,
  credentials: "include",
});

const appBaseQuery = fetchBaseQuery({
  baseUrl: "",
  credentials: "include",
});

const baseQuery: BaseQueryFn<string | FetchArgs, unknown, FetchBaseQueryError> = async (
  args,
  api,
  extraOptions,
) => {
  const url = typeof args === "string" ? args : args?.url;

  if (typeof url === "string" && url.startsWith("/api/session/")) {
    return appBaseQuery(args, api, extraOptions);
  }

  return backendBaseQuery(args, api, extraOptions);
};

export const api = createApi({
  reducerPath: "api",
  baseQuery,
  tagTypes: ["User", "Products", "Product", "Categories", "Brands"],
  endpoints: () => ({}),
});
```

- [ ] **Step 2: Convert `lib/store/store.js` → `lib/store/store.ts`**

```ts
import { configureStore } from "@reduxjs/toolkit";
import { api } from "./api";

export const makeStore = () =>
  configureStore({
    reducer: {
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
  });

export type AppStore = ReturnType<typeof makeStore>;
export type RootState = ReturnType<AppStore["getState"]>;
export type AppDispatch = AppStore["dispatch"];
```

- [ ] **Step 3: Convert `lib/store/hooks.js` → `lib/store/hooks.ts`**

```ts
import { useDispatch, useSelector } from "react-redux";
import type { AppDispatch, RootState } from "./store";

export const useAppDispatch = useDispatch.withTypes<AppDispatch>();
export const useAppSelector = useSelector.withTypes<RootState>();
```

- [ ] **Step 4: Delete old `.js` files, verify build**

```bash
git rm lib/store/api.js lib/store/store.js lib/store/hooks.js
```

Run: `npx next build 2>&1 | head -5`
Expected: `✓ Compiled successfully`

- [ ] **Step 5: Commit**

```bash
git add lib/store/
git commit -m "refactor: simplify Redux store, convert to TypeScript, remove dead tagTypes"
```

---

### Task 6: Create Error Handling Foundation

**Files:**
- Create: `lib/errors.ts`
- Create: `app/error.tsx`
- Create: `app/not-found.tsx`

- [ ] **Step 1: Create `lib/errors.ts`**

```ts
export class AppError extends Error {
  constructor(message: string, public code?: string) {
    super(message);
    this.name = "AppError";
  }
}

export class ApiError extends AppError {
  constructor(
    message: string,
    public status: number,
    public detail?: string,
  ) {
    super(message, `API_${status}`);
    this.name = "ApiError";
  }
}

export class NetworkError extends AppError {
  constructor(message: string = "Network error") {
    super(message, "NETWORK_ERROR");
    this.name = "NetworkError";
  }
}
```

- [ ] **Step 2: Create `app/error.tsx`**

```tsx
"use client";

import { useEffect } from "react";
import styles from "./page.module.css";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Unhandled error:", error);
  }, [error]);

  return (
    <div className="lm-app-bg" style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ textAlign: "center", padding: "2rem" }}>
        <h2 style={{ fontFamily: "Inter, sans-serif", fontSize: "1.25rem", fontWeight: 600, marginBottom: "0.5rem" }}>
          Что-то пошло не так
        </h2>
        <p style={{ fontFamily: "Inter, sans-serif", fontSize: "0.875rem", color: "#666", marginBottom: "1.5rem" }}>
          Попробуйте обновить страницу
        </p>
        <button
          onClick={reset}
          type="button"
          style={{
            fontFamily: "Inter, sans-serif",
            fontSize: "0.875rem",
            fontWeight: 500,
            padding: "0.75rem 2rem",
            borderRadius: "9999px",
            border: "none",
            background: "#111",
            color: "#fff",
            cursor: "pointer",
          }}
        >
          Попробовать снова
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create `app/not-found.tsx`**

```tsx
import Link from "next/link";

export default function NotFound() {
  return (
    <div className="lm-app-bg" style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ textAlign: "center", padding: "2rem" }}>
        <h2 style={{ fontFamily: "Inter, sans-serif", fontSize: "1.25rem", fontWeight: 600, marginBottom: "0.5rem" }}>
          Страница не найдена
        </h2>
        <p style={{ fontFamily: "Inter, sans-serif", fontSize: "0.875rem", color: "#666", marginBottom: "1.5rem" }}>
          Такой страницы не существует
        </p>
        <Link
          href="/"
          style={{
            fontFamily: "Inter, sans-serif",
            fontSize: "0.875rem",
            fontWeight: 500,
            padding: "0.75rem 2rem",
            borderRadius: "9999px",
            border: "none",
            background: "#111",
            color: "#fff",
            textDecoration: "none",
            display: "inline-block",
          }}
        >
          На главную
        </Link>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Verify build**

Run: `npx next build 2>&1 | head -5`

- [ ] **Step 5: Commit**

```bash
git add lib/errors.ts app/error.tsx app/not-found.tsx
git commit -m "feat: add error boundary, 404 page, and error types"
```

---

### Task 7: Create Auth Abstraction

**Files:**
- Create: `lib/auth/types.ts`
- Create: `lib/auth/session.ts`
- Rename: `lib/telegram/authServer.js` → `lib/auth/telegram.ts`
- Rename: `lib/telegram/browserDebugAuth.js` → `lib/auth/browserDebugAuth.ts`

- [ ] **Step 1: Create `lib/auth/types.ts`**

```ts
import type { AuthProvider } from "@/lib/types/auth";

export interface AuthState {
  provider: AuthProvider | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}
```

- [ ] **Step 2: Create `lib/auth/session.ts`**

```ts
export function getAccessTokenCookieName(): string {
  return "lm_access_token";
}

export async function isAuthenticated(): Promise<boolean> {
  // In Mini App context, auth state is managed server-side via httpOnly cookie.
  // Client cannot directly read the cookie; rely on API responses.
  return false;
}

export async function logout(): Promise<void> {
  await fetch("/api/session/logout", { method: "POST", credentials: "include" });
}
```

- [ ] **Step 3: Move and convert `lib/telegram/authServer.js` → `lib/auth/telegram.ts`**

Read the current file, add TypeScript types to all functions. Keep `"server-only"` import. Update all internal imports. After moving, update any files that import from `@/lib/telegram/authServer` to import from `@/lib/auth/telegram`.

- [ ] **Step 4: Move and convert `lib/telegram/browserDebugAuth.js` → `lib/auth/browserDebugAuth.ts`**

Read the current file, add TypeScript types. After moving, update all files that import from `@/lib/telegram/browserDebugAuth` to import from `@/lib/auth/browserDebugAuth`.

- [ ] **Step 5: Update all import paths**

Files that import from `@/lib/telegram/authServer`:
- `app/api/session/telegram/init/route.js`

Files that import from `@/lib/telegram/browserDebugAuth`:
- `app/api/session/telegram/init/route.js`
- `components/blocks/telegram/TelegramInit.jsx`
- `components/blocks/telegram/TelegramAuthBootstrap.jsx`

- [ ] **Step 6: Delete empty `lib/telegram/` directory if now empty**

- [ ] **Step 7: Verify build, commit**

```bash
git add lib/auth/ && git rm lib/telegram/authServer.js lib/telegram/browserDebugAuth.js
git commit -m "refactor: move auth utilities to lib/auth/, convert to TypeScript"
```

---

### Task 8: Convert StoreProvider and useItemFavorites

**Files:**
- Rename + type: `components/providers/StoreProvider.jsx` → `StoreProvider.tsx`
- Rename + type: `lib/hooks/useItemFavorites.js` → `useItemFavorites.ts`

- [ ] **Step 1: Convert `StoreProvider.jsx` → `StoreProvider.tsx`**

```tsx
"use client";

import { Provider } from "react-redux";
import { useState, type ReactNode } from "react";
import { makeStore, type AppStore } from "@/lib/store/store";

export default function StoreProvider({ children }: { children: ReactNode }) {
  const [store] = useState<AppStore>(() => makeStore());
  return <Provider store={store}>{children}</Provider>;
}
```

- [ ] **Step 2: Convert `useItemFavorites.js` → `useItemFavorites.ts`**

```ts
import { useCallback } from "react";

const EMPTY_SET = new Set<number | string>();
const EMPTY_MAP = new Map<number | string, number[]>();
const EMPTY_ARRAY: never[] = [];

export function useItemFavorites(_itemType: "product" | "brand") {
  const toggleFavorite = useCallback((_id: number | string) => {
    // TODO: connect to API
  }, []);

  return {
    favorites: EMPTY_ARRAY,
    favoriteItemIds: EMPTY_SET,
    itemIdToFavoriteIds: EMPTY_MAP,
    toggleFavorite,
    isLoading: false,
    isFetching: false,
    isError: false,
    isMutating: false,
    refetch: () => {},
  } as const;
}
```

- [ ] **Step 3: Delete old files, verify build, commit**

```bash
git rm components/providers/StoreProvider.jsx lib/hooks/useItemFavorites.js
git add components/providers/StoreProvider.tsx lib/hooks/useItemFavorites.ts
git commit -m "refactor: convert StoreProvider and useItemFavorites to TypeScript"
```

---

## Phase 2: Components

### Task 9: Convert UI Primitives (Button, BottomSheet)

**Files:**
- Rename + type: `components/ui/Button.jsx` → `Button.tsx`
- Rename + type: `components/ui/BottomSheet.jsx` → `BottomSheet.tsx`

- [ ] **Step 1:** Read each file, add typed props interface, rename to `.tsx`. Keep all existing logic and CSS Module imports.

- [ ] **Step 2:** Verify build, commit.

```bash
git rm components/ui/Button.jsx components/ui/BottomSheet.jsx
git add components/ui/Button.tsx components/ui/BottomSheet.tsx
git commit -m "refactor: convert UI primitives to TypeScript"
```

---

### Task 10: Convert Layout Components

**Files:**
- Rename + type: `components/layout/Header.jsx` → `Header.tsx`
- Rename + type: `components/layout/Footer.jsx` → `Footer.tsx`
- Rename + type: `components/layout/Layout.jsx` → `Layout.tsx`

- [ ] **Step 1:** Read each file, add typed props interface, rename to `.tsx`.

- [ ] **Step 2:** Verify build, commit.

```bash
git rm components/layout/Header.jsx components/layout/Footer.jsx components/layout/Layout.jsx
git add components/layout/Header.tsx components/layout/Footer.tsx components/layout/Layout.tsx
git commit -m "refactor: convert layout components to TypeScript"
```

---

### Task 11: Convert Telegram + iOS Components

**Files:**
- Rename + type: `components/blocks/telegram/TelegramInit.jsx` → `.tsx`
- Rename + type: `components/blocks/telegram/TelegramAuthBootstrap.jsx` → `.tsx`
- Rename + type: `components/blocks/telegram/TelegramNavButtons.jsx` → `.tsx`
- Rename + type: `components/blocks/telegram/WebViewErrorAlert.jsx` → `.tsx`
- Audit + add types: `components/ios/InputFocusFix.tsx` (already `.tsx`, needs strict-mode type audit)

- [ ] **Step 1:** Read each `.jsx` file, add types using `TelegramWebApp` from `lib/types/telegram.ts`. Update imports from `@/lib/telegram/browserDebugAuth` → `@/lib/auth/browserDebugAuth`.

- [ ] **Step 2:** Audit `InputFocusFix.tsx` — add proper types for any untyped params/state under strict mode.

- [ ] **Step 3:** Verify build, commit.

```bash
git commit -m "refactor: convert Telegram components to TypeScript"
```

---

### Task 12: Convert Product Components

**Files:** All 11 files in `components/blocks/product/` → `.tsx`

- [ ] **Step 1:** Read each component, add typed props interfaces. Key type: `ProductCardData` from spec (define in `lib/types/ui.ts` or inline).

- [ ] **Step 2:** Create `lib/types/ui.ts` with shared component types:

```ts
export interface ProductCardData {
  id: number | string;
  name: string;
  price: string;
  image: string;
  imageFallbacks?: string[];
  isFavorite?: boolean;
  brand?: string;
  deliveryText?: string;
}
```

- [ ] **Step 3:** Convert all 11 files. Verify build after each batch.

- [ ] **Step 4:** Commit.

```bash
git commit -m "refactor: convert product components to TypeScript"
```

---

### Task 13: Convert Remaining Feature Components

**Files:** All components in `blocks/catalog/`, `blocks/favorites/`, `blocks/search/`, `blocks/profile/`, `blocks/home/`, `blocks/reviews/`, `blocks/promo/`, `blocks/cart/` → `.tsx`

Total: ~27 files. Convert in batches by domain:

- [ ] **Step 1:** Catalog (CatalogTabs, BrandsList) → `.tsx`
- [ ] **Step 2:** Favorites — two separate `BrandCard` files exist:
  - `components/blocks/favorites/BrandCard.jsx` → `.tsx`
  - `components/blocks/favorites/brands/BrandCard.jsx` → `.tsx`
  - Plus: `BrandsSection`, `EmptyState`, `AllBrandsList`, `BrandsSearch`, `FavoriteBrandsSection` → `.tsx`
- [ ] **Step 3:** Search (SearchBar, FiltersSheet, PriceSheet, SelectSheet) → `.tsx`
- [ ] **Step 4:** Profile (ProfileHeader, ProfileMenuItem, ProfileMenuSection) → `.tsx`
- [ ] **Step 5:** Home (CategoryTabs, FriendsSection, HomeDeliveryStatusCard, InfoCard) → `.tsx`
- [ ] **Step 6:** Reviews (ReviewCard), Promo (PromoInfoModal, promo-points), Cart (useCart.js → useCart.ts) → `.tsx`/`.ts`
- [ ] **Step 7:** Verify build after all conversions.
- [ ] **Step 8:** Commit.

```bash
git commit -m "refactor: convert all remaining feature components to TypeScript"
```

---

### Task 14: CSS Cleanup

**Files:**
- Modify: `app/globals.css`

- [ ] **Step 1:** Remove the Google Fonts `@import` line (line 1):

```css
/* DELETE THIS LINE: */
@import url("https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&display=swap");
```

Keep all local `@font-face` declarations (lines 2-41).

- [ ] **Step 2:** Verify build, commit.

```bash
git add app/globals.css
git commit -m "fix: remove duplicate Google Fonts import, keep local @font-face"
```

---

## Phase 3: Pages

### Task 15: Convert Main Pages (Home, Catalog, Product)

**Files:**
- `app/page.jsx` → `.tsx`
- `app/catalog/page.jsx` → `.tsx`
- `app/catalog/[category]/page.jsx` → `.tsx`
- `app/catalog/loading.jsx` → `.tsx`
- `app/catalog/[category]/loading.jsx` → `.tsx`
- `app/product/[id]/page.jsx` → `.tsx`

- [ ] **Step 1:** Convert each file. Replace local `getProductPhotoCandidates`/`formatRubPrice` calls with imports from `@/lib/format/product-image` and `@/lib/format/price`. Remove dead `backendAssets` imports.

- [ ] **Step 2:** Verify build, commit.

```bash
git commit -m "refactor: convert main pages (home, catalog, product) to TypeScript"
```

---

### Task 16: Convert Favorites + Search Pages

**Files:**
- `app/favorites/page.jsx` → `.tsx`
- `app/favorites/brands/page.jsx` → `.tsx`
- `app/search/page.jsx` → `.tsx`

- [ ] **Step 1:** Convert. Replace local utility functions with shared imports. Remove dead `backendAssets` imports.

- [ ] **Step 2:** Verify build, commit.

```bash
git commit -m "refactor: convert favorites and search pages to TypeScript"
```

---

### Task 17: Convert Profile Pages

**Files:** All files in `app/profile/` (~28 files: 26 to convert + 2 mock data to delete) → `.tsx`/`.ts` (pages, client components, loading states)

- [ ] **Step 1:** Delete mock data files:
```bash
git rm app/profile/orders/mockOrders.js app/profile/purchased/mockPurchasedProducts.js
```

- [ ] **Step 2:** Convert client components (`OrdersClient`, `OrderDetailsClient`, `ReviewClient`, `CreateReturnClient`, `ReturnRequestClient`, `ComingSoon`) → `.tsx` with empty state UI.

- [ ] **Step 3:** Convert all profile page files → `.tsx`.

- [ ] **Step 4:** Verify build, commit.

```bash
git commit -m "refactor: convert profile pages to TypeScript, remove mock data"
```

---

### Task 18: Convert Remaining Pages

**Files:**
- `app/invite-friends/page.jsx` → `.tsx` (+ `InviteLinkActions.jsx`, `PromoCouponCard.jsx`, `loading.jsx`)
- `app/trash/page.jsx` → `.tsx`
- `app/checkout/page.jsx` → `.tsx`
- `app/checkout/pickup/page.jsx` → `.tsx`
- `app/checkout/pickup/search/page.jsx` → `.tsx`
- `app/poizon/page.jsx` → `.tsx`
- `app/promo/page.jsx` → `.tsx`

- [ ] **Step 1:** Convert each file. For `invite-friends`, replace local `formatRuDateTime`/`formatUntilDate` with imports from `@/lib/format/date`. For `trash`, replace local utilities with shared imports.

- [ ] **Step 2:** Add `loading.tsx` for main routes that don't have one. Currently only `catalog/`, `catalog/[category]/`, and `invite-friends/` have loading states. Create skeleton `loading.tsx` for:
  - `app/loading.tsx` (home)
  - `app/favorites/loading.tsx`
  - `app/search/loading.tsx`
  - `app/product/[id]/loading.tsx`
  - `app/profile/loading.tsx`
  - `app/trash/loading.tsx`
  - `app/checkout/loading.tsx`

Each should render a simple skeleton matching the page layout style.

- [ ] **Step 3:** Verify build, commit.

```bash
git commit -m "refactor: convert remaining pages to TypeScript, add missing loading states"
```

---

### Task 19: Convert BFF API Routes

**Files:** All 8 files in `app/api/` → `.ts`

- `app/api/backend/[...path]/route.js` → `.ts`
- `app/api/session/telegram/init/route.js` → `.ts`
- `app/api/auth/telegram/exchange/route.js` → `.ts`
- `app/api/auth/telegram/consume/route.js` → `.ts`
- `app/api/auth/telegram/_handoffStore.js` → `.ts`
- `app/api/dadata/suggest/address/route.js` → `.ts`
- `app/api/dadata/clean/address/route.js` → `.ts`
- `app/api/session/logout/route.js` → `.ts`

- [ ] **Step 1:** Convert each file. Add types to function parameters and return values. Update import paths for moved auth modules.

- [ ] **Step 2:** Verify build, commit.

```bash
git commit -m "refactor: convert BFF API routes to TypeScript"
```

---

### Task 20: Final Cleanup

**Files:**
- Delete: `lib/format/backendAssets.js` (replaced by `product-image.ts` + `brand-image.ts`)
- Rename: `next.config.js` → `next.config.ts`
- Create: `.env.example`

- [ ] **Step 1: Delete old backendAssets**

```bash
git rm lib/format/backendAssets.js
```

Verify no imports remain:
```bash
grep -r "backendAssets" app/ components/ lib/ --include="*.ts" --include="*.tsx"
```
Expected: 0 matches.

- [ ] **Step 2: Convert `next.config.js` → `next.config.ts`**

```ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "i.pravatar.cc",
        pathname: "/**",
      },
    ],
  },
};

export default nextConfig;
```

```bash
git rm next.config.js
git add next.config.ts
```

- [ ] **Step 3: Create `.env.example`**

```env
# Backend API
BACKEND_API_BASE_URL=http://localhost:8080

# Telegram Bot
TG_BOT_TOKEN=your_bot_token_here
TG_INITDATA_MAX_AGE_SECONDS=300

# DaData (address suggestions)
DADATA_TOKEN=your_dadata_token
DADATA_SECRET=your_dadata_secret

# Cookie
COOKIE_DOMAIN=

# Debug (dev only)
BROWSER_DEBUG_AUTH=true
NEXT_PUBLIC_BROWSER_DEBUG_AUTH=true
BROWSER_DEBUG_AUTH_ALLOWED_HOSTS=localhost
```

- [ ] **Step 4: Final verification**

```bash
# No .js/.jsx in source dirs
find app/ components/ lib/ -name "*.js" -o -name "*.jsx" | head -5
# Expected: 0 files

# Build passes
npx next build 2>&1 | head -5
# Expected: ✓ Compiled successfully

# TypeScript passes
npx tsc --noEmit 2>&1 | tail -5
# Expected: 0 errors
```

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore: final cleanup — delete backendAssets, convert next.config, add .env.example"
```

---

## Verification Checklist

After all tasks complete, verify these success criteria:

- [ ] `npx next build` passes with 0 errors
- [ ] `npx tsc --noEmit` passes with 0 errors
- [ ] No `.js` or `.jsx` files remain in `app/`, `components/`, `lib/`
- [ ] No duplicate utility functions across files
- [ ] No dead imports or dead code
- [ ] All components have typed props interfaces
- [ ] Error Boundary (`app/error.tsx`) renders on runtime error
- [ ] 404 page (`app/not-found.tsx`) renders on invalid route
- [ ] `strict: true` in `tsconfig.json`
- [ ] `next.config.ts` used instead of `.js`
