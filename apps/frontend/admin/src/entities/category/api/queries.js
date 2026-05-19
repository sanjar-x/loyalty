'use client';

import { useQuery } from '@tanstack/react-query';
import { REFERENCE_DATA_STALE_TIME_MS } from '@/shared/query';
import { fetchCategoryTree } from './categories';
import { fetchFormAttributes } from './form-attributes';
import { categoryKeys } from './keys';

/**
 * Full category tree — used by the category settings UI and by the
 * "add product → pick category" wizard. Cached for 5 minutes.
 */
export function useCategoryTree() {
  return useQuery({
    queryKey: categoryKeys.tree(),
    queryFn: fetchCategoryTree,
    staleTime: REFERENCE_DATA_STALE_TIME_MS,
  });
}

/**
 * Storefront form-attributes for a leaf category. Used by ProductDetailsForm.
 * Disabled until categoryId is known.
 */
export function useCategoryFormAttributes(categoryId) {
  return useQuery({
    queryKey: categoryKeys.formAttributes(categoryId),
    queryFn: () => fetchFormAttributes(categoryId),
    enabled: Boolean(categoryId),
    staleTime: REFERENCE_DATA_STALE_TIME_MS,
  });
}
