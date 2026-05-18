/**
 * Slug → decorative icon mapping for root-level category cards.
 * Kept small and explicit — unknown slugs get the generic fallback.
 */
const CATALOG_ICON_BY_SLUG = {
  odezhda: '/icons/catalog/catalog-icon-1.webp',
  clothes: '/icons/catalog/catalog-icon-1.webp',
  clothing: '/icons/catalog/catalog-icon-1.webp',
  obuv: '/icons/catalog/catalog-icon-2.webp',
  shoes: '/icons/catalog/catalog-icon-2.webp',
  shoe: '/icons/catalog/catalog-icon-2.webp',
  footwear: '/icons/catalog/catalog-icon-2.webp',
  aksessuary: '/icons/catalog/catalog-icon-3.webp',
  accessories: '/icons/catalog/catalog-icon-3.webp',
  accessory: '/icons/catalog/catalog-icon-3.webp',
};

const DEFAULT_ICON = '/icons/catalog/catalog-icon-1.webp';

export function getCategoryIconBySlug(slug) {
  if (typeof slug !== 'string' || !slug) return DEFAULT_ICON;
  const key = slug.toLowerCase();
  return CATALOG_ICON_BY_SLUG[key] || DEFAULT_ICON;
}
