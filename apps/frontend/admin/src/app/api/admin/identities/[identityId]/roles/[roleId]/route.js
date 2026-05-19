import { proxyToBackend } from '@/shared/api/bff';

export const DELETE = proxyToBackend({
  method: 'DELETE',
  pathFn: ({ identityId, roleId }) =>
    `/api/v1/admin/identities/${identityId}/roles/${roleId}`,
});
