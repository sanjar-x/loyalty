'use client';

import { useQuery } from '@tanstack/react-query';
import { DEFAULT_STALE_TIME_MS } from '@/shared/query';
import {
  fetchProviderAccount,
  fetchProviderAccounts,
} from './logistics-providers';
import { providerAccountKeys } from './keys';

/**
 * Provider-account list. This is configuration data — changed rarely, but
 * not "reference data" either: the 30s admin-default staleTime keeps it
 * fresh without refetching on every remount.
 */
export function useProviderAccounts(filters = {}) {
  return useQuery({
    queryKey: providerAccountKeys.list(filters),
    queryFn: () => fetchProviderAccounts(filters),
    staleTime: DEFAULT_STALE_TIME_MS,
  });
}

/**
 * Single provider account — seeds the edit modal with the live `config`
 * and `credentialFingerprints`. Disabled until `id` is known.
 */
export function useProviderAccount(id) {
  return useQuery({
    queryKey: providerAccountKeys.detail(id),
    queryFn: () => fetchProviderAccount(id),
    enabled: Boolean(id),
  });
}
