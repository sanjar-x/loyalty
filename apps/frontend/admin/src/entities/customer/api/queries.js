'use client';

import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { fetchCustomer, fetchCustomers } from './customers';
import { customerKeys } from './keys';

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
