import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

import { isTokenExpiredError } from '@/lib/api/errors';
import { getAnonymousToken } from '@/lib/cart/anonymousToken';
import { useAuthStore } from '@/lib/features/auth/store';
import { AuthStatus } from '@/lib/features/auth/types';

/**
 * Yagona RTKQ instansi. `lib/store/api.js` (qo'lda yozilgan endpointlar) va
 * `lib/store/__generated__/api.ts` (codegen) shu instansni `enhanceEndpoints`
 * orqali bo'yib ishlatadi — Redux'da bitta `reducerPath: "api"` ostida birlashadi.
 *
 * Bu yerda faqat transport-darajasi yashaydi:
 *  • Backend proxy (`/api/backend`) yoki to'g'ridan-to'g'ri NEXT_PUBLIC_API_BASE_URL
 *  • Anonymous-token header injection (faqat /cart/* uchun, checkout/merge'dan tashqari)
 *  • 401 → /api/auth/refresh → retry, in-flight refresh deduplikatsiyasi bilan
 *  • Auth expiry event-bus chaqiruvi
 *
 * Endpoint'larning hech biri bu yerda e'lon qilinmaydi.
 */

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || '/api/backend';

// Spec §7: `X-Anonymous-Token` faqat `/cart/*` uchun, lekin `/cart/checkout*`
// va `/cart/merge` chiqarib tashlangan — checkout faqat authenticated, merge
// esa Bearer + body'dagi token'ni o'zi qabul qiladi.
function shouldAttachAnonymousToken(url) {
  if (typeof url !== 'string') return false;
  if (!url.includes('/api/v1/cart')) return false;
  if (url.includes('/cart/checkout')) return false;
  if (url.includes('/cart/merge')) return false;
  if (url.includes('/cart/anonymous-token')) return false;
  return true;
}

function withAnonymousTokenHeader(args, url) {
  if (!shouldAttachAnonymousToken(url)) return args;
  const token = getAnonymousToken();
  if (!token) return args;

  const obj = typeof args === 'string' ? { url: args } : { ...args };
  obj.headers = { ...(obj.headers || {}), 'x-anonymous-token': token };
  return obj;
}

/**
 * CHK-006: Idempotency-Key passthrough.
 *
 * Codegen `query(queryArg) → { url, method, body }` callback'i custom
 * field'larni (`__idempotencyKey`) ehtimoldan o'tkazib yuboradi — body'ga
 * ham, header'ga ham kirmaydi. Shuning uchun key'ni baseQuery'ga
 * **yon-kanal** orqali uzatamiz: modul-level `Map<url, key>` ni hook
 * wrapper trigger chaqirishdan oldin to'ldiradi va baseQuery o'qiydi.
 *
 * Kontekst sequential — bir vaqtda bitta checkout attempt — shuning uchun
 * race xavfi yo'q. Map override'da overwrite. Success'da
 * `clearPendingIdempotencyKey(url)` chaqirilishi kerak.
 *
 * `withIdempotencyHeader(args)` esa qo'lda yozilgan endpointlar uchun
 * defensive — `args.__idempotencyKey` bo'lsa, header'ga ko'chiradi.
 * Hozircha hech qanday call site ishlatmaydi, lekin re-yoki keyin
 * `injectEndpoints` orqali qo'shilgan endpoint uchun zaxira.
 */
const pendingIdempotencyKeys = new Map();

export function setPendingIdempotencyKey(url, key) {
  if (typeof url !== 'string' || !url) return;
  if (typeof key !== 'string' || !key) {
    pendingIdempotencyKeys.delete(url);
    return;
  }
  pendingIdempotencyKeys.set(url, key);
}

export function clearPendingIdempotencyKey(url) {
  if (typeof url !== 'string' || !url) return;
  pendingIdempotencyKeys.delete(url);
}

function withIdempotencyFromRegistry(args) {
  if (!args || typeof args !== 'object') return args;
  const url = args.url;
  if (typeof url !== 'string') return args;
  const key = pendingIdempotencyKeys.get(url);
  if (!key) return args;
  return {
    ...args,
    headers: { ...(args.headers || {}), 'idempotency-key': key },
  };
}

function withIdempotencyHeader(args) {
  if (!args || typeof args !== 'object') return args;
  const key = args.__idempotencyKey;
  if (!key || typeof key !== 'string') return withIdempotencyFromRegistry(args);
  const { __idempotencyKey, ...rest } = args;
  void __idempotencyKey;
  return {
    ...rest,
    headers: { ...(rest.headers || {}), 'idempotency-key': key },
  };
}

const backendBaseQuery = fetchBaseQuery({
  baseUrl,
  credentials: 'include',
});

const appBaseQuery = fetchBaseQuery({
  baseUrl: '',
  credentials: 'include',
});

// Concurrent 401'lar bitta refresh chaqiruvini bo'lishadi
let refreshPromise = null;

const baseQuery = async (args, queryApi, extraOptions) => {
  const url = typeof args === 'string' ? args : args?.url;

  if (typeof url === 'string' && url.startsWith('/api/auth/')) {
    return appBaseQuery(args, queryApi, extraOptions);
  }

  const enrichedArgs = withIdempotencyHeader(withAnonymousTokenHeader(args, url));
  let result = await backendBaseQuery(enrichedArgs, queryApi, extraOptions);

  if (isTokenExpiredError(result?.error)) {
    const authStatus = useAuthStore.getState().status;
    if (authStatus !== AuthStatus.AUTHENTICATED) {
      return result;
    }

    if (!refreshPromise) {
      refreshPromise = appBaseQuery(
        { url: '/api/auth/refresh', method: 'POST' },
        queryApi,
        extraOptions
      ).finally(() => {
        setTimeout(() => {
          refreshPromise = null;
        }, 0);
      });
    }

    const refreshResult = await refreshPromise;

    if (refreshResult?.data?.ok) {
      result = await backendBaseQuery(enrichedArgs, queryApi, extraOptions);
    } else {
      try {
        const { emitAuthExpired } = await import('@/lib/auth-events');
        emitAuthExpired();
      } catch {
        // ignore
      }
    }
  }

  return result;
};

/**
 * Codegen va qo'lda yozilgan modullar shu instansni `injectEndpoints` /
 * `enhanceEndpoints` orqali to'ldiradi. Endpointlar **bu yerda e'lon
 * qilinmaydi** — bo'sh `endpoints: () => ({})` qoldirilgan.
 */
export const baseApi = createApi({
  reducerPath: 'api',
  baseQuery,
  tagTypes: [
    'User',
    'Products',
    'Product',
    'ForYouFeed',
    'Trending',
    'Categories',
    'CategoryTree',
    'Types',
    'Brands',
    'Favorites',
    'Cart',
    'Orders',
    'Payments',
    'Shipments',
    'Recipients',
    'Referrals',
    'PVZ',
    'SearchHistory',
  ],
  endpoints: () => ({}),
});
