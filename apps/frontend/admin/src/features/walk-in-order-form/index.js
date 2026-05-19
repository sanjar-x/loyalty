// Public API of the walk-in order creation feature.
//
// Renders the multi-section single-page form, handles client-side
// validation, two-step SKU picking, and submits via TanStack mutation
// to /api/admin/orders. Idempotency key lifecycle is owned here.

export { WalkInOrderForm } from './ui/WalkInOrderForm';

export { useWalkInOrderForm } from './model/useWalkInOrderForm';
export { useSubmitWalkInOrder } from './model/useSubmitWalkInOrder';

export {
  DEFAULT_CURRENCY,
  MAX_PRICE_OVERRIDE_RATIO,
  OFFLINE_PAYMENT_METHODS,
  PICKUP_CARRIERS,
} from './lib/constants';
