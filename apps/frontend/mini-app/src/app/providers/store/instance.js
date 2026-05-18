/**
 * RTK Query — single-instance assembly.
 *
 * `enhancedApi` — spreads domain-split endpoint configs (`./endpoints/*`)
 * into one `enhanceEndpoints` call.
 * `customApi` — hand-written endpoints that codegen can't express
 * (`injectEndpoints`). Both share the same underlying api (reducerPath
 * "api") — `baseApi === generatedApi === enhancedApi === customApi`.
 *
 * Audit: frontend-main 2026-05-15 — `Audit - Mini App Architecture` P1 #6.
 */
import { baseApi } from '@/shared/api/base-api/baseApi';
import { generatedApi } from '@/shared/api/codegen/api';
import {
  mapPickupPointsResponse,
  buildPickupPointsRequestBody,
} from '@/entities/pickup-point/lib/mapPickupPoints';
import { mapStorefrontProduct } from '@/entities/product/lib/mapStorefrontProduct';
import { resolveI18N } from '@/shared/lib/i18n';
import {
  readHistory as readSearchHistory,
  addEntry as addSearchHistoryEntry,
  removeEntry as removeSearchHistoryEntry,
  clearHistory as clearSearchHistoryStorage,
  subscribe as subscribeSearchHistory,
} from '@/features/search/model/history';

// Sprint 3d: deep paths for endpoints (avoiding a cycle through the barrel,
// because entities/*/index.js now re-exports api/hooks that import
// enhancedApi from here).
import { productEndpoints } from '@/entities/product/api/products.endpoints';
import { taxonomyEndpoints } from '@/entities/category/api/taxonomy.endpoints';
import { cartEndpoints } from '@/entities/cart/api/cart.endpoints';
import { orderEndpoints } from '@/entities/order/api/orders.endpoints';
import { favoriteEndpoints } from '@/entities/favorite/api/favorites.endpoints';

const enhancedApi = generatedApi.enhanceEndpoints({
  addTagTypes: ['User', 'Cart', 'Orders', 'PVZ', 'Recipients'],
  endpoints: {
    ...productEndpoints,
    ...taxonomyEndpoints,
    ...cartEndpoints,
    ...orderEndpoints,
    ...favoriteEndpoints,
  },
});

/* ──────────────────── Custom (hand-written) endpoints ────────────────────
 *
 * Cases that codegen can't express:
 *  1. Pickup-points: codegen treats POST as a mutation, but we need a query
 *     (with cache) — we cache the result after each viewport pan.
 *  2. Search history: no backend endpoint — a thin layer over localStorage.
 *  3. Brand search: no `?q=` on the backend — client-side filter.
 *  4. getProductsByIds: bulk fetch (for favorites/order details).
 *  5. Rate quote: new schema's admin path, the old signature is preserved.
 *  6. checkFavoritedItems: backend exposes POST as a mutation, but the
 *     semantics is a read-only bulk check — we cast it to a query.
 */
const customApi = baseApi.injectEndpoints({
  endpoints: (build) => ({
    storefrontPickupPoints: build.query({
      query: (args) => ({
        url: '/api/v1/storefront/logistics/pickup-points',
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: buildPickupPointsRequestBody(args) ?? {},
      }),
      transformResponse: mapPickupPointsResponse,
      keepUnusedDataFor: 60,
      providesTags: ['PVZ'],
    }),

    getSearchHistory: build.query({
      async queryFn() {
        return { data: readSearchHistory() };
      },
      providesTags: ['SearchHistory'],
      keepUnusedDataFor: 300,
      async onCacheEntryAdded(_arg, { updateCachedData, cacheDataLoaded, cacheEntryRemoved }) {
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
    createSearchHistory: build.mutation({
      async queryFn(payload) {
        const parameters =
          payload && typeof payload === 'object' && payload.parameters != null
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
            dispatch(customApi.util.updateQueryData('getSearchHistory', undefined, () => data));
          }
        } catch {
          // ignore
        }
      },
      invalidatesTags: ['SearchHistory'],
    }),
    removeSearchHistoryItem: build.mutation({
      async queryFn(query) {
        const next = removeSearchHistoryEntry(query);
        return { data: next };
      },
      async onQueryStarted(_query, { dispatch, queryFulfilled }) {
        try {
          const { data } = await queryFulfilled;
          if (Array.isArray(data)) {
            dispatch(customApi.util.updateQueryData('getSearchHistory', undefined, () => data));
          }
        } catch {
          // ignore
        }
      },
      invalidatesTags: ['SearchHistory'],
    }),
    clearSearchHistory: build.mutation({
      async queryFn() {
        clearSearchHistoryStorage();
        return { data: [] };
      },
      async onQueryStarted(_arg, { dispatch }) {
        dispatch(customApi.util.updateQueryData('getSearchHistory', undefined, () => []));
      },
      invalidatesTags: ['SearchHistory'],
    }),

    /**
     * Bulk check of which target_ids are favorited by the caller.
     *
     * Backend `POST /api/v1/favorites/check` body:
     *   `{target_type: "product"|"brand", target_ids: string[] (UUID, 1..200)}`
     * Response:
     *   `{favorited: {[target_id]: list_id}}` — list_id for favorited ids;
     *   ids that aren't favorited are not present in the map.
     *
     * Cache key is arg.{targetType, sorted targetIds}. The frontend always
     * sorts ids before sending so cache hits are maximized (different
     * render orders share one cache).
     *
     * `Favorites` provideTag — `add`/`remove`/`move` mutations
     * automatically invalidate the bulk cache (refetch + UI update).
     */
    checkFavoritedItems: build.query({
      query: ({ targetType, targetIds }) => ({
        url: '/api/v1/favorites/check',
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: {
          target_type: targetType,
          target_ids: Array.isArray(targetIds) ? targetIds : [],
        },
      }),
      transformResponse: (resp) => {
        const m = resp?.favorited;
        return m && typeof m === 'object' ? m : {};
      },
      providesTags: (_r, _e, arg) => [
        'Favorites',
        { type: 'Favorites', id: `check-${arg?.targetType ?? 'all'}` },
      ],
      keepUnusedDataFor: 30,
      // Don't send a request with empty `targetIds` — the caller hook uses
      // skip:true (the RTKQ side is also defensive: an empty array → empty
      // object, but the network call would be wasteful).
    }),

    searchBrands: build.query({
      async queryFn({ q } = {}, _api, _extraOptions, baseQuery) {
        const res = await baseQuery({
          url: '/api/v1/storefront/brands',
          method: 'GET',
        });
        if (res?.error) return { error: res.error };
        const items = Array.isArray(res?.data?.items)
          ? res.data.items
          : Array.isArray(res?.data)
            ? res.data
            : [];
        const needle = String(q || '')
          .trim()
          .toLowerCase();
        const filtered = needle
          ? items.filter((b) => {
              const name = resolveI18N(b?.nameI18N, b?.name || '') ?? b?.name ?? '';
              return String(name).toLowerCase().includes(needle);
            })
          : items;
        return { data: filtered };
      },
      providesTags: ['Brands'],
    }),

    getProductsByIds: build.query({
      async queryFn(ids, _api, _extraOptions, baseQuery) {
        const raw = Array.isArray(ids) ? ids : [];
        const uniqueIds = Array.from(new Set(raw.map((x) => String(x)).filter((x) => x)));
        if (uniqueIds.length === 0) return { data: [] };

        const products = await Promise.all(
          uniqueIds.map(async (id) => {
            const r = await baseQuery({
              url: `/api/v1/storefront/products/${encodeURIComponent(id)}`,
              method: 'GET',
            });
            const data = r && typeof r === 'object' ? r.data : null;
            return data && typeof data === 'object' ? mapStorefrontProduct(data) : null;
          })
        );
        return { data: products.filter((p) => p && typeof p === 'object') };
      },
      providesTags: (result) => {
        if (!Array.isArray(result)) return ['Products'];
        return [
          'Products',
          ...result
            .map((p) => (p && typeof p === 'object' ? p.id : null))
            .filter((id) => id != null)
            .map((id) => ({ type: 'Product', id })),
        ];
      },
    }),

    // Rate quote — customer-facing storefront endpoint (CHK-024).
    // Wire shape camelCase (REFACT-001). `serviceCode` is optional:
    // if null, the provider returns the cheapest tariff; if an explicit
    // value is given, that exact tariff is used for the
    // fallbackAlternatives toggle.
    getRateQuote: build.mutation({
      query: ({ items, providerCode, pickupPointExternalId, serviceCode }) => ({
        url: '/api/v1/storefront/logistics/rates/quote',
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: {
          items: Array.isArray(items)
            ? items.map((it) => ({
                skuId: it?.skuId ?? it?.sku_id,
                quantity: Math.max(1, Math.floor(Number(it?.quantity || 1))),
              }))
            : [],
          providerCode,
          pickupPointExternalId,
          serviceCode: serviceCode ?? null,
        },
      }),
    }),
  }),
});

/* ──────────────────── Public re-exports ──────────────────── */

// Legacy re-export — keeps the Redux store reducerPath="api", store.js stays unchanged.
export const api = enhancedApi;
export { enhancedApi, customApi };
