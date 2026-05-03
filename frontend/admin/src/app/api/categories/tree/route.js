import { proxyToBackend } from '@/shared/api/bff';

// Categories tree may resolve without an access token (used in pre-auth
// contexts), so requireAuth=false: the Bearer is still attached when one
// is available, but a missing token doesn't 401.
export const GET = proxyToBackend({
  pathFn: () => '/api/v1/admin/catalog/categories/tree',
  requireAuth: false,
});
