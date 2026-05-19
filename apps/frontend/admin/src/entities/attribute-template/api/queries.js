'use client';

import { useQuery } from '@tanstack/react-query';

import { REFERENCE_DATA_STALE_TIME_MS } from '@/shared/query';

import { fetchTemplateBindings } from './bindings';
import { fetchAttributeTemplates, getAttributeTemplate } from './templates';
import { attributeTemplateKeys } from './keys';

export function useAttributeTemplates(filters = {}) {
  return useQuery({
    queryKey: attributeTemplateKeys.list(filters),
    queryFn: () => fetchAttributeTemplates(filters),
    staleTime: REFERENCE_DATA_STALE_TIME_MS,
  });
}

export function useAttributeTemplate(templateId) {
  return useQuery({
    queryKey: attributeTemplateKeys.detail(templateId),
    queryFn: () => getAttributeTemplate(templateId),
    enabled: Boolean(templateId),
  });
}

export function useTemplateBindings(templateId) {
  return useQuery({
    queryKey: attributeTemplateKeys.bindings(templateId),
    queryFn: () => fetchTemplateBindings(templateId),
    enabled: Boolean(templateId),
    staleTime: REFERENCE_DATA_STALE_TIME_MS,
  });
}
