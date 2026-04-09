'use client';

import { useQuery } from '@tanstack/react-query';

import { apiClient } from '@/lib/api-client';
import { queryKeys } from '@/lib/query-keys';
import type { Favorite } from '@/types';

interface FavoritesParams {
  itemType?: string;
  brandId?: string;
}

export function useFavorites(params: FavoritesParams = {}) {
  const searchParams: Record<string, string> = {};
  if (params.itemType) searchParams['item_type'] = params.itemType;
  if (params.brandId) searchParams['brand_id'] = params.brandId;

  return useQuery({
    queryKey: queryKeys.favorites.list(params.itemType ?? 'all'),
    queryFn: () =>
      apiClient
        .get('api/v1/favorites', { searchParams })
        .json<Favorite[]>(),
  });
}
