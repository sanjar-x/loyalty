'use client';

import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { fetchCustomer, fetchCustomers } from './customers';
import { fetchIdentities, fetchIdentity } from './identities';
import { customerKeys, identityKeys } from './keys';

/**
 * Customers list (admin/customers) — paginated and filterable.
 *
 * Uses `keepPreviousData` so pagination changes don't flash a loader; the
 * previous page stays visible while the next one is being fetched.
 */
export function useCustomers(filters = {}) {
  return useQuery({
    queryKey: customerKeys.list(filters),
    queryFn: () => fetchCustomers(filters),
    placeholderData: keepPreviousData,
  });
}

/**
 * Single customer detail. Disabled until identityId is provided.
 */
export function useCustomer(identityId) {
  return useQuery({
    queryKey: customerKeys.detail(identityId),
    queryFn: () => fetchCustomer(identityId),
    enabled: Boolean(identityId),
  });
}

// Generic identities (covers staff + customers). Kept for callers that need
// the wider scope; customer-only screens should prefer `useCustomers`.
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
