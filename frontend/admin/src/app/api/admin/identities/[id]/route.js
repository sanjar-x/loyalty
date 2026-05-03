import { proxyToBackend } from '@/shared/api/bff';

export const GET = proxyToBackend({
  pathFn: ({ id }) => `/api/v1/admin/identities/${id}`,
});
