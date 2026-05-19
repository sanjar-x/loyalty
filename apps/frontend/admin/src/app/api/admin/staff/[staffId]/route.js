import { proxyToBackend } from '@/shared/api/bff';

export const GET = proxyToBackend({
  pathFn: ({ staffId }) => `/api/v1/admin/staff/${staffId}`,
});
