'use client';

import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { fetchInvitations, validateInvitationToken } from './invitations';
import { fetchStaffList, fetchStaffMember } from './staff';
import { invitationKeys, staffKeys } from './keys';

export function useStaffList(filters = {}) {
  return useQuery({
    queryKey: staffKeys.list(filters),
    queryFn: () => fetchStaffList(filters),
    placeholderData: keepPreviousData,
  });
}

export function useStaffMember(identityId) {
  return useQuery({
    queryKey: staffKeys.detail(identityId),
    queryFn: () => fetchStaffMember(identityId),
    enabled: Boolean(identityId),
  });
}

export function useStaffInvitations(filters = {}) {
  return useQuery({
    queryKey: invitationKeys.list(filters),
    queryFn: () => fetchInvitations(filters),
    placeholderData: keepPreviousData,
  });
}

// Public — fetched by /invite/[token]. Keyed by raw token so two
// simultaneous invitees on the same machine don't share cached state.
// retry: false because every 4xx is an actionable terminal state
// (not-found / expired / revoked / already-accepted) — silently
// retrying would just delay the error screen.
export function useInvitationInfo(token) {
  return useQuery({
    queryKey: invitationKeys.validate(token),
    queryFn: () => validateInvitationToken(token),
    enabled: Boolean(token),
    retry: false,
    staleTime: 0,
  });
}
