'use client';

import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { fetchIdentities, fetchIdentity } from './identities';
import { identityKeys } from './keys';

// Generic identities — covers staff + customers. Customer-only screens
// should prefer `useCustomers` from `entities/customer`.
export function useIdentities(filters = {}) {
  return useQuery({
    queryKey: identityKeys.list(filters),
    queryFn: () => fetchIdentities(filters),
    placeholderData: keepPreviousData,
  });
}

export function useIdentity(identityId) {
  return useQuery({
    queryKey: identityKeys.detail(identityId),
    queryFn: () => fetchIdentity(identityId),
    enabled: Boolean(identityId),
  });
}
