import { apiClient } from '@/shared/api/client-fetch';

const DEFAULT_LIMIT = 20;

// `InvitationStatus` enum from the OpenAPI: PENDING|ACCEPTED|REVOKED|EXPIRED.
// Anything else is rejected by the backend with 422.
export const INVITATION_STATUSES = [
  'PENDING',
  'ACCEPTED',
  'REVOKED',
  'EXPIRED',
];

export const INVITATION_STATUS_LABELS = {
  PENDING: 'Ожидает',
  ACCEPTED: 'Принято',
  REVOKED: 'Отозвано',
  EXPIRED: 'Истекло',
};

function buildInvitationsQuery({
  page = 1,
  limit = DEFAULT_LIMIT,
  status,
} = {}) {
  const params = new URLSearchParams();
  params.set('offset', String(Math.max(0, (page - 1) * limit)));
  params.set('limit', String(limit));
  if (status) params.set('status', status);
  return params.toString();
}

export async function fetchInvitations(filters = {}) {
  const data = await apiClient.get(
    `/api/admin/staff/invitations?${buildInvitationsQuery(filters)}`,
  );
  return {
    items: Array.isArray(data?.items) ? data.items : [],
    total: typeof data?.total === 'number' ? data.total : 0,
    offset: typeof data?.offset === 'number' ? data.offset : 0,
    limit: typeof data?.limit === 'number' ? data.limit : DEFAULT_LIMIT,
  };
}

// `InviteStaffRequest`: { email: string<email>, roleIds: uuid[], minItems 1 }
// Returns `InviteStaffResponse`: { invitationId, inviteUrl }.
export const createInvitation = (payload) =>
  apiClient.post('/api/admin/staff/invitations', payload);

export const revokeInvitation = (invitationId) =>
  apiClient.del(`/api/admin/staff/invitations/${invitationId}`);
