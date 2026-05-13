'use client';

import { useQuery } from '@tanstack/react-query';

import { apiClient } from '@/lib/api-client';
import { queryKeys } from '@/lib/query-keys';
import type { SearchSuggestion, SearchHistoryItem } from '@/types';

const ONE_MINUTE = 60 * 1000;
const FIVE_MINUTES = 5 * 60 * 1000;

export function useSearchSuggestions(query: string) {
  const trimmed = query.trim();

  return useQuery({
    queryKey: queryKeys.search.suggestions(trimmed),
    queryFn: () =>
      apiClient
        .get('api/v1/search', { searchParams: { q: trimmed } })
        .json<SearchSuggestion[]>(),
    enabled: trimmed.length > 0,
    staleTime: ONE_MINUTE,
  });
}

export function useSearchHistory() {
  return useQuery({
    queryKey: queryKeys.search.history(),
    queryFn: () =>
      apiClient
        .get('api/v1/search/history', { searchParams: { limit: '10' } })
        .json<SearchHistoryItem[]>(),
    staleTime: FIVE_MINUTES,
  });
}
