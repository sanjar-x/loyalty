/**
 * Sprint 2.2: moved out of shared/lib/url/backendAssets — business-bound
 * to brand logos. Generic `buildBackendAssetUrl` (used as fallback) stays
 * in shared.
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

export function buildBrandLogoUrl(filename) {
  const raw = typeof filename === 'string' ? filename.trim() : '';
  if (!raw) return '';

  // External URLs — use directly
  if (isHttpUrl(raw) && !isMainBackendUrl(raw)) return raw;

  const local = stripBackendOrigin(raw);

  // If already a routable path, use the generic asset proxy.
  const cleaned = local.replace(/^\/+/, '');
  if (/^(media|static|uploads|api)\//i.test(cleaned)) {
    return buildBackendAssetUrl(local);
  }

  const encoded = safeEncodePathParam(local);
  return encoded ? `/api/backend/api/v1/brands/logo/${encoded}` : '';
}
