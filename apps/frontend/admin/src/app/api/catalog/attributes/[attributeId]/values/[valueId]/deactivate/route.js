import { proxyToBackend } from '@/shared/api/bff';

// POST /api/catalog/attributes/{aid}/values/{vid}/deactivate
//
// Soft-deactivate an attribute value. SKUs that already reference the
// value stay alive but cannot be republished until the value is
// reactivated — backend enforces this on the publish FSM gate.
export const POST = proxyToBackend({
  method: 'POST',
  pathFn: ({ attributeId, valueId }) =>
    `/api/v1/admin/catalog/attributes/${attributeId}/values/${valueId}/deactivate`,
  forwardBody: false,
});
