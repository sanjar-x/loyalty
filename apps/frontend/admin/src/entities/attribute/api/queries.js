'use client';

import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { REFERENCE_DATA_STALE_TIME_MS } from '@/shared/query';

import { fetchAttributes, getAttribute, getAttributeUsage } from './attributes';
import { attributeKeys } from './keys';

/**
 * Paginated attribute list — admin-facing source of truth for catalog
 * configuration. 5-min staleTime keeps the settings page snappy while
 * still picking up backend-side edits within the same session.
 */
export function useAttributes(filters = {}) {
  return useQuery({
    queryKey: attributeKeys.list(filters),
    queryFn: () => fetchAttributes(filters),
    staleTime: REFERENCE_DATA_STALE_TIME_MS,
    placeholderData: keepPreviousData,
  });
}

export function useAttribute(attributeId) {
  return useQuery({
    queryKey: attributeKeys.detail(attributeId),
    queryFn: () => getAttribute(attributeId),
    enabled: Boolean(attributeId),
  });
}

/**
 * Usage analytics for a given attribute — drives the delete-confirm
 * blocker. `staleTime: 0` because the relevant numbers (template /
 * category / product counts) shift the moment the admin makes a
 * structural change elsewhere.
 */
export function useAttributeUsage(attributeId, { enabled = true } = {}) {
  return useQuery({
    queryKey: attributeKeys.usage(attributeId),
    queryFn: () => getAttributeUsage(attributeId),
    enabled: enabled && Boolean(attributeId),
    staleTime: 0,
  });
}
