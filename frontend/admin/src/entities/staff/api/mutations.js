'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { createInvitation, revokeInvitation } from './invitations';
import { deactivateStaff, reactivateStaff } from './staff';
import { invitationKeys, staffKeys } from './keys';

function invalidateStaff(qc, identityId) {
  qc.invalidateQueries({ queryKey: staffKeys.detail(identityId) });
  qc.invalidateQueries({ queryKey: staffKeys.lists() });
}

export function useDeactivateStaff(identityId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (reason) => deactivateStaff(identityId, reason),
    onSuccess: () => invalidateStaff(qc, identityId),
  });
}

export function useReactivateStaff(identityId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => reactivateStaff(identityId),
    onSuccess: () => invalidateStaff(qc, identityId),
  });
}

export function useInviteStaff() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload) => createInvitation(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: invitationKeys.lists() }),
  });
}

export function useRevokeInvitation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (invitationId) => revokeInvitation(invitationId),
    onSuccess: () => qc.invalidateQueries({ queryKey: invitationKeys.lists() }),
  });
}
