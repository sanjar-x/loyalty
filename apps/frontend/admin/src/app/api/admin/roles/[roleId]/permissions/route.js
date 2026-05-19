import { proxyToBackend } from '@/shared/api/bff';

export const PUT = proxyToBackend({
  method: 'PUT',
  pathFn: ({ roleId }) => `/api/v1/admin/roles/${roleId}/permissions`,
});
