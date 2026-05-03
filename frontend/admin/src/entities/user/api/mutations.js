'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  assignIdentityRole,
  deactivateIdentity,
  reactivateIdentity,
  revokeIdentityRole,
} from './identities';
import { identityKeys } from './keys';

function invalidateIdentity(qc, identityId) {
  qc.invalidateQueries({ queryKey: identityKeys.detail(identityId) });
  qc.invalidateQueries({ queryKey: identityKeys.lists() });
}

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
