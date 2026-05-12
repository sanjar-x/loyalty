'use client';

import { useQuery } from '@tanstack/react-query';

import { apiClient } from '@/lib/api-client';
import { queryKeys } from '@/lib/query-keys';
import type {
  ReferralLink,
  InvitedUsersResponse,
  ActiveDiscount,
  ReferralStats,
} from '@/types';

export function useReferralLink() {
  return useQuery({
    queryKey: queryKeys.referrals.link(),
    queryFn: () =>
      apiClient.get('api/v1/referrals/link').json<ReferralLink>(),
  });
}

export function useInvitedUsers() {
  return useQuery({
    queryKey: queryKeys.referrals.invited(),
    queryFn: () =>
      apiClient.get('api/v1/referrals/invited').json<InvitedUsersResponse>(),
  });
}

export function useActiveDiscount() {
  return useQuery({
    queryKey: queryKeys.referrals.discount(),
    queryFn: () =>
      apiClient.get('api/v1/referrals/discount').json<ActiveDiscount>(),
  });
}

export function useReferralStats() {
  return useQuery({
    queryKey: queryKeys.referrals.stats(),
    queryFn: () =>
      apiClient.get('api/v1/referrals/stats').json<ReferralStats>(),
  });
}
