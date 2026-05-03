import { proxyToBackend } from '@/shared/api/bff';

export const PUT = proxyToBackend({
  method: 'PUT',
  pathFn: ({ id }) => `/api/v1/admin/roles/${id}/permissions`,
});
