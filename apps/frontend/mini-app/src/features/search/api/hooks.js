/** Sprint 3d: Search RTKQ hooks (suggestions + history). */
import { enhancedApi, customApi } from '@/app/providers/store/instance';

export const useGetSearchSuggestionsQuery = (rawQuery, opts) => {
  const q = typeof rawQuery === 'string' ? rawQuery.trim() : '';
  return enhancedApi.useSearchSuggestApiV1StorefrontSearchSuggestGetQuery(
    { q, limit: 10 },
    opts
  );
};

/* Search history (custom — localStorage thin layer) */
export const useGetSearchHistoryQuery = customApi.useGetSearchHistoryQuery;
export const useCreateSearchHistoryMutation = customApi.useCreateSearchHistoryMutation;
export const useRemoveSearchHistoryItemMutation = customApi.useRemoveSearchHistoryItemMutation;
export const useClearSearchHistoryMutation = customApi.useClearSearchHistoryMutation;
