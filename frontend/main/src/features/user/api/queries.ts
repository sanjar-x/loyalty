'use client';

import { useQuery } from '@tanstack/react-query';

import { apiClient } from '@/lib/api-client';
import { queryKeys } from '@/lib/query-keys';
import type { UserProfile } from '@/types';

export function useMe() {
  return useQuery({
    queryKey: queryKeys.user.me(),
    queryFn: () => apiClient.get('api/v1/users').json<UserProfile>(),
  });
}
