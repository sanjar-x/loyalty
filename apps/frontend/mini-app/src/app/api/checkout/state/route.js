import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

import { getBackendBaseUrl } from '@/shared/api/bff';

/**
 * GET /api/checkout/state
 *
 * Returns the user's current state on the checkout page as a single JSON.
 * This is a plain JSON API instead of a Next.js RSC flight stream (which
 * comes with `?_rsc=...` query): suitable for external tools (curl,
 * Postman, Telegram bot).
 *
 * Sources:
 *  • Backend cart            — `GET /api/v1/cart` (canonical)
 *  • Anonymous-token (guests)— `X-Anonymous-Token` header
 *  • Bearer token            — `lm_access_token` cookie (BFF pattern)
 *
 * Selection / pickup / quote / recipient / customs / promo state is stored
 * on the client (Zustand `sessionStorage`) and does not exist on the
 * server, so this endpoint returns only **cart + auth + freeze status**
 * on the **server side**. Additional client-side state can also be sent
 * in the request as a JSON body (POST variant).
 *
 * Response shape (camelCase, Spec §1):
 * ```json
 * {
 *   "isAuthenticated": true,
 *   "cart": {
 *     "id": "uuid",
 *     "status": "active|frozen|ordered|cleared",
 *     "itemCount": 3,
 *     "totalAmount": 1599800,
 *     "currency": "RUB",
 *     "groups": [
 *       {
 *         "supplierType": "cross_border",
 *         "subtotal": { "amount": 599800, "currency": "RUB" },
 *         "items": [{ "id, "skuId", "productName", "quantity", "unitPrice", ... }]
 *       }
 *     ],
 *     "createdAt": "...",
 *     "updatedAt": "..."
 *   },
 *   "anonymous": false,
 *   "fetchedAt": "2026-04-28T19:00:00.000Z"
 * }
 * ```
 *
 * Errors (aligned with RFC 7807):
 *   401 — no auth and no anonymous token
 *   502 — backend unreachable (when the BFF proxy fails)
 */

const ACCESS_COOKIE = 'lm_access_token';

export async function GET(req) {
  let backendBase;
  try {
    backendBase = getBackendBaseUrl();
  } catch (e) {
    return NextResponse.json({ error: { code: 'CONFIG', message: e.message } }, { status: 500 });
  }

  // Auth: Bearer from cookie, or anonymous-token header
  let bearer = '';
  try {
    const jar = await cookies();
    bearer = jar.get(ACCESS_COOKIE)?.value || '';
  } catch (e) {
    console.error('[checkout/state] cookies() threw', { error: e?.message });
    bearer = '';
  }
  const anonToken = req.headers.get('x-anonymous-token') || '';

  if (!bearer && !anonToken) {
    return NextResponse.json(
      {
        error: {
          code: 'MISSING_TOKEN',
          message: 'Authentication or anonymous-token required',
        },
      },
      { status: 401 }
    );
  }

  // Cart fetch
  const upstreamHeaders = new Headers({ accept: 'application/json' });
  if (bearer) upstreamHeaders.set('authorization', `Bearer ${bearer}`);
  if (anonToken) upstreamHeaders.set('x-anonymous-token', anonToken);

  // Request tracing
  const reqId =
    req.headers.get('x-request-id') ||
    (typeof crypto?.randomUUID === 'function' ? crypto.randomUUID() : '');
  if (reqId) upstreamHeaders.set('x-request-id', reqId);

  let cartRes;
  try {
    cartRes = await fetch(`${backendBase}/api/v1/cart`, {
      method: 'GET',
      headers: upstreamHeaders,
      // 10s timeout
      signal: AbortSignal.timeout(10_000),
    });
  } catch (e) {
    return NextResponse.json(
      {
        error: {
          code: 'UPSTREAM_UNAVAILABLE',
          message: e?.name === 'TimeoutError' ? 'Backend timeout' : 'Backend unreachable',
          requestId: reqId,
        },
      },
      { status: 502 }
    );
  }

  if (!cartRes.ok) {
    let upstreamBody = null;
    try {
      upstreamBody = await cartRes.json();
    } catch {
      upstreamBody = null;
    }
    return NextResponse.json(
      {
        error: {
          code: upstreamBody?.error?.code || 'UPSTREAM_ERROR',
          message: upstreamBody?.error?.message || `Backend ${cartRes.status}`,
          status: cartRes.status,
          requestId: reqId,
        },
      },
      { status: cartRes.status === 401 ? 401 : 502 }
    );
  }

  let cart;
  try {
    cart = await cartRes.json();
  } catch {
    return NextResponse.json(
      {
        error: { code: 'PARSE_ERROR', message: 'Invalid cart JSON', requestId: reqId },
      },
      { status: 502 }
    );
  }

  // Keep Money in JSON shape (kopecks) for the client. Formatting happens
  // on the client side — similar to `mapStorefrontProduct`/`useCart`.
  const totalAmount = cart?.total?.amount ?? 0;
  const currency = cart?.total?.currency ?? 'RUB';

  return NextResponse.json(
    {
      isAuthenticated: Boolean(bearer),
      anonymous: !bearer && Boolean(anonToken),
      cart: {
        id: cart?.id ?? null,
        status: cart?.status ?? 'empty',
        itemCount: cart?.itemCount ?? 0,
        totalAmount,
        currency,
        groups: Array.isArray(cart?.groups) ? cart.groups : [],
        createdAt: cart?.createdAt ?? null,
        updatedAt: cart?.updatedAt ?? null,
      },
      fetchedAt: new Date().toISOString(),
      requestId: reqId,
    },
    {
      status: 200,
      headers: {
        'cache-control': 'no-store',
        ...(reqId ? { 'x-request-id': reqId } : {}),
      },
    }
  );
}
