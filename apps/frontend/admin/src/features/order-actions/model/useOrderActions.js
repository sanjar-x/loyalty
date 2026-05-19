'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import {
  changePickupPoint,
  forceCancelOrder,
  generateIdempotencyKey,
  holdOrder,
  orderKeys,
  procureOrder,
  resumeOrder,
} from '@/entities/order';

// Helper that invalidates every cache surface affected by an order
// mutation: the detail (toolbar gates re-evaluate), the list (FSM-state
// filters bucket the row differently), and the per-order history feed
// (a fresh transition just landed).
function invalidateOrderViews(qc, orderId) {
  qc.invalidateQueries({ queryKey: orderKeys.detail(orderId) });
  qc.invalidateQueries({ queryKey: orderKeys.history(orderId) });
  qc.invalidateQueries({ queryKey: orderKeys.lists() });
}

/**
 * Optimistic-update helper for write mutations whose only effect on the
 * cached detail is a status transition (hold/resume). We snapshot the
 * current detail, swap in the predicted status, and roll back on error.
 *
 * `predict(prev, variables)` receives the cached detail and the mutation
 * arguments; returning `null` skips the optimistic step (used when the
 * predicted shape isn't trivial — e.g. force-cancel could land in
 * cancelled/refunding/refunded depending on payment state).
 */
function withOptimisticDetail(qc, orderId, predict) {
  return {
    onMutate: async (variables) => {
      const detailKey = orderKeys.detail(orderId);
      await qc.cancelQueries({ queryKey: detailKey });
      const previous = qc.getQueryData(detailKey);
      if (previous) {
        const next = predict(previous, variables);
        if (next) qc.setQueryData(detailKey, next);
      }
      return { previous };
    },
    onError: (_err, _variables, context) => {
      if (context?.previous) {
        qc.setQueryData(orderKeys.detail(orderId), context.previous);
      }
    },
    onSettled: () => invalidateOrderViews(qc, orderId),
  };
}

export function useProcureOrder(orderId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ incomingDeclaration }) =>
      procureOrder(orderId, { incomingDeclaration }),
    ...withOptimisticDetail(qc, orderId, (prev, { incomingDeclaration }) => ({
      ...prev,
      status: 'procured',
      incomingDeclaration,
    })),
  });
}

export function useHoldOrder(orderId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ reason }) => holdOrder(orderId, { reason }),
    ...withOptimisticDetail(qc, orderId, (prev, { reason }) => ({
      ...prev,
      preHoldStatus: prev.status,
      status: 'on_hold',
      holdReason: reason,
      holdStartedAt: new Date().toISOString(),
    })),
  });
}

export function useResumeOrder(orderId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => resumeOrder(orderId),
    ...withOptimisticDetail(qc, orderId, (prev) => {
      if (prev.status !== 'on_hold' || !prev.preHoldStatus) return null;
      return {
        ...prev,
        status: prev.preHoldStatus,
        preHoldStatus: null,
        holdReason: null,
        holdStartedAt: null,
        holdUntil: null,
      };
    }),
  });
}

export function useForceCancelOrder(orderId) {
  const qc = useQueryClient();
  return useMutation({
    // The caller should pre-generate an idempotencyKey via
    // `generateIdempotencyKey()` so a retry doesn't spawn a second cancel.
    mutationFn: ({ reason, idempotencyKey }) =>
      forceCancelOrder(orderId, { reason, idempotencyKey }),
    // Cancel can land in cancelled / refunding / refunded depending on
    // the backend payment state — let the server tell us, no optimistic
    // status flip. Just refresh on settle.
    onSettled: () => invalidateOrderViews(qc, orderId),
  });
}

export function useChangePickupPoint(orderId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ carrier, pointId }) =>
      changePickupPoint(orderId, { carrier, pointId }),
    ...withOptimisticDetail(qc, orderId, (prev, { carrier, pointId }) => ({
      ...prev,
      pickupCarrier: carrier,
      pickupPointId: pointId,
    })),
  });
}

export { generateIdempotencyKey };
