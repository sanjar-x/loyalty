'use client';

import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { REFERENCE_DATA_STALE_TIME_MS } from '@/shared/query';

import { fetchAttributeValues, getAttributeValue } from './values';
import { attributeValueKeys } from './keys';

export function useAttributeValues(attributeId, filters = {}) {
  return useQuery({
    queryKey: attributeValueKeys.list(attributeId, filters),
    queryFn: () => fetchAttributeValues(attributeId, filters),
    enabled: Boolean(attributeId),
    staleTime: REFERENCE_DATA_STALE_TIME_MS,
    placeholderData: keepPreviousData,
  });
}

export function useAttributeValue(attributeId, valueId) {
  return useQuery({
    queryKey: attributeValueKeys.detail(attributeId, valueId),
    queryFn: () => getAttributeValue(attributeId, valueId),
    enabled: Boolean(attributeId && valueId),
  });
}
