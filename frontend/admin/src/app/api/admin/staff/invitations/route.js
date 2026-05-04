import { proxyToBackend } from '@/shared/api/bff';

export const GET = proxyToBackend({
  pathFn: () => '/api/v1/admin/staff/invitations',
});

export const POST = proxyToBackend({
  method: 'POST',
  pathFn: () => '/api/v1/admin/staff/invitations',
  successStatus: 201,
});
