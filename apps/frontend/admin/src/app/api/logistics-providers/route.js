import { proxyToBackend } from '@/shared/api/bff';

// GET  /api/logistics-providers  → list logistics provider accounts
// POST /api/logistics-providers  → create a provider account
//
// Backend: /api/v1/admin/logistics/provider-accounts (permission
// `logistics:admin`). Query params are forwarded verbatim — the logistics
// module serialises camelCase since the API-wide unification, so
// `providerCode` / `onlyActive` pass straight through.
const BACKEND_PATH = '/api/v1/admin/logistics/provider-accounts';

export const GET = proxyToBackend({
  pathFn: () => BACKEND_PATH,
  allowedParams: ['providerCode', 'onlyActive'],
});

export const POST = proxyToBackend({
  method: 'POST',
  pathFn: () => BACKEND_PATH,
  successStatus: 201,
});
