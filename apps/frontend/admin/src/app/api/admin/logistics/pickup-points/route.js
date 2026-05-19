import { proxyToBackend } from '@/shared/api/bff';

// POST /api/admin/logistics/pickup-points → /api/v1/admin/logistics/pickup-points
//
// Powers the ChangePickupPointModal search. Request body matches
// `PickupPointsRequest` (city/lat-lng/providerCode/deliveryType).
export const POST = proxyToBackend({
  method: 'POST',
  pathFn: () => '/api/v1/admin/logistics/pickup-points',
});
