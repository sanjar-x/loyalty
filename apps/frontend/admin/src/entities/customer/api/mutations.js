'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { deactivateCustomer, reactivateCustomer } from './customers';
import { customerKeys } from './keys';

function invalidateCustomer(qc, identityId) {
  qc.invalidateQueries({ queryKey: customerKeys.detail(identityId) });
  qc.invalidateQueries({ queryKey: customerKeys.lists() });
}

export function useDeactivateCustomer(identityId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (reason) => deactivateCustomer(identityId, reason),
    onSuccess: () => invalidateCustomer(qc, identityId),
  });
}

export function useReactivateCustomer(identityId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => reactivateCustomer(identityId),
    onSuccess: () => invalidateCustomer(qc, identityId),
  });
}
