// Identity slice public API. Identity is the broader IAM record on
// backend covering staff + customers; it owns role assignment and
// the lifecycle (de/reactivate) of any identity, not just customers.
//
// For customer-only screens use `entities/customer` instead — its
// queries hit the narrower `/admin/customers` projection and live in
// a separate TanStack Query cache namespace.

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
export {
  useAssignIdentityRole,
  useRevokeIdentityRole,
  useDeactivateIdentity,
  useReactivateIdentity,
} from './api/mutations';
