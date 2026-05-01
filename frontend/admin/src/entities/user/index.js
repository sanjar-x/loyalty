export { UserRow } from './ui/UserRow';
export { UserMetrics, Metric } from './ui/UserMetrics';
export { UserDetailModal } from './ui/UserDetailModal';
export { UserFilters } from './ui/UserFilters';

// Mock-backed seed accessors — kept for legacy display fixtures.
// New code should use the real /api/admin/identities hooks below.
export { getUsers, getUserById } from './api/users.mock';

export {
  fetchIdentities,
  fetchIdentity,
  assignIdentityRole,
  revokeIdentityRole,
  deactivateIdentity,
  reactivateIdentity,
} from './api/identities';
export { identityKeys } from './api/keys';
export { useIdentities, useIdentity } from './api/queries';
