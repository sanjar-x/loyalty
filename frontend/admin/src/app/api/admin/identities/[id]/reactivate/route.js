import { proxyToBackend } from '@/shared/api/bff';

export const POST = proxyToBackend({
  method: 'POST',
  pathFn: ({ id }) => `/api/v1/admin/identities/${id}/reactivate`,
  forwardBody: false,
});
