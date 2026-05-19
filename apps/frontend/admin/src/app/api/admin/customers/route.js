import { proxyToBackend } from '@/shared/api/bff';

export const GET = proxyToBackend({
  pathFn: () => '/api/v1/admin/customers',
});
