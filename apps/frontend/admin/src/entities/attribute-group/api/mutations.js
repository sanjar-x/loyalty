'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { attributeKeys } from '@/entities/attribute';

import {
  createAttributeGroup,
  deleteAttributeGroup,
  updateAttributeGroup,
} from './groups';
import { attributeGroupKeys } from './keys';

// Mutating an attribute-group can shift the `groupId` shown on every
// attribute row (rename, delete cascade-set-null), so we proactively
// invalidate `attributeKeys.lists()` from this slice. Importing
// `attributeKeys` cross-entity goes through the `entities/attribute`
// public barrel — ESLint enforces.
function invalidateGroupAndAttributes(qc, groupId) {
  qc.invalidateQueries({ queryKey: attributeGroupKeys.lists() });
  if (groupId) {
    qc.invalidateQueries({ queryKey: attributeGroupKeys.detail(groupId) });
  }
  qc.invalidateQueries({ queryKey: attributeKeys.lists() });
}

export function useCreateAttributeGroup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createAttributeGroup,
    onSuccess: () => invalidateGroupAndAttributes(qc),
  });
}

export function useUpdateAttributeGroup(groupId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload) => updateAttributeGroup(groupId, payload),
    onSuccess: () => invalidateGroupAndAttributes(qc, groupId),
  });
}

export function useDeleteAttributeGroup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (groupId) => deleteAttributeGroup(groupId),
    onSuccess: (_, groupId) => {
      qc.removeQueries({ queryKey: attributeGroupKeys.detail(groupId) });
      invalidateGroupAndAttributes(qc);
    },
  });
}
