'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import {
  activateAttributeValue,
  bulkAddAttributeValues,
  createAttributeValue,
  deactivateAttributeValue,
  deleteAttributeValue,
  reorderAttributeValues,
  updateAttributeValue,
} from './values';
import { attributeValueKeys } from './keys';

function invalidateValues(qc, attributeId) {
  qc.invalidateQueries({
    queryKey: attributeValueKeys.byAttribute(attributeId),
  });
}

export function useCreateAttributeValue(attributeId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload) => createAttributeValue(attributeId, payload),
    onSuccess: () => invalidateValues(qc, attributeId),
  });
}

export function useUpdateAttributeValue(attributeId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ valueId, payload }) =>
      updateAttributeValue(attributeId, valueId, payload),
    onSuccess: () => invalidateValues(qc, attributeId),
  });
}

export function useDeleteAttributeValue(attributeId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (valueId) => deleteAttributeValue(attributeId, valueId),
    onSuccess: (_, valueId) => {
      qc.removeQueries({
        queryKey: attributeValueKeys.detail(attributeId, valueId),
      });
      invalidateValues(qc, attributeId);
    },
  });
}

export function useDeactivateAttributeValue(attributeId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (valueId) => deactivateAttributeValue(attributeId, valueId),
    // Optimistic flip: backend returns `{id, isActive: false}`, the list
    // cache stores the value as part of `items`, so we patch in place
    // and rollback on failure. Avoids a full refetch flicker.
    onMutate: async (valueId) => {
      await qc.cancelQueries({
        queryKey: attributeValueKeys.byAttribute(attributeId),
      });
      const snapshots = qc.getQueriesData({
        queryKey: attributeValueKeys.byAttribute(attributeId),
      });
      for (const [key, data] of snapshots) {
        if (!data?.items) continue;
        qc.setQueryData(key, {
          ...data,
          items: data.items.map((v) =>
            v.id === valueId ? { ...v, isActive: false } : v,
          ),
        });
      }
      return { snapshots };
    },
    onError: (_err, _valueId, context) => {
      for (const [key, data] of context?.snapshots ?? []) {
        qc.setQueryData(key, data);
      }
    },
    onSettled: () => invalidateValues(qc, attributeId),
  });
}

export function useActivateAttributeValue(attributeId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (valueId) => activateAttributeValue(attributeId, valueId),
    onMutate: async (valueId) => {
      await qc.cancelQueries({
        queryKey: attributeValueKeys.byAttribute(attributeId),
      });
      const snapshots = qc.getQueriesData({
        queryKey: attributeValueKeys.byAttribute(attributeId),
      });
      for (const [key, data] of snapshots) {
        if (!data?.items) continue;
        qc.setQueryData(key, {
          ...data,
          items: data.items.map((v) =>
            v.id === valueId ? { ...v, isActive: true } : v,
          ),
        });
      }
      return { snapshots };
    },
    onError: (_err, _valueId, context) => {
      for (const [key, data] of context?.snapshots ?? []) {
        qc.setQueryData(key, data);
      }
    },
    onSettled: () => invalidateValues(qc, attributeId),
  });
}

export function useBulkAddAttributeValues(attributeId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (items) => bulkAddAttributeValues(attributeId, items),
    onSuccess: () => invalidateValues(qc, attributeId),
  });
}

export function useReorderAttributeValues(attributeId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (items) => reorderAttributeValues(attributeId, items),
    onSuccess: () => invalidateValues(qc, attributeId),
  });
}
