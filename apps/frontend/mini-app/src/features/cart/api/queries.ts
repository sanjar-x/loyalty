'use client';

import { useQuery } from '@tanstack/react-query';

import { apiClient } from '@/lib/api-client';
import { queryKeys } from '@/lib/query-keys';
import type { Cart } from '@/types';

export function useCart() {
  return useQuery({
    queryKey: queryKeys.cart.all,
    queryFn: () => apiClient.get('api/v1/cart').json<Cart>(),
  });
}
