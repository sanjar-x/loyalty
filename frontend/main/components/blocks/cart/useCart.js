"use client";

import { useCallback } from "react";

const EMPTY_ARRAY = [];

export function useCart() {
  const toggleFavorite = useCallback(() => {}, []);
  const removeItem = useCallback(async () => {}, []);
  const setQuantity = useCallback(async () => {}, []);
  const removeMany = useCallback(async () => {}, []);
  const clear = useCallback(async () => {}, []);

  return {
    ready: true,
    isLoading: false,
    isFetching: false,
    isError: false,
    items: EMPTY_ARRAY,
    toggleFavorite,
    removeItem,
    setQuantity,
    removeMany,
    clear,
    totalQuantity: 0,
    subtotalRub: 0,
  };
}
