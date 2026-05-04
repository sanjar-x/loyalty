import { proxyToBackend } from '@/shared/api/bff';

export const POST = proxyToBackend({
  method: 'POST',
  pathFn: ({ id }) => `/api/v1/admin/staff/${id}/reactivate`,
  forwardBody: false,
});
