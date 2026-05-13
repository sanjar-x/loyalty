'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { apiClient } from '@/lib/api-client';
import { queryKeys } from '@/lib/query-keys';
import type { SearchHistoryItem, CreateSearchHistoryPayload } from '@/types';

export function useCreateSearchHistory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: CreateSearchHistoryPayload) =>
      apiClient
        .post('api/v1/search/history', { json: body })
        .json<SearchHistoryItem>(),

    onMutate: async (newEntry) => {
      await queryClient.cancelQueries({
        queryKey: queryKeys.search.history(),
      });
      const previous = queryClient.getQueryData<SearchHistoryItem[]>(
        queryKeys.search.history(),
      );

      queryClient.setQueryData<SearchHistoryItem[]>(
        queryKeys.search.history(),
        (old) => {
          if (!old) return old;

          const normalized = newEntry.query.trim().replace(/\s+/g, ' ').toLowerCase();

          const tempItem: SearchHistoryItem = {
            id: `temp-${Date.now()}`,
            userId: null,
            query: newEntry.query,
            parameters: newEntry.parameters ?? {},
            searchedAt: new Date().toISOString(),
          };

          // Deduplicate by normalized query, put new on top
          const filtered = old.filter(
            (item) =>
              item.query.trim().replace(/\s+/g, ' ').toLowerCase() !== normalized,
          );

          return [tempItem, ...filtered];
        },
      );

      return { previous };
    },

    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKeys.search.history(), context.previous);
      }
    },

    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.search.history(),
      });
    },
  });
}
