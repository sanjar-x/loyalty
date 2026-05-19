import { proxyToBackend } from '@/shared/api/bff';

export const POST = proxyToBackend({
  method: 'POST',
  pathFn: ({ identityId }) => `/api/v1/admin/identities/${identityId}/roles`,
  successStatus: 201,
});
