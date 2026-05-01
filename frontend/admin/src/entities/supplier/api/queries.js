'use client';

import { useQuery } from '@tanstack/react-query';
import { REFERENCE_DATA_STALE_TIME_MS } from '@/shared/query';
import { fetchSuppliers } from './suppliers';
import { supplierKeys } from './keys';

/**
 * Active suppliers — slowly changing reference data, cached for 5 minutes.
 * `fetchSuppliers` already filters out deactivated entries.
 *
 * Eager fetch on mount: needed both for the dropdown list AND to resolve the
 * controlled `supplierId` prop into a display name when re-opening a draft
 * product. Cache + 5-min staleTime keeps this cheap across mounts.
 */
export function useSuppliers() {
  return useQuery({
    queryKey: supplierKeys.lists(),
    queryFn: fetchSuppliers,
    staleTime: REFERENCE_DATA_STALE_TIME_MS,
  });
}
