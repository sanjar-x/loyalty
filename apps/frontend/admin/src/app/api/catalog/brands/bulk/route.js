import { proxyToBackend } from '@/shared/api/bff';

export const POST = proxyToBackend({
  method: 'POST',
  pathFn: () => '/api/v1/admin/catalog/brands/bulk',
  successStatus: 201,
});
