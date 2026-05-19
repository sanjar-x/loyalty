import { proxyToBackend } from '@/shared/api/bff';

// POST /api/catalog/attributes/{aid}/values/{vid}/activate
//
// Re-activate a previously deactivated value — restores publish
// eligibility for SKUs that reference it.
export const POST = proxyToBackend({
  method: 'POST',
  pathFn: ({ attributeId, valueId }) =>
    `/api/v1/admin/catalog/attributes/${attributeId}/values/${valueId}/activate`,
  forwardBody: false,
});
