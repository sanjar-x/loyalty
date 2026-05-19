import { proxyToBackend } from '@/shared/api/bff';

export const DELETE = proxyToBackend({
  method: 'DELETE',
  pathFn: ({ invitationId }) =>
    `/api/v1/admin/staff/invitations/${invitationId}`,
});
