import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import {
  mapStorefrontProduct as sharedMapStorefrontProduct,
  unwrapPLPResponse as sharedUnwrapPLPResponse,
  resolveI18N,
} from "@/lib/format/mapStorefrontProduct";
import { mapCategoryTree as mapCategoryTreeResponse } from "@/lib/format/mapCategoryTree";
import {
  mapPickupPointsResponse,
  buildPickupPointsRequestBody,
} from "@/lib/format/mapPickupPoints";
import { useAuthStore } from "@/lib/features/auth/store";
import { AuthStatus } from "@/lib/features/auth/types";
import {
  getAnonymousToken,
  clearAnonymousToken,
} from "@/lib/cart/anonymousToken";
import { isTokenExpiredError } from "@/lib/api/errors";
import {
  readHistory as readSearchHistory,
  addEntry as addSearchHistoryEntry,
  removeEntry as removeSearchHistoryEntry,
  clearHistory as clearSearchHistoryStorage,
  subscribe as subscribeSearchHistory,
} from "@/lib/search/history";

// MoneyResponse { amount (kopecks, int), currency } → rubles number
function moneyToRub(money) {
  if (money == null) return 0;
  if (typeof money === "number") return money;
  const amount = Number(money?.amount);
  if (!Number.isFinite(amount)) return 0;
  return amount / 100;
}

/**
 * Normalize backend CartResponse → flat client shape.
 *
 * Backend (OpenAPI):
 *   CartResponse { id, status, itemCount, total: MoneyResponse,
 *                  groups: CartGroupResponse[] }
 *   CartGroupResponse { supplierType, items: CartItemResponse[], subtotal }
 *   CartItemResponse { id, skuId, productId, variantId, productName,
 *                      variantLabel, imageUrl, quantity, unitPrice,
 *                      lineTotal, supplierType, addedAt }
 *
 * Client shape (flat, legacy-kompatibel):
 *   { id, status, total_items, total_amount, currency, items: Item[], groups }
 *   Item { id, skuId, productId, variantId, productName, variantLabel,
 *          imageUrl, quantity, priceRub, lineTotalRub, supplierType, addedAt }
 */
function normalizeCartResponse(raw) {
  if (!raw || typeof raw !== "object") {
    return {
      id: null,
      status: "empty",
      total_items: 0,
      total_amount: 0,
      currency: "RUB",
      items: [],
      groups: [],
    };
  }

  const groups = Array.isArray(raw.groups) ? raw.groups : [];
  const flatItems = [];

  for (const g of groups) {
    const gItems = Array.isArray(g?.items) ? g.items : [];
    for (const it of gItems) {
      if (!it || typeof it !== "object") continue;
      flatItems.push({
        id: it.id,
        skuId: it.skuId,
        productId: it.productId,
        variantId: it.variantId,
        productName: it.productName ?? "",
        variantLabel: it.variantLabel ?? "",
        imageUrl: it.imageUrl ?? "",
        quantity: Number(it.quantity) || 0,
        priceRub: moneyToRub(it.unitPrice),
        lineTotalRub: moneyToRub(it.lineTotal),
        supplierType: it.supplierType ?? g?.supplierType ?? "",
        addedAt: it.addedAt ?? null,
      });
    }
  }

  return {
    id: raw.id ?? null,
    status: raw.status ?? "active",
    total_items:
      typeof raw.itemCount === "number"
        ? raw.itemCount
        : flatItems.reduce((s, x) => s + x.quantity, 0),
    total_amount: moneyToRub(raw.total),
    currency: raw.total?.currency ?? "RUB",
    items: flatItems,
    groups,
  };
}

function recalcCartTotals(cart) {
  if (!cart || typeof cart !== "object") return;
  const items = Array.isArray(cart.items) ? cart.items : [];
  let totalItems = 0;
  let totalAmount = 0;
  for (const it of items) {
    const qty = Number(it?.quantity);
    const q = Number.isFinite(qty) && qty > 0 ? qty : 0;
    totalItems += q;

    const line = Number(it?.lineTotalRub);
    if (Number.isFinite(line) && line > 0) {
      totalAmount += line;
      continue;
    }
    const price = Number(it?.priceRub);
    if (Number.isFinite(price)) totalAmount += price * q;
  }

  cart.total_items = totalItems;
  cart.total_amount = totalAmount;
}

// Re-export shared mapper so existing call sites inside this module keep working.
// The canonical implementation lives in lib/format/mapStorefrontProduct.js
// so Server Components can reuse it without pulling RTK Query into the server bundle.
const mapStorefrontProduct = sharedMapStorefrontProduct;
const unwrapPLPResponse = sharedUnwrapPLPResponse;

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "/api/backend";

// Spec §7: `X-Anonymous-Token` faqat `/cart/*` uchun, lekin `/cart/checkout*`
// va `/cart/merge` chiqarib tashlangan — checkout faqat authenticated, merge
// esa Bearer + body'dagi token'ni o'zi qabul qiladi.
function shouldAttachAnonymousToken(url) {
  if (typeof url !== "string") return false;
  if (!url.includes("/api/v1/cart")) return false;
  if (url.includes("/cart/checkout")) return false;
  if (url.includes("/cart/merge")) return false;
  if (url.includes("/cart/anonymous-token")) return false;
  return true;
}

const backendBaseQuery = fetchBaseQuery({
  baseUrl,
  credentials: "include", // httpOnly cookie session
});

const appBaseQuery = fetchBaseQuery({
  baseUrl: "",
  credentials: "include",
});

// Deduplication: concurrent 401s should share a single refresh call
let refreshPromise = null;

function withAnonymousTokenHeader(args, url) {
  if (!shouldAttachAnonymousToken(url)) return args;
  const token = getAnonymousToken();
  if (!token) return args;

  // String shorthand'ni object ga aylantirish — header qo'shish uchun
  const obj = typeof args === "string" ? { url: args } : { ...args };
  obj.headers = { ...(obj.headers || {}), "x-anonymous-token": token };
  return obj;
}

const baseQuery = async (args, queryApi, extraOptions) => {
  const url = typeof args === "string" ? args : args?.url;

  // Local Next.js BFF routes (auth refresh helper'lari)
  if (typeof url === "string" && url.startsWith("/api/auth/")) {
    return appBaseQuery(args, queryApi, extraOptions);
  }

  // Cart endpoint'lariga `X-Anonymous-Token` header'ni inject qilamiz
  const enrichedArgs = withAnonymousTokenHeader(args, url);

  // Backend calls through /api/backend proxy + auto-refresh on 401
  let result = await backendBaseQuery(enrichedArgs, queryApi, extraOptions);

  // Spec §3: 401 + `code` (TOKEN_EXPIRED, TOKEN_VERSION_STALE, ...) → refresh
  if (isTokenExpiredError(result?.error)) {
    // Defense-in-depth: agar hook AuthGate chetlab o'tib render bo'lgan bo'lsa
    // yoki hali birinchi marta autentifikatsiya tugamagan bo'lsa — refresh
    // chaqirish mantiqsiz (refresh cookie ham yo'q). emitAuthExpired ham
    // chaqirilmaydi, aks holda 401→refresh→expired→re-auth loop'i ochiladi.
    const authStatus = useAuthStore.getState().status;
    if (authStatus !== AuthStatus.AUTHENTICATED) {
      return result;
    }

    // Reuse an in-flight refresh if one is already running
    if (!refreshPromise) {
      refreshPromise = appBaseQuery(
        { url: "/api/auth/refresh", method: "POST" },
        queryApi,
        extraOptions,
      ).finally(() => {
        // Small tick to let concurrent callers attach, then clear
        setTimeout(() => {
          refreshPromise = null;
        }, 0);
      });
    }

    const refreshResult = await refreshPromise;

    if (refreshResult?.data?.ok) {
      // Retry original request with fresh cookie
      result = await backendBaseQuery(enrichedArgs, queryApi, extraOptions);
    } else {
      // Refresh failed — emit auth expired event (only once per batch)
      try {
        const { emitAuthExpired } = await import("@/lib/auth-events");
        emitAuthExpired();
      } catch {
        // ignore
      }
    }
  }

  return result;
};

export const api = createApi({
  reducerPath: "api",
  baseQuery,
  tagTypes: [
    "User",
    "Products",
    "Product",
    "ForYouFeed",
    "Trending",
    "Categories",
    "CategoryTree",
    "Types",
    "Brands",
    "Favorites",
    "Cart",
    "Orders",
    "Payments",
    "Shipments",
    "Referrals",
    "PVZ",
    "SearchHistory",
  ],
  endpoints: (builder) => ({
    // Session/User
    getMe: builder.query({
      query: () => "/api/v1/profile/me",
      transformResponse: (response) => ({
        ...response,
        first_name: response?.firstName,
        last_name: response?.lastName,
        photo_url: response?.photoUrl || null,
      }),
      providesTags: ["User"],
    }),

    // Products
    getProducts: builder.query({
      query: (params) => {
        const sp = new URLSearchParams();
        if (params?.category_id != null)
          sp.set("category_id", String(params.category_id));
        if (params?.limit != null) sp.set("limit", String(params.limit));
        if (params?.cursor != null) sp.set("cursor", String(params.cursor));

        // Backend OR-semantics: `brand_id=A&brand_id=B` (array bitta query
        // kalitida bir nechta marta uchraydi). `set` o'rniga `append`.
        const brandIds = Array.isArray(params?.brand_id)
          ? params.brand_id.filter((x) => x != null && x !== "")
          : params?.brand_id != null
            ? [params.brand_id]
            : [];
        for (const id of brandIds) sp.append("brand_id", String(id));

        if (params?.price_min != null)
          sp.set("price_min", String(params.price_min));
        if (params?.price_max != null)
          sp.set("price_max", String(params.price_max));
        if (params?.in_stock != null)
          sp.set("in_stock", String(params.in_stock));
        if (params?.sort != null) sp.set("sort", String(params.sort));
        if (params?.include_facets) sp.set("include_facets", "true");
        if (params?.lang != null) sp.set("lang", String(params.lang));

        const qs = sp.toString();
        const base = "/api/v1/catalog/storefront/products";
        return qs ? `${base}?${qs}` : base;
      },
      transformResponse: (response) => unwrapPLPResponse(response),
      providesTags: (result) => {
        const items = Array.isArray(result?.items) ? result.items : Array.isArray(result) ? result : [];
        if (!items.length) return ["Products"];
        return [
          "Products",
          ...items
            .map((p) => (p && typeof p === "object" ? p.id : null))
            .filter((id) => id != null)
            .map((id) => ({ type: "Product", id })),
        ];
      },
    }),

    getProductById: builder.query({
      query: (slugOrId) =>
        `/api/v1/catalog/storefront/products/${encodeURIComponent(String(slugOrId))}`,
      transformResponse: (response) => mapStorefrontProduct(response) || response,
      providesTags: (result, err, slugOrId) => [
        { type: "Product", id: slugOrId },
      ],
      keepUnusedDataFor: 300,
    }),

    getSimilarProducts: builder.query({
      query: ({ slug, limit = 12 } = {}) => {
        const sp = new URLSearchParams();
        if (limit != null) sp.set("limit", String(limit));
        return `/api/v1/catalog/storefront/products/${encodeURIComponent(
          String(slug),
        )}/similar?${sp.toString()}`;
      },
      transformResponse: (response) => {
        const items = Array.isArray(response) ? response : [];
        return items.map(mapStorefrontProduct).filter(Boolean);
      },
      providesTags: (result, err, arg) => [
        { type: "Product", id: `similar-${arg?.slug || ""}` },
      ],
      keepUnusedDataFor: 180,
    }),

    getAlsoViewedProducts: builder.query({
      query: ({ slug, limit = 12 } = {}) => {
        const sp = new URLSearchParams();
        if (limit != null) sp.set("limit", String(limit));
        return `/api/v1/catalog/storefront/products/${encodeURIComponent(
          String(slug),
        )}/also-viewed?${sp.toString()}`;
      },
      transformResponse: (response) => {
        const items = Array.isArray(response) ? response : [];
        return items.map(mapStorefrontProduct).filter(Boolean);
      },
      providesTags: (result, err, arg) => [
        { type: "Product", id: `also-viewed-${arg?.slug || ""}` },
      ],
      keepUnusedDataFor: 180,
    }),

    // Product media (admin endpoint, forwarded via BFF which attaches
    // the user's Bearer token). Used as PDP image source because the
    // storefront PDP currently returns `media: []` — see docs/backend-tz-pdp-media.md.
    //
    // Returns URL list derived from MediaAssetResponse[] filtered to images
    // with safe public roles and ordered by sort_order.
    getProductMedia: builder.query({
      query: ({ productId, limit = 50 } = {}) => {
        const sp = new URLSearchParams();
        if (limit != null) sp.set("limit", String(limit));
        return `/api/v1/catalog/products/${encodeURIComponent(
          String(productId),
        )}/media?${sp.toString()}`;
      },
      // Returns full MediaAssetResponse[] sorted main-first, then by sortOrder.
      // Consumers filter by role/variantId as needed (see lib/product/attributes.js).
      transformResponse: (response) => {
        const items = Array.isArray(response?.items)
          ? response.items
          : Array.isArray(response)
            ? response
            : [];
        const valid = items.filter(
          (m) =>
            m &&
            typeof m === "object" &&
            m.mediaType !== "video" &&
            typeof m.url === "string" &&
            m.url.trim(),
        );
        valid.sort((a, b) => {
          const ar = a.role === "main" ? -1 : 0;
          const br = b.role === "main" ? -1 : 0;
          if (ar !== br) return ar - br;
          return (a.sortOrder ?? 0) - (b.sortOrder ?? 0);
        });
        return valid;
      },
      providesTags: (result, err, arg) => [
        { type: "Product", id: `media-${arg?.productId || ""}` },
      ],
      keepUnusedDataFor: 300,
    }),

    getProductsByIds: builder.query({
      async queryFn(ids, _api, _extraOptions, baseQuery) {
        const raw = Array.isArray(ids) ? ids : [];
        const uniqueIds = Array.from(
          new Set(raw.map((x) => String(x)).filter((x) => x)),
        );

        if (uniqueIds.length === 0) return { data: [] };

        const state = _api.getState();

        const products = await Promise.all(
          uniqueIds.map(async (id) => {
            try {
              const cached = api.endpoints.getProductById.select(id)(state);
              if (cached?.data && typeof cached.data === "object") {
                return cached.data;
              }

              const result = await _api
                .dispatch(
                  api.endpoints.getProductById.initiate(id, {
                    subscribe: false,
                    forceRefetch: false,
                  }),
                )
                .unwrap();
              return result && typeof result === "object" ? result : null;
            } catch {
              const r = await baseQuery(
                `/api/v1/catalog/storefront/products/${encodeURIComponent(String(id))}`,
              );
              const data = r && typeof r === "object" ? r.data : null;
              return data && typeof data === "object" ? mapStorefrontProduct(data) : null;
            }
          }),
        );

        return {
          data: products.filter((p) => p && typeof p === "object"),
        };
      },
      providesTags: (result) => {
        if (!Array.isArray(result)) return ["Products"];
        return [
          "Products",
          ...result
            .map((p) => (p && typeof p === "object" ? p.id : null))
            .filter((id) => id != null)
            .map((id) => ({ type: "Product", id })),
        ];
      },
    }),

    getLatestProducts: builder.query({
      query: (params) => {
        const sp = new URLSearchParams();
        if (params?.category_id != null) sp.set("category_id", String(params.category_id));
        sp.set("sort", "newest");
        const limit = typeof params === "object" ? params?.limit : params;
        const n = limit == null ? null : Number(limit);
        if (typeof n === "number" && Number.isFinite(n) && n > 0) {
          sp.set("limit", String(Math.floor(n)));
        }
        return `/api/v1/catalog/storefront/products?${sp.toString()}`;
      },
      transformResponse: (response) => unwrapPLPResponse(response),
      providesTags: ["Products"],
    }),

    // Fallback: uses sort=newest since no latest-purchased endpoint exists
    getLatestPurchasedProducts: builder.query({
      query: (params) => {
        const sp = new URLSearchParams();
        if (params?.category_id != null) sp.set("category_id", String(params.category_id));
        sp.set("sort", "newest");
        const limit = typeof params === "object" ? params?.limit : params;
        const n = limit == null ? null : Number(limit);
        if (typeof n === "number" && Number.isFinite(n) && n > 0) {
          sp.set("limit", String(Math.floor(n)));
        }
        return `/api/v1/catalog/storefront/products?${sp.toString()}`;
      },
      transformResponse: (response) => {
        const plp = unwrapPLPResponse(response);
        return plp.items;
      },
      providesTags: ["Products"],
    }),

    // Personalized "Для вас" feed (cursor-paginated).
    // Auth'dan kelib chiqib server personalizatsiya / cold-start qaytaradi.
    // Alohida "ForYouFeed" tag bilan marked — "Products" invalidatsiyasi uni
    // qayta yuklab yubormaydi (auth bootstrap'dan keladigan keraksiz fetch'lardan himoya).
    getForYouFeed: builder.query({
      query: (params) => {
        const sp = new URLSearchParams();
        if (params?.limit != null) sp.set("limit", String(params.limit));
        if (params?.cursor != null) sp.set("cursor", String(params.cursor));
        if (params?.lang != null) sp.set("lang", String(params.lang));
        const qs = sp.toString();
        const base = "/api/v1/catalog/storefront/for-you";
        return qs ? `${base}?${qs}` : base;
      },
      transformResponse: (response) => {
        const items = Array.isArray(response?.items) ? response.items : [];
        return {
          items: items.map(mapStorefrontProduct).filter(Boolean),
          nextCursor: response?.next_cursor ?? null,
          hasNext: Boolean(response?.next_cursor),
          strategyVersion: response?.strategy_version ?? null,
          isPersonalized: Boolean(response?.is_personalized),
        };
      },
      // Home feed'ni tab o'zgarishida qayta yuklamaslik — 5 daqiqa cache.
      keepUnusedDataFor: 300,
      providesTags: (result) => {
        const items = Array.isArray(result?.items) ? result.items : [];
        if (!items.length) return ["ForYouFeed"];
        return [
          "ForYouFeed",
          ...items
            .map((p) => (p && typeof p === "object" ? p.id : null))
            .filter((id) => id != null)
            .map((id) => ({ type: "Product", id })),
        ];
      },
    }),

    // Trending products ("Только что купили" placeholder — eng ko'p ko'rilgan).
    // Redis sorted set'lar asosida, global yoki kategoriya bo'yicha.
    getTrendingProducts: builder.query({
      query: (params) => {
        const sp = new URLSearchParams();
        if (params?.limit != null) sp.set("limit", String(params.limit));
        if (params?.window != null) sp.set("window", String(params.window));
        if (params?.category_id != null) sp.set("category_id", String(params.category_id));
        if (params?.lang != null) sp.set("lang", String(params.lang));
        const qs = sp.toString();
        const base = "/api/v1/catalog/storefront/trending";
        return qs ? `${base}?${qs}` : base;
      },
      transformResponse: (response) => {
        const plp = unwrapPLPResponse(response);
        return plp.items;
      },
      keepUnusedDataFor: 300,
      providesTags: (result) => {
        const items = Array.isArray(result) ? result : [];
        if (!items.length) return ["Trending"];
        return [
          "Trending",
          ...items
            .map((p) => (p && typeof p === "object" ? p.id : null))
            .filter((id) => id != null)
            .map((id) => ({ type: "Product", id })),
        ];
      },
    }),

    // Categories
    getCategoryTree: builder.query({
      query: (arg) => {
        const maxDepth = Number(arg?.maxDepth);
        const qs =
          Number.isInteger(maxDepth) && maxDepth >= 1 && maxDepth <= 10
            ? `?max_depth=${maxDepth}`
            : "";
        return `/api/v1/catalog/categories/tree${qs}`;
      },
      keepUnusedDataFor: 1800,
      transformResponse: (response) => {
        // Lazy import-free normalization: re-use mapCategoryTree logic inline
        // to avoid cyclic deps. We import at top-of-file below (see imports).
        return mapCategoryTreeResponse(response);
      },
      providesTags: ["CategoryTree"],
    }),
    getCategories: builder.query({
      query: () => "/api/v1/catalog/categories?limit=100",
      keepUnusedDataFor: 1800,
      transformResponse: (response) => {
        const items = Array.isArray(response?.items) ? response.items : Array.isArray(response) ? response : [];
        return items
          .filter((c) => c && typeof c === "object")
          .map((c) => ({
            ...c,
            name: resolveI18N(c.nameI18N, c.name || c.title || c.label || ""),
          }));
      },
      providesTags: (result) => {
        if (!Array.isArray(result)) return ["Categories"];
        return [
          "Categories",
          ...result
            .map((c) => (c && typeof c === "object" ? c.id : null))
            .filter((id) => id != null)
            .map((id) => ({ type: "Categories", id })),
        ];
      },
    }),
    createCategory: builder.mutation({
      query: (payload) => ({
        url: "/api/v1/catalog/categories",
        method: "POST",
        headers: { "content-type": "application/json" },
        body: payload,
      }),
      invalidatesTags: ["Categories"],
    }),
    deleteCategory: builder.mutation({
      query: (categoryId) => ({
        url: `/api/v1/catalog/categories/${encodeURIComponent(String(categoryId))}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Categories"],
    }),

    // Types — backend'da /api/v1/types yo'q (Spec §6: faqat
    // catalog/{categories,brands,attributes,...} mavjud). Eski UI uchun
    // bo'sh fallback.
    getCategoriesWithTypes: builder.query({
      async queryFn() {
        return { data: [] };
      },
      keepUnusedDataFor: 1800,
      providesTags: ["Types"],
    }),
    getTypesByCategory: builder.query({
      async queryFn() {
        return { data: [] };
      },
      providesTags: ["Types"],
    }),

    // Brands
    getBrands: builder.query({
      query: () => "/api/v1/catalog/brands?limit=200",
      keepUnusedDataFor: 1800,
      transformResponse: (response) => {
        const items = Array.isArray(response?.items) ? response.items : Array.isArray(response) ? response : [];
        return items.filter((b) => b && typeof b === "object");
      },
      providesTags: (result) => {
        if (!Array.isArray(result)) return ["Brands"];
        return [
          "Brands",
          ...result
            .map((b) => (b && typeof b === "object" ? b.id : null))
            .filter((id) => id != null)
            .map((id) => ({ type: "Brands", id })),
        ];
      },
    }),
    // Backend'da `/brands/search` yo'q — `getBrands`'ni qaytarib, klient
    // tarafda filtrlaymiz. PLP UI bunga qarab ishlaydi.
    searchBrands: builder.query({
      async queryFn({ q } = {}, _api, _extraOptions, baseQuery) {
        const res = await baseQuery("/api/v1/catalog/brands?limit=200");
        if (res?.error) return { error: res.error };
        const items = Array.isArray(res?.data?.items)
          ? res.data.items
          : Array.isArray(res?.data)
            ? res.data
            : [];
        const needle = String(q || "").trim().toLowerCase();
        const filtered = needle
          ? items.filter((b) => {
              const name =
                resolveI18N(b?.nameI18N, b?.name || "") ?? b?.name ?? "";
              return String(name).toLowerCase().includes(needle);
            })
          : items;
        return { data: filtered };
      },
      providesTags: ["Brands"],
    }),
    getBrandById: builder.query({
      query: (brandId) =>
        `/api/v1/catalog/brands/${encodeURIComponent(String(brandId))}`,
      providesTags: (_result, _err, brandId) => [
        { type: "Brands", id: brandId },
      ],
    }),
    createBrand: builder.mutation({
      query: (formData) => ({
        url: "/api/v1/catalog/brands",
        method: "POST",
        body: formData,
      }),
      invalidatesTags: ["Brands"],
    }),
    deleteBrand: builder.mutation({
      query: (brandId) => ({
        url: `/api/v1/catalog/brands/${encodeURIComponent(String(brandId))}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Brands"],
    }),
    // `/brands/{id}/logo` backend'da yo'q — `Product Media`'siga o'xshash
    // brand-logo endpoint v1 spec'ida e'lon qilinmagan. Admin app brand
    // tahriri katalog/brands PATCH orqali (logo URL maydoni bilan) amalga
    // oshiriladi. Customer app uchun bu mutatsiyalar kerak emas.
    uploadBrandLogo: builder.mutation({
      async queryFn() {
        return { error: { status: 501, data: { error: { code: "NOT_IMPLEMENTED" } } } };
      },
    }),
    deleteBrandLogo: builder.mutation({
      async queryFn() {
        return { error: { status: 501, data: { error: { code: "NOT_IMPLEMENTED" } } } };
      },
    }),

    // Favorites (no backend equivalent — graceful fallback)
    getFavorites: builder.query({
      async queryFn(_params) {
        // Backend has no /api/v1/favorites endpoint — return empty array
        return { data: [] };
      },
      providesTags: ["Favorites"],
    }),
    addFavorite: builder.mutation({
      async queryFn(_payload) {
        // No backend favorites — no-op
        return { data: { ok: true } };
      },
      invalidatesTags: ["Favorites"],
    }),
    removeFavorite: builder.mutation({
      async queryFn(_favoriteId) {
        // No backend favorites — no-op
        return { data: { ok: true } };
      },
      invalidatesTags: ["Favorites"],
    }),

    // Referrals — Spec §11: «Промо-код / Loyalty points / Referral» moduli
    // v1 backend'da yo'q. UI invite-friends sahifalarini bo'sh ma'lumot
    // bilan render qilishi uchun `queryFn` empty fallback'ga o'tkazilgan.
    getMyReferralLink: builder.query({
      async queryFn() {
        return { data: null };
      },
      providesTags: ["Referrals"],
    }),
    getMyInvitedUsers: builder.query({
      async queryFn() {
        return { data: [] };
      },
      providesTags: ["Referrals"],
    }),
    getMyActiveDiscount: builder.query({
      async queryFn() {
        return { data: null };
      },
      providesTags: ["Referrals"],
    }),
    getMyReferralStats: builder.query({
      async queryFn() {
        return { data: { invitedCount: 0, totalDiscountRub: 0 } };
      },
      providesTags: ["Referrals"],
    }),

    // Cart — backend spec: CartResponse (groups[].items[], MoneyResponse)
    getMyCart: builder.query({
      query: () => "/api/v1/cart",
      transformResponse: (response) => normalizeCartResponse(response),
      providesTags: ["Cart"],
    }),
    getCartSummary: builder.query({
      query: () => "/api/v1/cart/summary",
      transformResponse: (response) => ({
        itemCount: Number(response?.itemCount) || 0,
        totalRub: moneyToRub(response?.total),
        currency: response?.total?.currency ?? "RUB",
      }),
      providesTags: ["Cart"],
    }),
    clearCart: builder.mutation({
      query: () => ({
        url: "/api/v1/cart",
        method: "DELETE",
      }),
      async onQueryStarted(_arg, { dispatch, queryFulfilled }) {
        const patch = dispatch(
          api.util.updateQueryData("getMyCart", undefined, (draft) => {
            if (!draft || typeof draft !== "object") return;
            draft.items = [];
            draft.groups = [];
            draft.total_items = 0;
            draft.total_amount = 0;
          }),
        );
        try {
          await queryFulfilled;
        } catch {
          patch.undo();
        }
      },
      invalidatesTags: ["Cart"],
    }),
    // AddItemRequest: { skuId, quantity }  → AddItemResponse { cartId, itemId }
    addCartItem: builder.mutation({
      query: (payload) => ({
        url: "/api/v1/cart/items",
        method: "POST",
        headers: { "content-type": "application/json" },
        body: {
          skuId: payload?.skuId,
          quantity: Math.max(1, Math.floor(Number(payload?.quantity || 1))),
        },
      }),
      async onQueryStarted(payload, { dispatch, queryFulfilled }) {
        const skuId = payload?.skuId;
        const qty = Math.max(1, Math.floor(Number(payload?.quantity || 1)));
        if (!skuId) return;

        const patch = dispatch(
          api.util.updateQueryData("getMyCart", undefined, (draft) => {
            if (!draft || typeof draft !== "object") return;
            const list = Array.isArray(draft.items) ? draft.items : [];
            const idx = list.findIndex(
              (x) => String(x?.skuId) === String(skuId),
            );
            if (idx >= 0) {
              const prev = Number(list[idx]?.quantity) || 0;
              list[idx].quantity = prev + qty;
              const price = Number(list[idx]?.priceRub) || 0;
              list[idx].lineTotalRub = price * list[idx].quantity;
            } else {
              list.push({
                id: null,
                skuId,
                productId: payload?.productId ?? null,
                variantId: payload?.variantId ?? null,
                productName: payload?.productName ?? "",
                variantLabel: payload?.variantLabel ?? "",
                imageUrl: payload?.imageUrl ?? "",
                quantity: qty,
                priceRub: Number(payload?.priceRub) || 0,
                lineTotalRub: (Number(payload?.priceRub) || 0) * qty,
                supplierType: payload?.supplierType ?? "",
                addedAt: new Date().toISOString(),
              });
            }
            draft.items = list;
            recalcCartTotals(draft);
          }),
        );

        try {
          await queryFulfilled;
        } catch {
          patch.undo();
        }
      },
      invalidatesTags: ["Cart"],
    }),
    // PATCH /cart/items/{sku_id}  body: UpdateQuantityRequest { quantity }
    updateCartItem: builder.mutation({
      query: ({ skuId, quantity }) => ({
        url: `/api/v1/cart/items/${encodeURIComponent(String(skuId))}`,
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: { quantity: Math.max(1, Math.floor(Number(quantity || 1))) },
      }),
      async onQueryStarted({ skuId, quantity }, { dispatch, queryFulfilled }) {
        const nextQty = Number(quantity);
        const patch = dispatch(
          api.util.updateQueryData("getMyCart", undefined, (draft) => {
            if (!draft || typeof draft !== "object") return;
            const list = Array.isArray(draft.items) ? draft.items : [];
            const idx = list.findIndex(
              (x) => String(x?.skuId) === String(skuId),
            );
            if (idx < 0 || !Number.isFinite(nextQty) || nextQty < 0) return;

            if (nextQty === 0) {
              list.splice(idx, 1);
            } else {
              list[idx].quantity = nextQty;
              const price = Number(list[idx]?.priceRub) || 0;
              list[idx].lineTotalRub = price * nextQty;
            }
            draft.items = list;
            recalcCartTotals(draft);
          }),
        );

        try {
          await queryFulfilled;
        } catch {
          patch.undo();
        }
      },
      invalidatesTags: ["Cart"],
    }),
    // DELETE /cart/items/{sku_id}
    removeCartItem: builder.mutation({
      query: (skuId) => ({
        url: `/api/v1/cart/items/${encodeURIComponent(String(skuId))}`,
        method: "DELETE",
      }),
      async onQueryStarted(skuId, { dispatch, queryFulfilled }) {
        const patch = dispatch(
          api.util.updateQueryData("getMyCart", undefined, (draft) => {
            if (!draft || typeof draft !== "object") return;
            const list = Array.isArray(draft.items) ? draft.items : [];
            draft.items = list.filter(
              (x) => String(x?.skuId) !== String(skuId),
            );
            recalcCartTotals(draft);
          }),
        );
        try {
          await queryFulfilled;
        } catch {
          patch.undo();
        }
      },
      invalidatesTags: ["Cart"],
    }),

    // Checkout (freeze → confirm) — OpenAPI: InitiateCheckoutRequest { pickupPointId }
    initiateCheckout: builder.mutation({
      query: ({ pickupPointId }) => ({
        url: "/api/v1/cart/checkout",
        method: "POST",
        headers: { "content-type": "application/json" },
        body: { pickupPointId },
      }),
    }),
    confirmCheckout: builder.mutation({
      query: ({ attemptId }) => ({
        url: "/api/v1/cart/checkout/confirm",
        method: "POST",
        headers: { "content-type": "application/json" },
        body: { attemptId },
      }),
      invalidatesTags: ["Cart", "Orders"],
    }),
    cancelCheckout: builder.mutation({
      query: () => ({
        url: "/api/v1/cart/checkout/cancel",
        method: "POST",
      }),
      invalidatesTags: ["Cart"],
    }),
    // Anonymous cart token (Spec §7.3) — guest cart yaratiladi, token
    // localStorage'ga saqlanadi. Cart endpoint'lariga keyin
    // `X-Anonymous-Token` header sifatida yuboriladi.
    getAnonymousCartToken: builder.mutation({
      query: () => ({
        url: "/api/v1/cart/anonymous-token",
        method: "POST",
      }),
    }),

    // Merge guest cart → authenticated cart. Login muvaffaqiyatli
    // bo'lgandan keyin chaqiriladi (TelegramAuthBootstrap orqali).
    mergeCart: builder.mutation({
      query: ({ anonymousToken }) => ({
        url: "/api/v1/cart/merge",
        method: "POST",
        headers: { "content-type": "application/json" },
        body: { anonymousToken },
      }),
      invalidatesTags: ["Cart"],
    }),

    // Pickup-points (POST /logistics/pickup-points). Spec §8.1: snake_case
    // body, `lat+lng` yoki `city` majburiy. Server javobi ham snake_case.
    //
    // POST query (RTK Query qabul qiladi) — cache key serialized arg
    // bo'ladi, shuning uchun map pan/filter o'zgarganda alohida cache
    // entry yaratiladi va eski natija saqlanadi (refetch flicker yo'q).
    // `transformResponse` snake_case → camelCase ko'chiradi va compound
    // id (`provider_code:external_id`) yaratadi.
    listPickupPoints: builder.query({
      query: (args) => ({
        url: "/api/v1/logistics/pickup-points",
        method: "POST",
        headers: { "content-type": "application/json" },
        body: buildPickupPointsRequestBody(args) ?? {},
      }),
      transformResponse: mapPickupPointsResponse,
      keepUnusedDataFor: 60,
      providesTags: ["PVZ"],
    }),

    // Rate quote (Spec §8.2) — checkout-flow uchun yagona quote.
    // `quote_id` 30 daqiqa amal qiladi; UI bu vaqtni `expires_at` orqali
    // kuzatib turadi va kerak bo'lsa qayta chaqiradi.
    getRateQuote: builder.mutation({
      query: ({ items, providerCode, pickupPointExternalId, serviceCode }) => ({
        url: "/api/v1/logistics/rates/quote",
        method: "POST",
        headers: { "content-type": "application/json" },
        body: {
          items: Array.isArray(items)
            ? items.map((it) => ({
                sku_id: it?.skuId ?? it?.sku_id,
                quantity: Math.max(1, Math.floor(Number(it?.quantity || 1))),
              }))
            : [],
          provider_code: providerCode,
          pickup_point_external_id: pickupPointExternalId,
          service_code: serviceCode ?? null,
        },
      }),
    }),

    // Orders — Spec §11: backend'da Orders moduli yo'q. Cart `confirmCheckout`
    // `orderId` qaytaradi, lekin `GET/PATCH /orders/*` endpoint'lari hali
    // mavjud emas. UI bo'sh ma'lumot bilan render qilishi uchun fallback.
    listOrders: builder.query({
      async queryFn() {
        return { data: [] };
      },
      providesTags: ["Orders"],
    }),
    getOrderById: builder.query({
      async queryFn() {
        return { data: null };
      },
      providesTags: (_result, _err, orderId) => [
        { type: "Orders", id: orderId },
      ],
    }),
    createOrder: builder.mutation({
      async queryFn() {
        return { error: { status: 501, data: { error: { code: "NOT_IMPLEMENTED" } } } };
      },
    }),
    updateOrderStatus: builder.mutation({
      async queryFn() {
        return { error: { status: 501, data: { error: { code: "NOT_IMPLEMENTED" } } } };
      },
    }),
    getOrderStatus: builder.query({
      async queryFn() {
        return { data: null };
      },
    }),

    /* ================= Search ================= */

    // Autocomplete suggestions (Spec §6 storefront/search/suggest).
    // Backend cheklovi: `q` minLength=2, maxLength=100. 1 belgili so'rov 422
    // bersa ham, mijoz tarafda darhol bo'sh natija qaytaramiz.
    // Response: SearchSuggestionResponse[] = {type, text, slug, extra?}.
    // SearchOverlay UI faqat string label'larni renderlaydi, shuning uchun
    // transformResponse'da `text` ga proyeksiya + dedupe qilinadi.
    getSearchSuggestions: builder.query({
      query: (rawQuery) => {
        const q = typeof rawQuery === "string" ? rawQuery.trim() : "";
        const sp = new URLSearchParams();
        sp.set("q", q);
        sp.set("limit", "10");
        return `/api/v1/catalog/storefront/search/suggest?${sp.toString()}`;
      },
      transformResponse: (response) => {
        const items = Array.isArray(response) ? response : [];
        const seen = new Set();
        const out = [];
        for (const item of items) {
          const text = typeof item?.text === "string" ? item.text.trim() : "";
          if (!text) continue;
          const key = text.toLowerCase();
          if (seen.has(key)) continue;
          seen.add(key);
          out.push(text);
        }
        return out;
      },
      keepUnusedDataFor: 60,
    }),

    // Search history — Spec §6/§11: backend'da search-history endpoint'i
    // yo'q, shuning uchun mijoz `localStorage`'da saqlaydi
    // (`lib/search/history.js`). RTKQ shu storage ustidan thin layer:
    //  • `getSearchHistory`        — read + cross-tab live invalidation
    //  • `createSearchHistory`     — upsert (dedupe + searchedAt yangilanadi)
    //  • `removeSearchHistoryItem` — bitta entry'ni o'chirish
    //  • `clearSearchHistory`      — hammasi
    //
    // Optimistic updates'siz xulq qilamiz: queryFn deyarli sync (localStorage
    // read/write), shuning uchun tag-invalidation orqali refetch yetadi.
    // Cross-tab sinxronizatsiya `onCacheEntryAdded`'da `storage` event'iga
    // yoziladi.
    getSearchHistory: builder.query({
      async queryFn() {
        return { data: readSearchHistory() };
      },
      providesTags: ["SearchHistory"],
      // localStorage o'zi persistent — RTKQ cache faqat in-memory mirror.
      // Subscriber'siz qolganda 5 daqiqa saqlash (tezkor qayta ochish UX'i).
      keepUnusedDataFor: 300,
      async onCacheEntryAdded(
        _arg,
        { updateCachedData, cacheDataLoaded, cacheEntryRemoved },
      ) {
        try {
          await cacheDataLoaded;
        } catch {
          return;
        }
        const unsubscribe = subscribeSearchHistory(() => {
          updateCachedData(() => readSearchHistory());
        });
        try {
          await cacheEntryRemoved;
        } finally {
          unsubscribe();
        }
      },
    }),
    // Yozish operatsiyalari sinxron (localStorage). queryFn `addEntry` /
    // `removeEntry` / `clearHistory`'dan to'g'ridan-to'g'ri yangi ro'yxatni
    // qaytaradi va `onQueryStarted` orqali `getSearchHistory` cache'ga
    // yozadi. Refetch round-trip'siz UI darhol yangilanadi. `invalidatesTags`
    // qo'shimcha xavfsizlik kafolat — ehtimoliy boshqa subscriber'lar uchun.
    createSearchHistory: builder.mutation({
      async queryFn(payload) {
        const parameters =
          payload && typeof payload === "object" && payload.parameters != null
            ? payload.parameters
            : null;
        const next = addSearchHistoryEntry({
          query: payload?.query,
          parameters,
        });
        return { data: next };
      },
      async onQueryStarted(_payload, { dispatch, queryFulfilled }) {
        try {
          const { data } = await queryFulfilled;
          if (Array.isArray(data)) {
            dispatch(
              api.util.updateQueryData("getSearchHistory", undefined, () => data),
            );
          }
        } catch {
          // Storage write fail bo'lsa keyingi `getSearchHistory` o'qishi
          // realityni tiklaydi — patch.undo() kerak emas.
        }
      },
      invalidatesTags: ["SearchHistory"],
    }),
    removeSearchHistoryItem: builder.mutation({
      async queryFn(query) {
        const next = removeSearchHistoryEntry(query);
        return { data: next };
      },
      async onQueryStarted(_query, { dispatch, queryFulfilled }) {
        try {
          const { data } = await queryFulfilled;
          if (Array.isArray(data)) {
            dispatch(
              api.util.updateQueryData("getSearchHistory", undefined, () => data),
            );
          }
        } catch {
          // ignore — keyingi read storage'dan to'g'ri qiymat qaytaradi
        }
      },
      invalidatesTags: ["SearchHistory"],
    }),
    clearSearchHistory: builder.mutation({
      async queryFn() {
        clearSearchHistoryStorage();
        return { data: [] };
      },
      async onQueryStarted(_arg, { dispatch }) {
        // Sinxron operatsiya — queryFulfilled'ni kutmasdan darhol cache'ni
        // bo'shatamiz. queryFn baribir empty array qaytaradi.
        dispatch(
          api.util.updateQueryData("getSearchHistory", undefined, () => []),
        );
      },
      invalidatesTags: ["SearchHistory"],
    }),
  }),
});

export const {
  useGetMeQuery,
  useGetProductsQuery,
  useLazyGetProductsQuery,
  useGetProductByIdQuery,
  useGetSimilarProductsQuery,
  useGetAlsoViewedProductsQuery,
  useGetProductMediaQuery,
  useGetProductsByIdsQuery,
  useGetLatestProductsQuery,
  useGetLatestPurchasedProductsQuery,
  useGetForYouFeedQuery,
  useLazyGetForYouFeedQuery,
  useGetTrendingProductsQuery,
  useLazyGetTrendingProductsQuery,
  useGetCategoryTreeQuery,
  useGetCategoriesQuery,
  useCreateCategoryMutation,
  useDeleteCategoryMutation,
  useGetCategoriesWithTypesQuery,
  useGetTypesByCategoryQuery,
  useGetBrandsQuery,
  useSearchBrandsQuery,
  useGetBrandByIdQuery,
  useCreateBrandMutation,
  useDeleteBrandMutation,
  useUploadBrandLogoMutation,
  useDeleteBrandLogoMutation,
  useGetFavoritesQuery,
  useAddFavoriteMutation,
  useRemoveFavoriteMutation,
  useGetMyReferralLinkQuery,
  useGetMyInvitedUsersQuery,
  useGetMyActiveDiscountQuery,
  useGetMyReferralStatsQuery,
  useGetMyCartQuery,
  useGetCartSummaryQuery,
  useClearCartMutation,
  useAddCartItemMutation,
  useUpdateCartItemMutation,
  useRemoveCartItemMutation,
  useGetAnonymousCartTokenMutation,
  useMergeCartMutation,
  useInitiateCheckoutMutation,
  useConfirmCheckoutMutation,
  useCancelCheckoutMutation,
  useListPickupPointsQuery,
  useGetRateQuoteMutation,
  useListOrdersQuery,
  useGetOrderByIdQuery,
  useCreateOrderMutation,
  useUpdateOrderStatusMutation,
  useGetOrderStatusQuery,
  useGetSearchSuggestionsQuery,
  useGetSearchHistoryQuery,
  useCreateSearchHistoryMutation,
  useRemoveSearchHistoryItemMutation,
  useClearSearchHistoryMutation,
} = api;
