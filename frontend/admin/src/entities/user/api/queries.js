'use client';

import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { fetchIdentities, fetchIdentity } from './identities';
import { identityKeys } from './keys';

/**
 * Identities (admin users) list — paginated and filterable.
 *
 * Uses `keepPreviousData` so pagination changes don't flash a loader; the
 * previous page stays visible while the next one is being fetched.
 */
export function useIdentities(filters = {}) {
  return useQuery({
    queryKey: identityKeys.list(filters),
    queryFn: () => fetchIdentities(filters),
    placeholderData: keepPreviousData,
  });
}

/**
 * Single identity detail. Disabled until identityId is provided.
 */
export function useIdentity(identityId) {
  return useQuery({
    queryKey: identityKeys.detail(identityId),
    queryFn: () => fetchIdentity(identityId),
    enabled: Boolean(identityId),
  });
}
