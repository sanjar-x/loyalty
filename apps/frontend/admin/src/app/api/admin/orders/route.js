import { proxyToBackend } from '@/shared/api/bff';

// GET /api/admin/orders → /api/v1/admin/orders
//
// Backend honours `statuses` (multi-value), `limit` (≤200), `cursor` (ISO
// datetime). Anything else gets dropped by `allowedParams`.
export const GET = proxyToBackend({
  pathFn: () => '/api/v1/admin/orders',
  allowedParams: ['statuses', 'limit', 'cursor'],
});

// POST /api/admin/orders → /api/v1/admin/orders
//
// Walk-in order creation. Body is forwarded verbatim (camelCase per
// REFACT-001 wire contract) — the schema is `AdminCreateWalkInOrderRequest`
// and includes idempotencyKey, so retrying with the same key is safe.
// proxyToBackend applies CSRF check + Bearer auth by default for non-safe
// methods. successStatus locks 201 so a transient backend 200 (shouldn't
// happen, but be defensive) still presents as the documented Created.
export const POST = proxyToBackend({
  method: 'POST',
  pathFn: () => '/api/v1/admin/orders',
  successStatus: 201,
});
