import { useCallback } from "react";

const EMPTY_SET = new Set<number | string>();
const EMPTY_MAP = new Map<number | string, number[]>();
const EMPTY_ARRAY: never[] = [];

export function useItemFavorites(_itemType: "product" | "brand") {
  const toggleFavorite = useCallback((_id: number | string) => {
    // TODO: connect to API
  }, []);

  return {
    favorites: EMPTY_ARRAY,
    favoriteItemIds: EMPTY_SET,
    itemIdToFavoriteIds: EMPTY_MAP,
    toggleFavorite,
    isLoading: false,
    isFetching: false,
    isError: false,
    isMutating: false,
    refetch: () => {},
  } as const;
}
