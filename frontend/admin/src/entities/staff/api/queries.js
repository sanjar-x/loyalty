'use client';

import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { fetchInvitations } from './invitations';
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
