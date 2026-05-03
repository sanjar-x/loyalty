import { proxyToBackend } from '@/shared/api/bff';

export const GET = proxyToBackend({
  pathFn: () => '/api/v1/admin/pricing/contexts',
  allowedParams: ['is_active', 'is_frozen'],
});

export const POST = proxyToBackend({
  method: 'POST',
  pathFn: () => '/api/v1/admin/pricing/contexts',
  successStatus: 201,
});
