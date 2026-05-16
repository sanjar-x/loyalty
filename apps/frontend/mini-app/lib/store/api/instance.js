/**
 * RTK Query — yagona instance assembly.
 *
 * `enhancedApi` — domen-bo'yicha bo'lingan endpoint config'larni
 * (`./endpoints/*`) bitta `enhanceEndpoints` chaqiruviga spread qiladi.
 * `customApi` — codegen mos kelmaydigan qo'lda yozilgan endpointlar
 * (`injectEndpoints`). Ikkalasi ham bitta underlying api (reducerPath
 * "api") — `baseApi === generatedApi === enhancedApi === customApi`.
 *
 * Audit: frontend-main 2026-05-15 — `Audit - Mini App Architecture` P1 #6.
 */
import { baseApi } from '@/lib/store/baseApi';
import { generatedApi } from '@/lib/store/__generated__/api';
import {
  mapPickupPointsResponse,
  buildPickupPointsRequestBody,
} from '@/lib/adapters/mapPickupPoints';
import { mapStorefrontProduct, resolveI18N } from '@/lib/adapters/mapStorefrontProduct';
import {
  readHistory as readSearchHistory,
  addEntry as addSearchHistoryEntry,
  removeEntry as removeSearchHistoryEntry,
  clearHistory as clearSearchHistoryStorage,
  subscribe as subscribeSearchHistory,
} from '@/lib/search/history';

import { productEndpoints } from './endpoints/products';
import { taxonomyEndpoints } from './endpoints/taxonomy';
import { cartEndpoints } from './endpoints/cart';
import { orderEndpoints } from './endpoints/orders';
import { favoriteEndpoints } from './endpoints/favorites';

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

/* ──────────────────── Custom (qo'lda yozilgan) endpointlar ────────────────────
 *
 * Codegen mos kelmaydigan holatlar:
 *  1. Pickup-points: codegen POST'ni mutation deb belgilaydi, bizga query
 *     (cache bilan) kerak — har viewport panidan keyin natijani saqlaymiz.
 *  2. Search history: backend endpointi yo'q — localStorage ustidagi thin layer.
 *  3. Brand search: backend'da `?q=` yo'q — clientga filtr.
 *  4. getProductsByIds: bulk fetch (favorites/order details uchun).
 *  5. Rate quote: yangi schema admin path, eski signaturasi saqlanadi.
 *  6. checkFavoritedItems: backend POST'ni mutation deb beradi, lekin
 *     semantikasi read-only bulk check — query'ga cast qilamiz.
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
     * Bulk check qaysi target_id'lar caller tomonidan favorited bo'lganini.
     *
     * Backend `POST /api/v1/favorites/check` body:
     *   `{target_type: "product"|"brand", target_ids: string[] (UUID, 1..200)}`
     * Response:
     *   `{favorited: {[target_id]: list_id}}` — favorited bo'lgan id'lar
     *   uchun list_id; favorited bo'lmaganlar map'da yo'q.
     *
     * Cache key arg.{targetType, targetIds.sortlangan}. Frontend ids'larni
     * doim sortlab yuborishi cache hit'ni maksimal qiladi (turli render
     * tartibi bir cache'ni baham ko'radi).
     *
     * `Favorites` provideTag — `add`/`remove`/`move` mutation'lar bulk
     * cache'ni avtomatik invalidate qiladi (refetch + UI yangilanish).
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
      // Bo'sh `targetIds` bilan request yubormaslik — caller hookida
      // skip:true sifatida ishlatadi (RTKQ ichida ham ehtiyot:
      // empty array → empty object qaytaradi, lekin tarmoq ortiqcha).
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
    // Wire shape camelCase (REFACT-001). `serviceCode` ixtiyoriy:
    // null bo'lsa provider eng arzon tarifni qaytaradi; aniq qiymat
    // berilsa fallbackAlternatives toggle uchun aynan o'sha tarif.
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

// Legacy re-export — Redux store reducerPath="api" qoldiradi, store.js o'zgarmaydi.
export const api = enhancedApi;
export { enhancedApi, customApi };
