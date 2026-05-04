'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { deactivateCustomer, reactivateCustomer } from './customers';
import {
  assignIdentityRole,
  deactivateIdentity,
  reactivateIdentity,
  revokeIdentityRole,
} from './identities';
import { customerKeys, identityKeys } from './keys';

function invalidateCustomer(qc, identityId) {
  qc.invalidateQueries({ queryKey: customerKeys.detail(identityId) });
  qc.invalidateQueries({ queryKey: customerKeys.lists() });
}

function invalidateIdentity(qc, identityId) {
  qc.invalidateQueries({ queryKey: identityKeys.detail(identityId) });
  qc.invalidateQueries({ queryKey: identityKeys.lists() });
}

// Customer-scoped mutations — invalidate only the customer cache namespace.

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

// Identity-scoped mutations — used by the (future) staff/IAM screens.

export function useAssignIdentityRole(identityId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (roleId) => assignIdentityRole(identityId, roleId),
    onSuccess: () => invalidateIdentity(qc, identityId),
  });
}

export function useRevokeIdentityRole(identityId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (roleId) => revokeIdentityRole(identityId, roleId),
    onSuccess: () => invalidateIdentity(qc, identityId),
  });
}

export function useDeactivateIdentity(identityId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (reason) => deactivateIdentity(identityId, reason),
    onSuccess: () => invalidateIdentity(qc, identityId),
  });
}

export function useReactivateIdentity(identityId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => reactivateIdentity(identityId),
    onSuccess: () => invalidateIdentity(qc, identityId),
  });
}
