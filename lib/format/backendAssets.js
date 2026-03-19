function isHttpUrl(value) {
  return typeof value === "string" && /^https?:\/\//i.test(value.trim());
}

function safeEncodePathParam(value) {
  const raw = typeof value === "string" ? value.trim() : "";
  if (!raw) return "";

  const cleaned = raw.replace(/^\/+/, "");

  // If backend already returns an encoded string, avoid double-encoding.
  if (/%[0-9A-Fa-f]{2}/.test(cleaned)) return cleaned;

  return encodeURIComponent(cleaned);
}

export function buildBackendAssetUrl(path, prefixSegments = []) {
  const raw = typeof path === "string" ? path.trim() : "";
  if (!raw) return "";
  if (isHttpUrl(raw)) return raw;

  const cleaned = raw.replace(/^\/+/, "");
  const encoded = cleaned
    .split("/")
    .map((p) => encodeURIComponent(p))
    .join("/");

  const prefix =
    Array.isArray(prefixSegments) && prefixSegments.length
      ? `${prefixSegments.map((s) => encodeURIComponent(String(s))).join("/")}/`
      : "";

  return `/api/backend/${prefix}${encoded}`;
}

export function buildProductPhotoUrl(filename) {
  const raw = typeof filename === "string" ? filename.trim() : "";
  if (!raw) return "";
  if (isHttpUrl(raw)) return raw;

  const encoded = safeEncodePathParam(raw);
  return encoded ? `/api/backend/api/v1/products/get_photo/${encoded}` : "";
}

export function buildBrandLogoUrl(filename) {
  const raw = typeof filename === "string" ? filename.trim() : "";
  if (!raw) return "";
  if (isHttpUrl(raw)) return raw;

  const encoded = safeEncodePathParam(raw);
  return encoded ? `/api/backend/api/v1/brands/logo/${encoded}` : "";
}
