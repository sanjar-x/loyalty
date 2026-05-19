'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import {
  acceptInvitationToken,
  createInvitation,
  resendInvitation,
  revokeInvitation,
} from './invitations';
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

// Resend mints a fresh token + URL and creates a NEW invitation row
// (backend revokes the old one). The success payload mirrors create:
// { invitationId, inviteUrl } — the caller surfaces the URL via the
// same copy-link UX used by InviteStaffModal.
export function useResendInvitation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (invitationId) => resendInvitation(invitationId),
    onSuccess: () => qc.invalidateQueries({ queryKey: invitationKeys.lists() }),
  });
}

// Public — used by the /invite/[token] accept form. On success the BFF
// already wrote httpOnly cookies, so we just need the promise to
// resolve before navigating. We don't invalidate anything: the invitee
// is unauthenticated until this completes, and the freshly-authenticated
// /admin shell will fetch its own data with the new session.
export function useAcceptInvitation(token) {
  return useMutation({
    mutationFn: (payload) => acceptInvitationToken(token, payload),
  });
}
