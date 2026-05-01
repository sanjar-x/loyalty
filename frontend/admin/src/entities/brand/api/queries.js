'use client';

import { useQuery } from '@tanstack/react-query';
import { REFERENCE_DATA_STALE_TIME_MS } from '@/shared/query';
import { fetchBrands } from './brands';
import { brandKeys } from './keys';

/**
 * Brand catalogue — slowly changing reference data, cached for 5 minutes
 * across the whole admin (form selectors, filter dropdowns).
 *
 * Eager fetch on mount: brands are needed both for the dropdown list AND to
 * resolve the controlled `value` prop into a display name. Was lazy-on-open
 * in the pre-RQ implementation, but the new staleTime + cross-component
 * cache makes eager fetch essentially free.
 */
export function useBrands() {
  return useQuery({
    queryKey: brandKeys.lists(),
    queryFn: fetchBrands,
    staleTime: REFERENCE_DATA_STALE_TIME_MS,
  });
}
