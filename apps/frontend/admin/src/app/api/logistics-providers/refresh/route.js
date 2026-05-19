import { proxyToBackend } from '@/shared/api/bff';

// POST /api/logistics-providers/refresh → rebuild the in-memory provider
// registry on the worker that serves this request. Called automatically
// after every provider-account mutation — the running backend otherwise
// keeps the registry it built at process start. Static `refresh` segment
// takes routing precedence over the sibling `[id]` route.
export const POST = proxyToBackend({
  method: 'POST',
  pathFn: () => '/api/v1/admin/logistics/provider-accounts/refresh',
});
