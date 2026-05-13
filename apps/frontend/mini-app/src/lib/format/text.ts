/**
 * Normalize text for general search: trim, collapse whitespace, lowercase.
 */
export function normalize(text: string): string {
  return text.trim().replace(/\s+/g, " ").toLowerCase();
}

/**
 * Normalize text for catalog search: additionally replaces ё->е and strips special chars.
 * Used for fuzzy matching of Russian category/brand names.
 */
export function normalizeForCatalogSearch(text: string): string {
  return text
    .toLowerCase()
    .replace(/ё/g, "е")
    .replace(/[^а-яa-z0-9 ]/g, "")
    .trim();
}

/**
 * Get the first letter of a string, uppercased. Used for alphabetical grouping.
 */
export function getFirstLetter(text: string): string {
  const trimmed = text.trim();
  return trimmed.length > 0 ? trimmed[0]!.toUpperCase() : "#";
}
