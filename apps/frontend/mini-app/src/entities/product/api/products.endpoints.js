/**
 * RTKQ endpoint enhancement configs — Products / Profile / Search / Media.
 * `instance.js` spreads this into `enhanceEndpoints({ endpoints })`.
 */
import {
  mapStorefrontProduct,
  unwrapPLPResponse,
} from '../lib/mapStorefrontProduct';
import { transformForYouFeed } from '../lib/transformers';

export const productEndpoints = {
  getMyProfileApiV1ProfileMeGet: {
    providesTags: ['User'],
    transformResponse: (response) => ({
      ...response,
      first_name: response?.firstName,
      last_name: response?.lastName,
      photo_url: response?.photoUrl || null,
    }),
  },

  listStorefrontProductsApiV1StorefrontProductsGet: {
    transformResponse: (response) => unwrapPLPResponse(response),
    providesTags: (result) => {
      const items = Array.isArray(result?.items) ? result.items : [];
      if (!items.length) return ['Products'];
      return [
        'Products',
        ...items
          .map((p) => (p && typeof p === 'object' ? p.id : null))
          .filter((id) => id != null)
          .map((id) => ({ type: 'Product', id })),
      ];
    },
  },
  getStorefrontProductApiV1StorefrontProductsSlugGet: {
    transformResponse: (response) => mapStorefrontProduct(response) || response,
    providesTags: (_result, _err, arg) => [{ type: 'Product', id: arg?.slug }],
    keepUnusedDataFor: 300,
  },
  getSimilarProductsApiV1StorefrontProductsSlugSimilarGet: {
    transformResponse: (response) => {
      const items = Array.isArray(response) ? response : [];
      return items.map(mapStorefrontProduct).filter(Boolean);
    },
    providesTags: (_r, _e, arg) => [{ type: 'Product', id: `similar-${arg?.slug || ''}` }],
    keepUnusedDataFor: 180,
  },
  getAlsoViewedProductsApiV1StorefrontProductsSlugAlsoViewedGet: {
    transformResponse: (response) => {
      const items = Array.isArray(response) ? response : [];
      return items.map(mapStorefrontProduct).filter(Boolean);
    },
    providesTags: (_r, _e, arg) => [{ type: 'Product', id: `also-viewed-${arg?.slug || ''}` }],
    keepUnusedDataFor: 180,
  },
  getForYouFeedApiV1StorefrontForYouGet: {
    transformResponse: transformForYouFeed,
    keepUnusedDataFor: 300,
    providesTags: (result) => {
      const items = Array.isArray(result?.items) ? result.items : [];
      if (!items.length) return ['ForYouFeed'];
      return [
        'ForYouFeed',
        ...items
          .map((p) => (p && typeof p === 'object' ? p.id : null))
          .filter((id) => id != null)
          .map((id) => ({ type: 'Product', id })),
      ];
    },
  },
  listTrendingProductsApiV1StorefrontTrendingGet: {
    transformResponse: (response) => unwrapPLPResponse(response).items,
    keepUnusedDataFor: 300,
    providesTags: (result) => {
      const items = Array.isArray(result) ? result : [];
      if (!items.length) return ['Trending'];
      return [
        'Trending',
        ...items
          .map((p) => (p && typeof p === 'object' ? p.id : null))
          .filter((id) => id != null)
          .map((id) => ({ type: 'Product', id })),
      ];
    },
  },

  searchSuggestApiV1StorefrontSearchSuggestGet: {
    transformResponse: (response) => {
      const items = Array.isArray(response) ? response : [];
      const seen = new Set();
      const out = [];
      for (const item of items) {
        const text = typeof item?.text === 'string' ? item.text.trim() : '';
        if (!text) continue;
        const key = text.toLowerCase();
        if (seen.has(key)) continue;
        seen.add(key);
        out.push(text);
      }
      return out;
    },
    keepUnusedDataFor: 60,
  },

  listProductMediaApiV1AdminCatalogProductsProductIdMediaGet: {
    transformResponse: (response) => {
      const items = Array.isArray(response?.items)
        ? response.items
        : Array.isArray(response)
          ? response
          : [];
      const valid = items.filter(
        (m) =>
          m &&
          typeof m === 'object' &&
          m.mediaType !== 'video' &&
          typeof m.url === 'string' &&
          m.url.trim()
      );
      valid.sort((a, b) => {
        const ar = a.role === 'main' ? -1 : 0;
        const br = b.role === 'main' ? -1 : 0;
        if (ar !== br) return ar - br;
        return (a.sortOrder ?? 0) - (b.sortOrder ?? 0);
      });
      return valid;
    },
    providesTags: (_r, _e, arg) => [{ type: 'Product', id: `media-${arg?.productId || ''}` }],
    keepUnusedDataFor: 300,
  },
};
