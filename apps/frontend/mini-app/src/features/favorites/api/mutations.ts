'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { apiClient } from '@/lib/api-client';
import { queryKeys } from '@/lib/query-keys';
import type { Favorite, AddFavoritePayload } from '@/types';

export function useAddFavorite() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: AddFavoritePayload) =>
      apiClient.post('api/v1/favorites', { json: body }).json<Favorite>(),

    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.favorites.all });
    },
  });
}

export function useRemoveFavorite() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`api/v1/favorites/${id}`).json<void>(),

    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.favorites.all });
    },
  });
}
