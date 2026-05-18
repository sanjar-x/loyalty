/** Sprint 3d: Category RTKQ hooks. */
import { enhancedApi } from '@/app/providers/store/instance';

export const useGetCategoryTreeQuery = (arg, opts) => {
  const maxDepth = Number(arg?.maxDepth);
  const safe = Number.isInteger(maxDepth) && maxDepth >= 1 && maxDepth <= 10 ? maxDepth : undefined;
  return enhancedApi.useStorefrontCategoryTreeApiV1StorefrontCategoriesTreeGetQuery(
    { maxDepth: safe },
    opts
  );
};

export const useGetCategoriesQuery = (arg, opts) =>
  enhancedApi.useStorefrontListCategoriesApiV1StorefrontCategoriesGetQuery(
    { limit: 100, ...(arg || {}) },
    opts
  );

const adminOnlyMutation = () => [
  () => Promise.reject(new Error('Admin operation — not exposed in customer app')),
  { isLoading: false, isError: false, error: undefined, reset: () => {} },
];

const pendingFeatureQuery = () => ({
  data: undefined,
  isLoading: false,
  isFetching: false,
  isError: false,
  error: undefined,
  refetch: () => Promise.resolve(),
});

export const useCreateCategoryMutation = adminOnlyMutation;
export const useDeleteCategoryMutation = adminOnlyMutation;
export const useGetCategoriesWithTypesQuery = () => ({ ...pendingFeatureQuery(), data: [] });
export const useGetTypesByCategoryQuery = () => ({ ...pendingFeatureQuery(), data: [] });
