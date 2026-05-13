'use client';

import { useQuery } from '@tanstack/react-query';

import { apiClient } from '@/lib/api-client';
import { queryKeys } from '@/lib/query-keys';
import type { Order } from '@/types';

export function useOrders(userId?: string) {
  const searchParams: Record<string, string> = {};
  if (userId) searchParams['user_id'] = userId;

  return useQuery({
    queryKey: queryKeys.orders.list(userId),
    queryFn: () =>
      apiClient
        .get('api/v1/orders/', { searchParams })
        .json<Order[]>(),
  });
}

export function useOrder(id: string) {
  return useQuery({
    queryKey: queryKeys.orders.detail(id),
    queryFn: () =>
      apiClient.get(`api/v1/orders/${id}`).json<Order>(),
    enabled: !!id,
  });
}
