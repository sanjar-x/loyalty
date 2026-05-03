import { proxyToBackend } from '@/shared/api/bff';

export const GET = proxyToBackend({
  pathFn: () => '/api/v1/admin/roles',
});

export const POST = proxyToBackend({
  method: 'POST',
  pathFn: () => '/api/v1/admin/roles',
  successStatus: 201,
});
