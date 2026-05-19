import { proxyToBackend } from '@/shared/api/bff';

// POST /api/admin/staff/invitations/{invitationId}/resend
//
// Mints a fresh token + URL for an existing invitation. Backend revokes
// the previous row and creates a new one, so the response carries a NEW
// invitationId — the consumer must refresh the list afterwards.
//
// No `successStatus` override: backend returns 200 per OpenAPI spec.
// Earlier code forced 201 on top of that, which lied about the contract
// in devtools and confused any status-based monitoring.
export const POST = proxyToBackend({
  method: 'POST',
  pathFn: ({ invitationId }) =>
    `/api/v1/admin/staff/invitations/${invitationId}/resend`,
});
