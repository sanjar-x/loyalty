import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

import { isTokenExpiredError } from '@/shared/api/errors';
import { getAnonymousToken } from '@/shared/lib/anonymous-token';
import { readAuthStatus } from './authStatus';

// Sprint 3a: getAuthStatus is read through a DI seam (authStatus.js).
// features/auth-telegram registers its getter at init — no lazy
// `require()` or feature imports from shared.
const AUTH_STATUS_AUTHENTICATED = 'authenticated';

/**
 * Single RTKQ instance. `lib/store/api.js` (hand-written endpoints) and
 * `lib/store/__generated__/api.ts` (codegen) augment this instance via
 * `enhanceEndpoints` — in Redux they merge under a single `reducerPath: "api"`.
 *
 * Only the transport layer lives here:
 *  • Backend proxy (`/api/backend`) or direct NEXT_PUBLIC_API_BASE_URL
 *  • Anonymous-token header injection (only for /cart/*, excluding checkout/merge)
 *  • 401 → /api/auth/refresh → retry, with in-flight refresh deduplication
 *  • Auth-expiry event-bus dispatch
 *
 * No endpoint is declared here.
 */

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || '/api/backend';

// Spec §7: `X-Anonymous-Token` only for `/cart/*`, but `/cart/checkout*` and
// `/cart/merge` are excluded — checkout is authenticated-only, and merge itself
// accepts a Bearer plus the token in the body.
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
 * The codegen `query(queryArg) → { url, method, body }` callback drops custom
 * fields (`__idempotencyKey`) — they end up neither in the body nor in the
 * headers. Therefore we pass the key to baseQuery via a **side channel**: the
 * hook wrapper fills a module-level `Map<url, key>` before triggering the
 * call, and baseQuery reads it.
 *
 * The context is sequential — one checkout attempt at a time — so there is
 * no race risk. The map overwrites on override. On success
 * `clearPendingIdempotencyKey(url)` must be called.
 *
 * `withIdempotencyHeader(args)` is the defensive path for hand-written
 * endpoints — if `args.__idempotencyKey` is present, it is moved to the
 * headers. No call site currently uses it, but it is a fallback for any
 * endpoint added later via `injectEndpoints`.
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

// Concurrent 401s share a single refresh call
let refreshPromise = null;

const baseQuery = async (args, queryApi, extraOptions) => {
  const url = typeof args === 'string' ? args : args?.url;

  if (typeof url === 'string' && url.startsWith('/api/auth/')) {
    return appBaseQuery(args, queryApi, extraOptions);
  }

  const enrichedArgs = withIdempotencyHeader(withAnonymousTokenHeader(args, url));
  let result = await backendBaseQuery(enrichedArgs, queryApi, extraOptions);

  if (isTokenExpiredError(result?.error)) {
    const authStatus = readAuthStatus();
    if (authStatus && authStatus !== AUTH_STATUS_AUTHENTICATED) {
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
        const { emitAuthExpired } = await import('@/shared/lib/events');
        emitAuthExpired();
      } catch {
        // ignore
      }
    }
  }

  return result;
};

/**
 * Codegen and hand-written modules augment this instance via `injectEndpoints` /
 * `enhanceEndpoints`. Endpoints are **not declared here** — an empty
 * `endpoints: () => ({})` is left in place.
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
