// Staff slice public API. Mirrors the layout used by entities/customer
// and entities/identity — staff is the IAM projection covering everyone
// invitable through /admin/staff/invitations. Wired directly to the
// real backend (`/api/admin/staff` + `/api/admin/staff/invitations`);
// the legacy `staff.mock.js` seed file has been retired.

// UI components
export { StaffRow } from './ui/StaffRow';
export { StaffFilters } from './ui/StaffFilters';
export { StaffDetailModal } from './ui/StaffDetailModal';
export { InviteStaffModal } from './ui/InviteStaffModal';
export { InvitationRow } from './ui/InvitationRow';
export {
  StaffAnomalyBadges,
  StaffAnomalyBanner,
  hasStaffAnomaly,
} from './ui/StaffAnomalyBadges';

// CSS module — re-exported as a named binding so callers can do
// `import { staffStyles } from '@/entities/staff'`.
export { default as staffStyles } from './ui/styles/staff.module.css';

// Staff API — list, detail, deactivate/reactivate, sort options.
export {
  STAFF_SORT_OPTIONS,
  fetchStaffList,
  fetchStaffMember,
  deactivateStaff,
  reactivateStaff,
} from './api/staff';

// Invitations API — list/create/resend/revoke + public validate/accept +
// status enum and Russian labels.
export {
  INVITATION_STATUSES,
  INVITATION_STATUS_LABELS,
  fetchInvitations,
  createInvitation,
  resendInvitation,
  revokeInvitation,
  validateInvitationToken,
  acceptInvitationToken,
} from './api/invitations';

// TanStack Query keys.
export { staffKeys, invitationKeys } from './api/keys';

// Read hooks.
export {
  useStaffList,
  useStaffMember,
  useStaffInvitations,
  useInvitationInfo,
} from './api/queries';

// Write hooks.
export {
  useDeactivateStaff,
  useReactivateStaff,
  useInviteStaff,
  useRevokeInvitation,
  useResendInvitation,
  useAcceptInvitation,
} from './api/mutations';
