// Customer slice public API. Customer is the customer-facing projection
// of the broader Identity record on backend — see `entities/identity/`
// for the IAM-scope view (covers staff + customers, role management).

export { CustomerRow } from './ui/CustomerRow';
export { CustomerMetrics, Metric } from './ui/CustomerMetrics';
export { CustomerDetailModal } from './ui/CustomerDetailModal';
export { CustomerFilters } from './ui/CustomerFilters';

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
