/**
 * Sprint 2.2: moved out of shared/lib/url/backendAssets — business-bound
 * to product photos. Generic `buildBackendAssetUrl` (used as fallback)
 * stays in shared.
 */

import {
  buildBackendAssetUrl,
  isMainBackendUrl,
  safeEncodePathParam,
  stripBackendOrigin,
} from '@/shared/lib/url/backendAssets';

function isHttpUrl(value) {
  return typeof value === 'string' && /^https?:\/\//i.test(value.trim());
}

export function buildProductPhotoUrl(filename) {
  const raw = typeof filename === 'string' ? filename.trim() : '';
  if (!raw) return '';

  // External URLs (e.g. image-backend) — use directly
  if (isHttpUrl(raw) && !isMainBackendUrl(raw)) return raw;

  // Main-backend full URL → strip origin and proxy
  const local = stripBackendOrigin(raw);

  // If the value (after stripping backend origin) is already a routable path
  // (e.g. "/media/photos/1/file.jpg" or "/api/v1/..."), route it through the
  // generic asset proxy instead of wrapping it with the get_photo/ prefix.
  const cleaned = local.replace(/^\/+/, '');
  if (/^(media|static|uploads|api)\//i.test(cleaned)) {
    return buildBackendAssetUrl(local);
  }

  const encoded = safeEncodePathParam(local);
  return encoded ? `/api/backend/api/v1/products/get_photo/${encoded}` : '';
}
