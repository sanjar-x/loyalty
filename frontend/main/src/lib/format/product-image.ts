interface ProductLike {
  image?: string;
  image_url?: string;
  photo?: string;
  photo_url?: string;
  photos?: Array<string | { filename?: string; file?: string; path?: string; url?: string }>;
}

function isHttpUrl(value: string): boolean {
  return /^https?:\/\//i.test(value.trim());
}

function safeEncodePathParam(value: string): string {
  const raw = value.trim();
  if (!raw) return "";
  const cleaned = raw.replace(/^\/+/, "");
  if (/%[0-9A-Fa-f]{2}/.test(cleaned)) return cleaned;
  return encodeURIComponent(cleaned);
}

export function buildProductPhotoUrl(filename: string): string {
  const raw = filename.trim();
  if (!raw) return "";
  if (isHttpUrl(raw)) return raw;
  const encoded = safeEncodePathParam(raw);
  return encoded ? `/api/backend/api/v1/products/get_photo/${encoded}` : "";
}

export function buildBackendAssetUrl(
  path: string,
  prefixSegments: string[] = [],
): string {
  const raw = path.trim();
  if (!raw) return "";
  if (isHttpUrl(raw)) return raw;
  const cleaned = raw.replace(/^\/+/, "");
  const encoded = cleaned
    .split("/")
    .map((p) => encodeURIComponent(p))
    .join("/");
  const prefix = prefixSegments.length
    ? `${prefixSegments.map((s) => encodeURIComponent(s)).join("/")}/`
    : "";
  return `/api/backend/${prefix}${encoded}`;
}

/**
 * Build a prioritized list of image URL candidates for a product.
 * Tries direct fields first, then constructs proxy URLs from photos array.
 */
export function getProductPhotoCandidates(
  product: ProductLike | null | undefined,
): string[] {
  if (!product) return [];
  const candidates: string[] = [];

  const rawDirect =
    (typeof product.image === "string" ? product.image : "") ||
    (typeof product.image_url === "string" ? product.image_url : "") ||
    (typeof product.photo === "string" ? product.photo : "") ||
    (typeof product.photo_url === "string" ? product.photo_url : "");
  if (rawDirect?.trim()) candidates.push(rawDirect.trim());

  const photos = Array.isArray(product.photos) ? product.photos : [];
  const first = photos[0];
  const filename =
    typeof first === "string"
      ? first
      : first && typeof first === "object"
        ? (first.filename ?? first.file ?? first.path ?? first.url)
        : null;

  const raw = typeof filename === "string" ? filename.trim() : "";
  if (raw) {
    candidates.push(
      buildProductPhotoUrl(raw),
      buildBackendAssetUrl(raw, ["media"]),
      buildBackendAssetUrl(raw, ["static"]),
      buildBackendAssetUrl(raw, ["uploads"]),
      buildBackendAssetUrl(raw),
    );
  }

  return candidates.filter(Boolean);
}
