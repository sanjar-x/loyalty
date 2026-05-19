import { proxyToBackend } from '@/shared/api/bff';

// GET /api/storefront/search → /api/v1/storefront/search
//
// Proxies the customer-facing full-text product search so the walk-in
// order form can find products by name. The backend storefront endpoint
// only returns PUBLISHED products, which is exactly the gate we want
// here — admin should never be able to assemble a walk-in order against
// draft / enriching SKUs.
//
// `requireAuth: false` because the storefront endpoint is anonymous, but
// the Edge proxy (`src/proxy.js`) still gates /api/* on a valid access
// token, so this route is reachable only from an authenticated admin
// session.
//
// `allowedParams` mirrors the OpenAPI schema verbatim (no `cursor` pass-
// through gymnastics needed — backend accepts it as-is).
export const GET = proxyToBackend({
  pathFn: () => '/api/v1/storefront/search',
  requireAuth: false,
  allowedParams: [
    'q',
    'categoryId',
    'brandId',
    'priceMin',
    'priceMax',
    'sortBy',
    'limit',
    'cursor',
  ],
});
