'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import {
  bulkCreateAttributes,
  createAttribute,
  deleteAttribute,
  updateAttribute,
} from './attributes';
import { attributeKeys } from './keys';

export function useCreateAttribute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createAttribute,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: attributeKeys.lists() });
    },
  });
}

export function useUpdateAttribute(attributeId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload) => updateAttribute(attributeId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: attributeKeys.detail(attributeId) });
      qc.invalidateQueries({ queryKey: attributeKeys.lists() });
    },
  });
}

export function useDeleteAttribute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (attributeId) => deleteAttribute(attributeId),
    onSuccess: (_, attributeId) => {
      qc.removeQueries({ queryKey: attributeKeys.detail(attributeId) });
      qc.invalidateQueries({ queryKey: attributeKeys.lists() });
    },
  });
}

export function useBulkCreateAttributes() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: bulkCreateAttributes,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: attributeKeys.lists() });
    },
  });
}
