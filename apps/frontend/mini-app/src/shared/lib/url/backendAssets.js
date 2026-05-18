/**
 * Generic backend asset proxy URL builders. Sprint 2.2: business-specific
 * builders (buildProductPhotoUrl, buildBrandLogoUrl) moved into their own
 * entities — entities/product/lib/photoUrl.js, entities/brand/lib/logoUrl.js.
 */

function isHttpUrl(value) {
  return typeof value === 'string' && /^https?:\/\//i.test(value.trim());
}

// Main backend origin — only strip this when proxying
const MAIN_BACKEND_HOSTNAME = 'backend-production-43b6.up.railway.app';

/**
 * Check if a full URL belongs to the main backend (should be proxied).
 * Any other full URL (e.g. image-backend) is returned as-is.
 */
export function isMainBackendUrl(value) {
  if (!isHttpUrl(value)) return false;
  try {
    const u = new URL(value.trim());
    return u.hostname === MAIN_BACKEND_HOSTNAME;
  } catch {
    return false;
  }
}

/**
 * If the value is a full HTTP URL from the main backend, strip the
 * origin and return only the pathname so we can route it through the local
 * `/api/backend` proxy. External image URLs are left untouched.
 */
export function stripBackendOrigin(value) {
  if (!isHttpUrl(value)) return value;
  if (!isMainBackendUrl(value)) return value;
  try {
    const u = new URL(value.trim());
    return u.pathname;
  } catch {
    return value;
  }
}

export function safeEncodePathParam(value) {
  const raw = typeof value === 'string' ? value.trim() : '';
  if (!raw) return '';

  const cleaned = raw.replace(/^\/+/, '');

  // If backend already returns an encoded string, avoid double-encoding.
  if (/%[0-9A-Fa-f]{2}/.test(cleaned)) return cleaned;

  return encodeURIComponent(cleaned);
}

export { isHttpUrl };

export function buildBackendAssetUrl(path, prefixSegments = []) {
  const raw = typeof path === 'string' ? path.trim() : '';
  if (!raw) return '';

  // External URLs (e.g. image-backend) — use directly, don't proxy
  if (isHttpUrl(raw) && !isMainBackendUrl(raw)) return raw;

  // Rewrite main-backend URLs to go through the proxy
  const local = stripBackendOrigin(raw);

  const cleaned = local.replace(/^\/+/, '');
  const encoded = cleaned
    .split('/')
    .map((p) => {
      try {
        return encodeURIComponent(decodeURIComponent(p));
      } catch {
        return encodeURIComponent(p);
      }
    })
    .join('/');

  const prefix =
    Array.isArray(prefixSegments) && prefixSegments.length
      ? `${prefixSegments.map((s) => encodeURIComponent(String(s))).join('/')}/`
      : '';

  return `/api/backend/${prefix}${encoded}`;
}
