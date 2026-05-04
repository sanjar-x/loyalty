export { UserRow } from './ui/UserRow';
export { UserMetrics, Metric } from './ui/UserMetrics';
export { UserDetailModal } from './ui/UserDetailModal';
export { UserFilters } from './ui/UserFilters';

// Mock-backed seed accessors — kept for legacy display fixtures.
// New code should use the real /api/admin/customers or /api/admin/identities
// hooks below.
export { getUsers, getUserById } from './api/users.mock';

// Customers (customer-only projection — the «Пользователи» admin screen).
export {
  fetchCustomers,
  fetchCustomer,
  deactivateCustomer,
  reactivateCustomer,
  CUSTOMER_SORT_OPTIONS,
} from './api/customers';
export { customerKeys } from './api/keys';
export { useCustomers, useCustomer } from './api/queries';
export { useDeactivateCustomer, useReactivateCustomer } from './api/mutations';

// Identities (broader scope — covers staff + customers, exposes role
// management). Use for IAM/staff screens, not for the customer list.
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
