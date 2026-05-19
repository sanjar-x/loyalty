import { proxyToBackend } from '@/shared/api/bff';

// GET /api/admin/orders/meta/cancellation-reasons
//   → /api/v1/admin/orders/_meta/cancellation-reasons
//
// Frontend folder is `meta/` (not `_meta/`) because Next.js App Router
// opts underscore-prefixed folders out of routing entirely — a
// `_meta/` folder here would silently 404. Backend keeps `_meta` in its
// own URL, the BFF just bridges the rename.
//
// Static taxonomy fetched once per session by `useCancellationReasons`
// and cached with a 30-minute staleTime. Powers the grouped dropdown in
// ForceCancelModal so the 19 reasons stay backend-driven instead of
// hard-coded on the frontend.
export const GET = proxyToBackend({
  pathFn: () => '/api/v1/admin/orders/_meta/cancellation-reasons',
  responseHeaders: { 'Cache-Control': 'private, max-age=900' },
});
