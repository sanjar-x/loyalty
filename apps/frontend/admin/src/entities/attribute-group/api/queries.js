'use client';

import { useQuery } from '@tanstack/react-query';

import { REFERENCE_DATA_STALE_TIME_MS } from '@/shared/query';

import { fetchAttributeGroups, getAttributeGroup } from './groups';
import { attributeGroupKeys } from './keys';

export function useAttributeGroups(filters = {}) {
  return useQuery({
    queryKey: attributeGroupKeys.list(filters),
    queryFn: () => fetchAttributeGroups(filters),
    staleTime: REFERENCE_DATA_STALE_TIME_MS,
  });
}

export function useAttributeGroup(groupId) {
  return useQuery({
    queryKey: attributeGroupKeys.detail(groupId),
    queryFn: () => getAttributeGroup(groupId),
    enabled: Boolean(groupId),
  });
}
