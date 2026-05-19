'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import {
  bindAttributeToTemplate,
  reorderTemplateBindings,
  unbindAttributeFromTemplate,
  updateTemplateBinding,
} from './bindings';
import {
  cloneAttributeTemplate,
  createAttributeTemplate,
  deleteAttributeTemplate,
  updateAttributeTemplate,
} from './templates';
import { attributeTemplateKeys } from './keys';

function invalidateLists(qc) {
  qc.invalidateQueries({ queryKey: attributeTemplateKeys.lists() });
}

export function useCreateAttributeTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createAttributeTemplate,
    onSuccess: () => invalidateLists(qc),
  });
}

export function useUpdateAttributeTemplate(templateId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload) => updateAttributeTemplate(templateId, payload),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: attributeTemplateKeys.detail(templateId),
      });
      invalidateLists(qc);
    },
  });
}

export function useDeleteAttributeTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (templateId) => deleteAttributeTemplate(templateId),
    onSuccess: (_, templateId) => {
      qc.removeQueries({
        queryKey: attributeTemplateKeys.detail(templateId),
      });
      invalidateLists(qc);
    },
  });
}

export function useCloneAttributeTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: cloneAttributeTemplate,
    onSuccess: () => invalidateLists(qc),
  });
}

export function useBindAttribute(templateId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload) => bindAttributeToTemplate(templateId, payload),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: attributeTemplateKeys.bindings(templateId),
      });
    },
  });
}

export function useUpdateBinding(templateId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ bindingId, payload }) =>
      updateTemplateBinding(templateId, bindingId, payload),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: attributeTemplateKeys.bindings(templateId),
      });
    },
  });
}

export function useUnbindAttribute(templateId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (bindingId) =>
      unbindAttributeFromTemplate(templateId, bindingId),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: attributeTemplateKeys.bindings(templateId),
      });
    },
  });
}

export function useReorderBindings(templateId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (items) => reorderTemplateBindings(templateId, items),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: attributeTemplateKeys.bindings(templateId),
      });
    },
  });
}
