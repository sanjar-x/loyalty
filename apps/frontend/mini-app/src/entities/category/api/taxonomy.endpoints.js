/**
 * RTKQ endpoint enhancement config'lari — Taxonomy (categories + brands).
 */
import { mapCategoryTree as mapCategoryTreeResponse } from '@/entities/category/lib/mapCategoryTree';
import { resolveI18N } from '@/shared/lib/i18n';

export const taxonomyEndpoints = {
  storefrontCategoryTreeApiV1StorefrontCategoriesTreeGet: {
    transformResponse: (response) => mapCategoryTreeResponse(response),
    keepUnusedDataFor: 1800,
    providesTags: ['CategoryTree'],
  },
  storefrontListCategoriesApiV1StorefrontCategoriesGet: {
    keepUnusedDataFor: 1800,
    transformResponse: (response) => {
      const items = Array.isArray(response?.items)
        ? response.items
        : Array.isArray(response)
          ? response
          : [];
      return items
        .filter((c) => c && typeof c === 'object')
        .map((c) => ({
          ...c,
          name: resolveI18N(c.nameI18N, c.name || c.title || c.label || ''),
        }));
    },
    providesTags: (result) => {
      if (!Array.isArray(result)) return ['Categories'];
      return [
        'Categories',
        ...result
          .map((c) => (c && typeof c === 'object' ? c.id : null))
          .filter((id) => id != null)
          .map((id) => ({ type: 'Categories', id })),
      ];
    },
  },
  storefrontListBrandsApiV1StorefrontBrandsGet: {
    keepUnusedDataFor: 1800,
    transformResponse: (response) => {
      const items = Array.isArray(response?.items)
        ? response.items
        : Array.isArray(response)
          ? response
          : [];
      return items.filter((b) => b && typeof b === 'object');
    },
    providesTags: (result) => {
      if (!Array.isArray(result)) return ['Brands'];
      return [
        'Brands',
        ...result
          .map((b) => (b && typeof b === 'object' ? b.id : null))
          .filter((id) => id != null)
          .map((id) => ({ type: 'Brands', id })),
      ];
    },
  },
  storefrontGetBrandApiV1StorefrontBrandsBrandIdGet: {
    providesTags: (_r, _e, arg) => [{ type: 'Brands', id: arg?.brandId }],
  },
};
