function isHttpUrl(value) {
  return typeof value === 'string' && /^https?:\/\//i.test(value.trim());
}

// Main backend origin — only strip this when proxying
const MAIN_BACKEND_HOSTNAME = 'backend-production-43b6.up.railway.app';

/**
 * Check if a full URL belongs to the main backend (should be proxied).
 * Any other full URL (e.g. image-backend) is returned as-is.
 */
function isMainBackendUrl(value) {
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
function stripBackendOrigin(value) {
  if (!isHttpUrl(value)) return value;
  if (!isMainBackendUrl(value)) return value; // external URL — keep as-is
  try {
    const u = new URL(value.trim());
    return u.pathname;
  } catch {
    return value;
  }
}

function safeEncodePathParam(value) {
  const raw = typeof value === 'string' ? value.trim() : '';
  if (!raw) return '';

  const cleaned = raw.replace(/^\/+/, '');

  // If backend already returns an encoded string, avoid double-encoding.
  if (/%[0-9A-Fa-f]{2}/.test(cleaned)) return cleaned;

  return encodeURIComponent(cleaned);
}

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
      // Decode first to avoid double-encoding already-escaped segments
      // (e.g. "1%2Ffile.png" should stay as one segment, not become "1%252Ffile.png").
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
