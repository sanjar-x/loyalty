import { proxyToBackend } from '@/shared/api/bff';

export const GET = proxyToBackend({
  pathFn: ({ productId }) =>
    `/api/v1/admin/catalog/products/${productId}/completeness`,
  responseHeaders: { 'Cache-Control': 'no-store' },
});
