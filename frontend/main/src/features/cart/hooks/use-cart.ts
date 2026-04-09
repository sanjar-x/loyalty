"use client";

import { useMemo } from "react";

import { useAddCartItem, useUpdateCartItem, useRemoveCartItem, useClearCart } from "@/features/cart/api/mutations";
import { useCart as useCartQuery } from "@/features/cart/api/queries";
import { formatRub } from "@/lib/format";
import type { CartItem } from "@/types";

export interface EnrichedCartItem extends CartItem {
  formattedPrice: string;
}

export function useCart() {
  const { data: cart, isLoading, error } = useCartQuery();
  const addMutation = useAddCartItem();
  const updateMutation = useUpdateCartItem();
  const removeMutation = useRemoveCartItem();
  const clearMutation = useClearCart();

  const items = useMemo<EnrichedCartItem[]>(() => {
    if (!cart?.items) return [];
    return cart.items.map((item) => ({
      ...item,
      formattedPrice: formatRub(item.price * item.quantity),
    }));
  }, [cart?.items]);

  const totalQuantity = cart?.totalItems ?? 0;
  const subtotalRub = cart?.totalAmount ?? 0;

  return {
    items,
    totalQuantity,
    subtotalRub,
    formattedSubtotal: formatRub(subtotalRub),
    isLoading,
    error,
    addItem: (productId: string, skuId: string, quantity: number = 1) =>
      addMutation.mutateAsync({ product_id: productId, sku_id: skuId, quantity }),
    updateQuantity: (itemId: string, quantity: number) =>
      updateMutation.mutateAsync({ itemId, quantity }),
    removeItem: (itemId: string) =>
      removeMutation.mutateAsync(itemId),
    clearCart: () =>
      clearMutation.mutateAsync(),
    isAdding: addMutation.isPending,
    isUpdating: updateMutation.isPending,
    isRemoving: removeMutation.isPending,
    isClearing: clearMutation.isPending,
  };
}
