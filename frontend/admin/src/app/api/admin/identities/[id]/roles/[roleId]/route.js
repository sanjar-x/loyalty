import { proxyToBackend } from '@/shared/api/bff';

export const DELETE = proxyToBackend({
  method: 'DELETE',
  pathFn: ({ id, roleId }) => `/api/v1/admin/identities/${id}/roles/${roleId}`,
});
