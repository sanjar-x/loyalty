import { proxyToBackend } from '@/shared/api/bff';

// POST /api/catalog/attributes/{aid}/values/reorder
//
// Bulk-reorder up to 500 values in one round-trip. Frontend computes
// the new sortOrder array (typically after a DnD swap) and sends a
// list of `{valueId, sortOrder}` pairs.
export const POST = proxyToBackend({
  method: 'POST',
  pathFn: ({ attributeId }) =>
    `/api/v1/admin/catalog/attributes/${attributeId}/values/reorder`,
});
