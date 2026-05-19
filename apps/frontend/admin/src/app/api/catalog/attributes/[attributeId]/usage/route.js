import { proxyToBackend } from '@/shared/api/bff';

// GET /api/catalog/attributes/{id}/usage → /api/v1/admin/catalog/attributes/{id}/usage
//
// Read-only analytics — returns where the attribute is wired (templates,
// categories, product count). Used by the delete-confirm modal so the
// admin sees the blast radius before clicking through.
export const GET = proxyToBackend({
  pathFn: ({ attributeId }) =>
    `/api/v1/admin/catalog/attributes/${attributeId}/usage`,
  responseHeaders: { 'Cache-Control': 'no-store' },
});
