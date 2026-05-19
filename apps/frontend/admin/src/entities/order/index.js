// Public API for the order slice. Components and pages must import from this
// barrel — never reach into ./api/* or ./ui/* directly. ESLint enforces.

// UI
export { OrderCard } from './ui/OrderCard';
export { OrderDetailsView } from './ui/OrderDetailsView';
export { OrdersList } from './ui/OrdersList';
export { OrderStateHistoryTable } from './ui/OrderStateHistoryTable';
export { OrderTrackingTimeline } from './ui/OrderTrackingTimeline';
export { RecipientSnapshotPanel } from './ui/RecipientSnapshotPanel';
export { TopMetrics } from './ui/TopMetrics';

// PII masking helpers — used by RecipientSnapshotPanel and exported so
// future surfaces (audit logs, customs export) reuse the same policy.
export { formatInn, maskEmail, maskPassport, maskPhone } from './lib/mask';

// Domain constants
export {
  ORDER_STATUSES,
  ORDER_STATUS_LABELS,
  CUSTOMER_FACING_STATUS_LABELS,
  ORDER_STATUS_FILTER_GROUPS,
  ACTION_GATES,
  canPerformAction,
  HOLD_REASON_MAX,
  CANCEL_REASON_MAX,
  // typed enums (post-D0.1) — mirror backend `HoldReason` /
  // `CancellationReason` 1:1; consumers should always go through these
  // constants instead of hard-coding strings.
  HOLD_REASON_VALUES,
  HOLD_REASONS_FOR_ADMIN,
  HOLD_REASON_LABELS,
  holdReasonLabel,
  CANCELLATION_REASON_LABELS,
  CANCELLATION_CATEGORY_LABELS,
  cancellationReasonLabel,
  // legacy mock-driven labels kept for backward-compat with the order-filter
  // slice while it migrates off the in-memory mock array.
  STATUS_LABELS,
  STATUS_PILL_LABELS,
  REASON_FILTERS,
  REASON_FILTER_LABELS,
} from './lib/constants';
export { resolveOrderStatus } from './lib/orders';

// API — real BFF-backed by default. The dev-only mock fallback below is
// gated by NEXT_PUBLIC_FALLBACK_TO_MOCKS so a contributor running the admin
// without a live backend still sees a populated list/detail. The fallback
// is read-only — write operations always hit the real BFF (a no-op mock
// "mutation" would mask integration regressions).
import {
  listOrders as listOrdersReal,
  getOrderById as getOrderByIdReal,
  getOrderHistory as getOrderHistoryReal,
  getOrderTracking as getOrderTrackingReal,
  procureOrder,
  holdOrder,
  resumeOrder,
  forceCancelOrder,
  changePickupPoint,
  createWalkInOrder,
  validateIncomingDeclaration,
  generateIdempotencyKey,
  INCOMING_DECLARATION_RE,
} from './api/orders';

import * as ordersMock from './api/orders.mock';

// Build-time + runtime gate. We resolve at module init so each import gets
// the same wired functions; runtime hot-toggles aren't supported (would
// require a Provider, which is overkill for a dev-only escape hatch).
const SHOULD_FALLBACK_TO_MOCKS =
  process.env.NODE_ENV !== 'production' &&
  process.env.NEXT_PUBLIC_FALLBACK_TO_MOCKS === 'true';

async function listOrders(filters = {}) {
  if (!SHOULD_FALLBACK_TO_MOCKS) return listOrdersReal(filters);
  try {
    return await listOrdersReal(filters);
  } catch (err) {
    if (err?.status === 0 || err?.code === 'NETWORK_ERROR') {
      return {
        items: ordersMock.getOrders(),
        nextCursor: null,
      };
    }
    throw err;
  }
}

async function getOrderById(orderId) {
  if (!SHOULD_FALLBACK_TO_MOCKS) return getOrderByIdReal(orderId);
  try {
    return await getOrderByIdReal(orderId);
  } catch (err) {
    if (err?.status === 0 || err?.code === 'NETWORK_ERROR') {
      return ordersMock.getOrderById(orderId);
    }
    throw err;
  }
}

async function getOrderHistory(orderId) {
  if (!SHOULD_FALLBACK_TO_MOCKS) return getOrderHistoryReal(orderId);
  try {
    return await getOrderHistoryReal(orderId);
  } catch (err) {
    if (err?.status === 0 || err?.code === 'NETWORK_ERROR') return [];
    throw err;
  }
}

async function getOrderTracking(orderId) {
  if (!SHOULD_FALLBACK_TO_MOCKS) return getOrderTrackingReal(orderId);
  try {
    return await getOrderTrackingReal(orderId);
  } catch (err) {
    if (err?.status === 0 || err?.code === 'NETWORK_ERROR') return null;
    throw err;
  }
}

export {
  // Read
  listOrders,
  getOrderById,
  getOrderHistory,
  getOrderTracking,
  // Write — real backend only, no mock fallback
  procureOrder,
  holdOrder,
  resumeOrder,
  forceCancelOrder,
  changePickupPoint,
  createWalkInOrder,
  // Validation helpers
  validateIncomingDeclaration,
  generateIdempotencyKey,
  INCOMING_DECLARATION_RE,
};

// Legacy mock-only helper still used by the order-filter slice for in-memory
// status updates. Slated for removal once that slice migrates to TanStack
// mutations. Keep until the order-filter refactor below catches up.
export const updateOrderStatus = ordersMock.updateOrderStatus;

// TanStack Query hooks (read-only, write-side lives in features/order-actions)
export {
  useOrders,
  useOrder,
  useOrderHistory,
  useOrderTracking,
  useCancellationReasons,
} from './api/queries';

export { orderKeys } from './api/keys';
