/** Sprint 3d: Product RTKQ hooks — moved out of app/providers/store/hooks. */
import { enhancedApi, customApi } from '@/app/providers/store/instance';

export const useGetProductsQuery = (params, opts) =>
  enhancedApi.useListStorefrontProductsApiV1StorefrontProductsGetQuery(
    {
      categoryId: params?.category_id,
      brandId: params?.brand_id,
      priceMin: params?.price_min,
      priceMax: params?.price_max,
      inStock: params?.in_stock,
      sort: params?.sort,
      limit: params?.limit,
      cursor: params?.cursor,
      includeTotal: params?.include_total,
      includeFacets: params?.include_facets,
      lang: params?.lang,
    },
    opts
  );

export const useLazyGetProductsQuery =
  enhancedApi.useLazyListStorefrontProductsApiV1StorefrontProductsGetQuery;

export const useGetProductByIdQuery = (slugOrId, opts) =>
  enhancedApi.useGetStorefrontProductApiV1StorefrontProductsSlugGetQuery(
    { slug: String(slugOrId) },
    opts
  );

export const useGetSimilarProductsQuery = ({ slug, limit = 12 } = {}, opts) =>
  enhancedApi.useGetSimilarProductsApiV1StorefrontProductsSlugSimilarGetQuery(
    { slug, limit },
    opts
  );

export const useGetAlsoViewedProductsQuery = ({ slug, limit = 12 } = {}, opts) =>
  enhancedApi.useGetAlsoViewedProductsApiV1StorefrontProductsSlugAlsoViewedGetQuery(
    { slug, limit },
    opts
  );

export const useGetProductMediaQuery = ({ productId, limit = 50 } = {}, opts) =>
  enhancedApi.useListProductMediaApiV1AdminCatalogProductsProductIdMediaGetQuery(
    { productId, limit },
    opts
  );

export const useGetProductsByIdsQuery = customApi.useGetProductsByIdsQuery;

export const useGetLatestProductsQuery = (params, opts) => {
  const limit = typeof params === 'object' && params != null ? params?.limit : params;
  const n = limit == null ? null : Number(limit);
  const safe = typeof n === 'number' && Number.isFinite(n) && n > 0 ? Math.floor(n) : undefined;
  return enhancedApi.useListStorefrontProductsApiV1StorefrontProductsGetQuery(
    {
      categoryId: params && typeof params === 'object' ? params?.category_id : undefined,
      sort: 'newest',
      limit: safe,
    },
    opts
  );
};

export const useGetLatestPurchasedProductsQuery = (params, opts) => {
  const result = useGetLatestProductsQuery(params, opts);
  return {
    ...result,
    data: Array.isArray(result?.data?.items) ? result.data.items : [],
  };
};

export const useGetForYouFeedQuery = (params, opts) =>
  enhancedApi.useGetForYouFeedApiV1StorefrontForYouGetQuery(
    {
      limit: params?.limit,
      cursor: params?.cursor,
      lang: params?.lang,
    },
    opts
  );

export const useLazyGetForYouFeedQuery =
  enhancedApi.useLazyGetForYouFeedApiV1StorefrontForYouGetQuery;

export const useGetTrendingProductsQuery = (params, opts) =>
  enhancedApi.useListTrendingProductsApiV1StorefrontTrendingGetQuery(
    {
      limit: params?.limit,
      window: params?.window,
      categoryId: params?.category_id,
      lang: params?.lang,
    },
    opts
  );

export const useLazyGetTrendingProductsQuery =
  enhancedApi.useLazyListTrendingProductsApiV1StorefrontTrendingGetQuery;
