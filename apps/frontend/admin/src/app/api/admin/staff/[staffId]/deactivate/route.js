import { proxyToBackend } from '@/shared/api/bff';

export const POST = proxyToBackend({
  method: 'POST',
  pathFn: ({ staffId }) => `/api/v1/admin/staff/${staffId}/deactivate`,
});
