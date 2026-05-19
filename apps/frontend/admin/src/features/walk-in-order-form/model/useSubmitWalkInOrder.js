'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { createWalkInOrder, orderKeys } from '@/entities/order';
import { useToast } from '@/shared/hooks/useToast';
import { formatCurrency } from '@/shared/lib/utils';

import { DEFAULT_CURRENCY } from '../lib/constants';

// `<input type="datetime-local">` returns a local-time string without a
// timezone. Sending it as-is means the backend (Pydantic naive UTC parse)
// shifts the payment record by the admin's UTC offset — a Moscow admin
// who picks "12:00" lands a record at 12:00Z = 15:00 MSK. Promote to a
// full ISO string with the user's offset baked in before submit. Returns
// `null` if the input is unparseable so the caller can drop the field
// and let backend `now()` win instead of submitting garbage.
function toIsoOrNull(localDateTimeString) {
  if (!localDateTimeString) return null;
  const t = new Date(localDateTimeString).getTime();
  if (Number.isNaN(t)) return null;
  return new Date(t).toISOString();
}

// Build the wire payload from form state. The form holds display-only
// snapshots (sku metadata, pickup label) that the backend doesn't want;
// strip them here so the schema check in `proxyToBackend` doesn't waste
// bytes and the request stays readable in devtools.
function buildPayload(state) {
  const paidAtIso = toIsoOrNull(state.payment.paidAt);
  return {
    profile: {
      fullName: state.profile.fullName.trim(),
      phone: state.profile.phone.trim(),
      ...(state.profile.email.trim()
        ? { email: state.profile.email.trim() }
        : {}),
    },
    recipient: {
      fullNameRu: state.recipient.fullNameRu.trim(),
      fullNameLat: state.recipient.fullNameLat.trim(),
      phone: state.recipient.phone.trim(),
      email: state.recipient.email.trim(),
      passportSerial: state.recipient.passportSerial,
      passportNumber: state.recipient.passportNumber,
      passportIssueDate: state.recipient.passportIssueDate,
      birthDate: state.recipient.birthDate,
      inn: state.recipient.inn,
    },
    items: state.items.map((it) => ({
      skuId: it.skuId,
      quantity: it.quantity,
      ...(it.unitPriceOverrideAmount != null
        ? {
            unitPriceOverrideAmount: it.unitPriceOverrideAmount,
            overrideReason: it.overrideReason?.trim() ?? '',
          }
        : {}),
    })),
    pickupCarrier: state.pickupCarrier,
    pickupPointId: state.pickupPointId,
    currency: DEFAULT_CURRENCY,
    payment: {
      method: state.payment.method,
      reference: state.payment.reference.trim(),
      // Empty / unparseable = "use server time". A long-open form would
      // otherwise ship a stale paidAt — let the backend pick `now()`.
      ...(paidAtIso ? { paidAt: paidAtIso } : {}),
    },
    idempotencyKey: state.idempotencyKey,
    deliveryAmount: state.deliveryAmount,
  };
}

// Translate a 422 ApiError from the backend into either a per-line
// highlight (returned via `itemErrors`) or a global form-level error.
// For WALK_IN_SKU_NOT_USABLE the details object names every offending
// SKU bucketed by reason; iterate every bucket so a new backend
// rejection reason still surfaces something instead of a silent toast.
// For PRICE_OVERRIDE_OUT_OF_RANGE backend names the single offending
// SKU plus the bound (kopecks).
const SKU_BUCKET_LABELS = {
  missing: 'Товар не найден',
  inactive: 'Товар деактивирован',
  unpriced: 'Цена не рассчитана. Дождитесь pricing recompute.',
  currencyMismatch: 'Валюта товара не совпадает с валютой заказа',
};

function mapErrorToFields(err) {
  if (!err || err.name !== 'ApiError') return null;

  if (err.code === 'WALK_IN_SKU_NOT_USABLE') {
    const details = err.details ?? {};
    const itemErrors = {};
    for (const [bucket, ids] of Object.entries(details)) {
      if (!Array.isArray(ids)) continue;
      const label = SKU_BUCKET_LABELS[bucket] ?? `Товар недоступен (${bucket})`;
      for (const skuId of ids) {
        itemErrors[skuId] = { kind: bucket, message: label };
      }
    }
    return Object.keys(itemErrors).length > 0 ? { itemErrors } : null;
  }

  if (err.code === 'PRICE_OVERRIDE_OUT_OF_RANGE') {
    const { skuId, basePrice, maxRatio } = err.details ?? {};
    if (!skuId) return null;
    const max =
      Number.isInteger(basePrice) && Number.isInteger(maxRatio)
        ? basePrice * maxRatio
        : null;
    return {
      itemErrors: {
        [skuId]: {
          kind: 'overrideOutOfRange',
          message: max
            ? `Допустимо 0 — ${formatCurrency(max / 100)}`
            : 'Цена выходит за допустимый диапазон',
        },
      },
    };
  }

  return null;
}

export function useSubmitWalkInOrder({ state, resetForm }) {
  const router = useRouter();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [itemErrors, setItemErrors] = useState({});
  const [globalError, setGlobalError] = useState(null);

  const mutation = useMutation({
    mutationFn: () => createWalkInOrder(buildPayload(state)),
    onMutate: () => {
      setItemErrors({});
      setGlobalError(null);
    },
    onSuccess: (data) => {
      const orderId = data?.orderId;
      // Backend regression / wire-format drift safety: if the response
      // doesn't carry orderId, the order *was* created (idempotency
      // cache now holds the submission) but we have nowhere to send the
      // admin. Don't reset — the form data is the only artifact they
      // have left for support to find the order. Render globalError
      // instead of navigating into /admin/orders/undefined.
      if (!orderId) {
        setGlobalError({
          code: 'INVALID_RESPONSE',
          message:
            'Заказ создан, но сервер не вернул идентификатор. Найдите заказ в списке /admin/orders.',
        });
        toast.warning('Заказ создан, но не удалось открыть его страницу');
        return;
      }
      // Invalidate the list cache so a back-button navigation to
      // /admin/orders shows the freshly-created order instead of stale
      // data.
      queryClient.invalidateQueries({ queryKey: orderKeys.lists() });
      toast.success('Заказ создан');
      resetForm();
      router.push(`/admin/orders/${orderId}`);
    },
    onError: (err) => {
      if (process.env.NODE_ENV !== 'production') {
        // Surface in devtools — TanStack doesn't log by default and the
        // generic toast hides the original stack on non-ApiError throws.
        console.error('[walk-in-order] submit failed', err);
      }
      const mapped = mapErrorToFields(err);
      if (mapped?.itemErrors) {
        setItemErrors(mapped.itemErrors);
      }
      // Non-ApiError throws (TypeError from a future refactor, etc.)
      // reach onError with their raw stack — sanitize to a generic
      // Russian message so the admin doesn't see English error text.
      const isApi = err?.name === 'ApiError';
      const message = isApi
        ? err.message || 'Не удалось создать заказ'
        : 'Не удалось создать заказ. Обновите страницу и попробуйте снова.';
      toast.error(message);
      setGlobalError({ code: err?.code, message, status: err?.status });
    },
  });

  return {
    submit: mutation.mutate,
    isPending: mutation.isPending,
    itemErrors,
    globalError,
    clearErrors: () => {
      setItemErrors({});
      setGlobalError(null);
    },
  };
}
