import { proxyToBackend } from '@/shared/api/bff';

// POST /api/logistics-providers/{providerId}/active → activate / deactivate.
// Body: { isActive: boolean }. Backend rejects a second active account for
// the same providerCode with 409 CONFLICT.
export const POST = proxyToBackend({
  method: 'POST',
  pathFn: (params) =>
    `/api/v1/admin/logistics/provider-accounts/${params.providerId}/active`,
});
