import { buildBackendAssetUrl } from "./product-image";

function uniqStrings(arr: string[]): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const v of arr) {
    if (!v || seen.has(v)) continue;
    seen.add(v);
    out.push(v);
  }
  return out;
}

export function buildBrandLogoUrl(filename: string | null | undefined): string {
  const raw = typeof filename === "string" ? filename.trim() : "";
  if (!raw) return "";
  if (/^https?:\/\//i.test(raw)) return raw;
  const cleaned = raw.replace(/^\/+/, "");
  if (/%[0-9A-Fa-f]{2}/.test(cleaned))
    return `/api/backend/api/v1/brands/logo/${cleaned}`;
  return `/api/backend/api/v1/brands/logo/${encodeURIComponent(cleaned)}`;
}

interface BrandLike {
  id?: number | string | null;
  logo?: string | null;
  logo_path?: string | null;
  logoUrl?: string | null;
  image?: string | null;
  image_url?: string | null;
}

/**
 * Build a prioritized list of logo URL candidates for a brand.
 */
export function getBrandLogoCandidates(
  brand: BrandLike | null | undefined,
): string[] {
  if (!brand) return [];
  const id = brand.id;
  const logo =
    brand.logo ?? brand.logo_path ?? brand.logoUrl ?? brand.image ?? brand.image_url;

  const byPath = typeof logo === "string" ? buildBrandLogoUrl(logo) : "";
  const byId =
    id != null
      ? `/api/backend/api/v1/brands/${encodeURIComponent(String(id))}/logo`
      : "";

  return uniqStrings([
    byPath,
    byId,
    typeof logo === "string" ? buildBackendAssetUrl(logo) : "",
    typeof logo === "string" ? buildBackendAssetUrl(logo, ["media"]) : "",
    typeof logo === "string" ? buildBackendAssetUrl(logo, ["static"]) : "",
    typeof logo === "string" ? buildBackendAssetUrl(logo, ["uploads"]) : "",
  ]);
}
