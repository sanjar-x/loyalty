/**
 * Pick localized value from `{ru, en, ...}` map, with fallback chain.
 *
 * Universal — not tied to any specific entity (Sprint 1.4: lifted from
 * entities/product/lib/mapStorefrontProduct, where it was used cross-entity
 * via deep imports).
 *
 * @param {string | Record<string, string> | null | undefined} i18nObj
 * @param {string} [fallback]
 * @returns {string}
 */
const DEFAULT_LANG = 'ru';

export function resolveI18N(i18nObj, fallback) {
  if (typeof i18nObj === 'string') return i18nObj;
  if (i18nObj && typeof i18nObj === 'object') {
    return i18nObj[DEFAULT_LANG] || i18nObj.en || Object.values(i18nObj)[0] || fallback || '';
  }
  return fallback || '';
}
