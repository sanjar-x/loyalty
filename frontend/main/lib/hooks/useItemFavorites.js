import { useCallback, useMemo } from "react";

const EMPTY_SET = new Set();
const EMPTY_MAP = new Map();
const EMPTY_ARRAY = [];

export function useItemFavorites(_itemType) {
  const toggleFavorite = useCallback(() => {
    // TODO: подключить API
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
  };
}
