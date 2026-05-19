'use client';

import { useQuery } from '@tanstack/react-query';
import { REFERENCE_DATA_STALE_TIME_MS } from '@/shared/query';
import { fetchBrands, getBrand } from './brands';
import { brandKeys } from './keys';

/**
 * Brand catalogue — slowly changing reference data, cached for 5 minutes
 * across the whole admin (form selectors, filter dropdowns).
 */
export function useBrands() {
  return useQuery({
    queryKey: brandKeys.lists(),
    queryFn: fetchBrands,
    staleTime: REFERENCE_DATA_STALE_TIME_MS,
  });
}

/**
 * Single brand detail — used by the edit modal to seed the form before the
 * user starts typing. Disabled until `brandId` is known.
 */
export function useBrand(brandId) {
  return useQuery({
    queryKey: brandKeys.detail(brandId),
    queryFn: () => getBrand(brandId),
    enabled: Boolean(brandId),
  });
}
