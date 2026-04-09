"use client";

import { useCallback } from "react";

interface CartItem {
  id: string | number;
  name: string;
  price: number;
  quantity: number;
  isFavorite?: boolean;
  priceRub?: number;
  lineTotalRub?: number;
  deliveryText?: string;
  shippingText?: string;
  image?: string;
  size?: string;
  article?: string;
  productId?: string | number;
}

interface UseCartReturn {
  ready: boolean;
  isLoading: boolean;
  isFetching: boolean;
  isError: boolean;
  items: CartItem[];
  toggleFavorite: (id: string | number) => void;
  removeItem: (id: string | number) => Promise<void>;
  setQuantity: (id: string | number, quantity: number) => Promise<void>;
  removeMany: (ids: (string | number)[]) => Promise<void>;
  clear: () => Promise<void>;
  totalQuantity: number;
  subtotalRub: number;
}

const EMPTY_ARRAY: CartItem[] = [];

export function useCart(): UseCartReturn {
  const toggleFavorite = useCallback((_id: string | number) => {}, []);
  const removeItem = useCallback(async (_id: string | number) => {}, []);
  const setQuantity = useCallback(async (_id: string | number, _quantity: number) => {}, []);
  const removeMany = useCallback(async (_ids: (string | number)[]) => {}, []);
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
