// Order-actions — a deliberate *collection* feature.
//
// Why one slice instead of `order-procurement` / `order-hold-resume` /
// `order-force-cancel` / `order-pickup-change`: every modal here shares
// the same TanStack mutation plumbing (`invalidateOrderViews`,
// `withOptimisticDetail`). Splitting per-action would either duplicate
// the helpers four times or push them up into `entities/order/lib`,
// where they don't belong (they own cache-invalidation policy, which
// is a feature-layer concern).
//
// Rule of thumb if this folder keeps growing: split as soon as a new
// action does *not* share these helpers — e.g. a printable shipping
// label modal that just opens a window with no mutation.
//
// Imports from `entities/order` always go through the public barrel —
// never via deep paths (ESLint enforced).

export { ProcureModal } from './ui/ProcureModal';
export { HoldResumeModal } from './ui/HoldResumeModal';
export { ForceCancelModal } from './ui/ForceCancelModal';
export { ChangePickupPointModal } from './ui/ChangePickupPointModal';

export {
  useProcureOrder,
  useHoldOrder,
  useResumeOrder,
  useForceCancelOrder,
  useChangePickupPoint,
  generateIdempotencyKey,
} from './model/useOrderActions';
