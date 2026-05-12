"use client";

import { useMemo, useCallback } from "react";

import { useAddFavorite, useRemoveFavorite } from "@/features/favorites/api/mutations";
import { useFavorites } from "@/features/favorites/api/queries";
import type { Favorite } from "@/types";

type ItemType = "product" | "brand";

export function useItemFavorites(itemType: ItemType) {
  const { data: favorites = [], isLoading } = useFavorites({ itemType });
  const addMutation = useAddFavorite();
  const removeMutation = useRemoveFavorite();

  const favoriteIds = useMemo(
    () => new Set(favorites.map((f: Favorite) => f.itemId)),
    [favorites],
  );

  const isFavorite = useCallback(
    (itemId: string | number) => favoriteIds.has(String(itemId)),
    [favoriteIds],
  );

  const toggleFavorite = useCallback(
    async (itemId: string | number) => {
      const id = String(itemId);
      if (favoriteIds.has(id)) {
        const record = favorites.find((f: Favorite) => f.itemId === id);
        if (record) {
          await removeMutation.mutateAsync(record.id);
        }
      } else {
        await addMutation.mutateAsync({ item_id: id, item_type: itemType });
      }
    },
    [favoriteIds, favorites, addMutation, removeMutation, itemType],
  );

  return {
    favorites,
    favoriteIds,
    isFavorite,
    toggleFavorite,
    isLoading,
    isToggling: addMutation.isPending || removeMutation.isPending,
  };
}
