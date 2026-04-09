'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { apiClient } from '@/lib/api-client';
import { queryKeys } from '@/lib/query-keys';
import type { Cart, CartItem } from '@/types';

// ── Helpers ──────────────────────────────────────────────────────────

function recalcCartTotals(cart: Cart): Cart {
  let totalItems = 0;
  let totalAmount = 0;
  for (const item of cart.items) {
    totalItems += item.quantity;
    totalAmount += item.price * item.quantity;
  }
  return { ...cart, totalItems, totalAmount };
}

// ── Add Cart Item ────────────────────────────────────────────────────

interface AddCartItemPayload {
  product_id: string;
  sku_id: string;
  quantity: number;
}

export function useAddCartItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: AddCartItemPayload) =>
      apiClient.post('api/v1/cart/items', { json: body }).json<CartItem>(),

    onMutate: async (newItem) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.cart.all });
      const previous = queryClient.getQueryData<Cart>(queryKeys.cart.all);

      queryClient.setQueryData<Cart>(queryKeys.cart.all, (old) => {
        if (!old) return old;

        const existingIdx = old.items.findIndex((item) => item.productId === newItem.product_id);

        let nextItems: CartItem[];
        if (existingIdx >= 0) {
          nextItems = old.items.map((item, idx) =>
            idx === existingIdx ? { ...item, quantity: item.quantity + newItem.quantity } : item,
          );
        } else {
          nextItems = [
            ...old.items,
            {
              id: `temp-${Date.now()}`,
              productId: newItem.product_id,
              skuId: newItem.sku_id,
              quantity: newItem.quantity,
              price: 0,
            } as CartItem,
          ];
        }

        return recalcCartTotals({ ...old, items: nextItems });
      });

      return { previous };
    },

    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKeys.cart.all, context.previous);
      }
    },

    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.cart.all });
    },
  });
}

// ── Update Cart Item ─────────────────────────────────────────────────

interface UpdateCartItemPayload {
  itemId: string;
  quantity: number;
}

export function useUpdateCartItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ itemId, ...body }: UpdateCartItemPayload) =>
      apiClient.patch(`api/v1/cart/items/${itemId}`, { json: body }).json<CartItem>(),

    onMutate: async ({ itemId, quantity }) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.cart.all });
      const previous = queryClient.getQueryData<Cart>(queryKeys.cart.all);

      queryClient.setQueryData<Cart>(queryKeys.cart.all, (old) => {
        if (!old) return old;

        let nextItems: CartItem[];
        if (quantity === 0) {
          nextItems = old.items.filter((item) => item.id !== itemId);
        } else {
          nextItems = old.items.map((item) => (item.id === itemId ? { ...item, quantity } : item));
        }

        return recalcCartTotals({ ...old, items: nextItems });
      });

      return { previous };
    },

    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKeys.cart.all, context.previous);
      }
    },

    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.cart.all });
    },
  });
}

// ── Remove Cart Item ─────────────────────────────────────────────────

export function useRemoveCartItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (itemId: string) => apiClient.delete(`api/v1/cart/items/${itemId}`).json<void>(),

    onMutate: async (itemId) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.cart.all });
      const previous = queryClient.getQueryData<Cart>(queryKeys.cart.all);

      queryClient.setQueryData<Cart>(queryKeys.cart.all, (old) => {
        if (!old) return old;
        const nextItems = old.items.filter((item) => item.id !== itemId);
        return recalcCartTotals({ ...old, items: nextItems });
      });

      return { previous };
    },

    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKeys.cart.all, context.previous);
      }
    },

    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.cart.all });
    },
  });
}

// ── Clear Cart ───────────────────────────────────────────────────────

export function useClearCart() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => apiClient.delete('api/v1/cart').json<void>(),

    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: queryKeys.cart.all });
      const previous = queryClient.getQueryData<Cart>(queryKeys.cart.all);

      queryClient.setQueryData<Cart>(queryKeys.cart.all, (old) => {
        if (!old) return old;
        return { ...old, items: [], totalItems: 0, totalAmount: 0 };
      });

      return { previous };
    },

    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKeys.cart.all, context.previous);
      }
    },

    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.cart.all });
    },
  });
}
