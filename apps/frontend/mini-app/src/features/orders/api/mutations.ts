'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { apiClient } from '@/lib/api-client';
import { queryKeys } from '@/lib/query-keys';
import type { Order, OrderStatus } from '@/types';

// ── Create Order ─────────────────────────────────────────────────────

interface CreateOrderPayload {
  items: Array<{ product_id: string; sku_id: string; quantity: number }>;
  shipping_address?: string;
  pickup_point_id?: string;
  [key: string]: unknown;
}

export function useCreateOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: CreateOrderPayload) =>
      apiClient.post('api/v1/orders/', { json: body }).json<Order>(),

    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.orders.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.cart.all });
    },
  });
}

// ── Update Order Status ──────────────────────────────────────────────

interface UpdateOrderStatusPayload {
  orderId: string;
  status: OrderStatus;
}

export function useUpdateOrderStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ orderId, ...body }: UpdateOrderStatusPayload) =>
      apiClient
        .patch(`api/v1/orders/${orderId}/status`, { json: body })
        .json<Order>(),

    onSettled: (_data, _err, { orderId }) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.orders.all });
      void queryClient.invalidateQueries({
        queryKey: queryKeys.orders.detail(orderId),
      });
    },
  });
}
