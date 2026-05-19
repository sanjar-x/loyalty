'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  createProviderAccount,
  deleteProviderAccount,
  setProviderAccountActive,
  updateProviderAccount,
} from './logistics-providers';
import { providerAccountKeys } from './keys';

// Mutations only invalidate cache here. The registry `refresh` + toasts are
// orchestrated one layer up (features/logistics-provider-form) so the
// entity stays UI-agnostic.

export function useCreateProviderAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createProviderAccount,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: providerAccountKeys.lists() });
    },
  });
}

export function useUpdateProviderAccount(id) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload) => updateProviderAccount(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: providerAccountKeys.detail(id) });
      qc.invalidateQueries({ queryKey: providerAccountKeys.lists() });
    },
  });
}

export function useSetProviderAccountActive() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, isActive }) => setProviderAccountActive(id, isActive),
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: providerAccountKeys.detail(id) });
      qc.invalidateQueries({ queryKey: providerAccountKeys.lists() });
    },
  });
}

export function useDeleteProviderAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deleteProviderAccount,
    onSuccess: (_data, id) => {
      qc.removeQueries({ queryKey: providerAccountKeys.detail(id) });
      qc.invalidateQueries({ queryKey: providerAccountKeys.lists() });
    },
  });
}
