import { proxyToBackend } from '@/shared/api/bff';

export const GET = proxyToBackend({
  pathFn: ({ identityId }) => `/api/v1/admin/identities/${identityId}`,
});
