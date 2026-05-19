import { proxyToBackend } from '@/shared/api/bff';

// POST /api/catalog/attributes/bulk → /api/v1/admin/catalog/attributes/bulk
//
// Backend accepts up to 100 attributes per call with `skipExisting` flag.
// We forward the body verbatim — payload shaping happens in the modal.
export const POST = proxyToBackend({
  method: 'POST',
  pathFn: () => '/api/v1/admin/catalog/attributes/bulk',
  successStatus: 201,
});
