/** Sprint 3d: Brand RTKQ hooks. */
import { enhancedApi, customApi } from '@/app/providers/store/instance';

export const useGetBrandsQuery = (arg, opts) =>
  enhancedApi.useStorefrontListBrandsApiV1StorefrontBrandsGetQuery(
    { limit: 200, ...(arg || {}) },
    opts
  );

export const useSearchBrandsQuery = customApi.useSearchBrandsQuery;

export const useGetBrandByIdQuery = (brandId, opts) =>
  enhancedApi.useStorefrontGetBrandApiV1StorefrontBrandsBrandIdGetQuery({ brandId }, opts);

const adminOnlyMutation = () => [
  () => Promise.reject(new Error('Admin operation — not exposed in customer app')),
  { isLoading: false, isError: false, error: undefined, reset: () => {} },
];

export const useCreateBrandMutation = adminOnlyMutation;
export const useDeleteBrandMutation = adminOnlyMutation;
export const useUploadBrandLogoMutation = adminOnlyMutation;
export const useDeleteBrandLogoMutation = adminOnlyMutation;
