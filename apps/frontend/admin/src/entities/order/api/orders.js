import { apiClient } from '@/shared/api/clientFetch';

// Russian translations keyed by backend `error.code`. The shared client-fetch
// translation map keys by message string (legacy product-flow convention)
// while orders prefer the code: the backend domain enums (ORDER_*) are stable
// across releases, the human messages may drift. The `withCodeTranslations`
// wrapper rewrites `err.message` post-throw based on `err.code` so callers
// see a translated message regardless of what the backend shipped in
// `message`. ApiError extends Error, so reassigning `err.message` is safe.
const ORDER_ERROR_TRANSLATIONS = {
  ORDER_NOT_FOUND: 'Заказ не найден',
  ORDER_INVALID_TRANSITION:
    'Действие недоступно для текущего статуса заказа. Обновите страницу.',
  ORDER_HOLD_STATE: 'Заказ уже в состоянии Hold',
  ORDER_NOT_HELD: 'Заказ не находится в состоянии Hold',
  ORDER_ALREADY_PROCURED: 'Заказ уже передан в закупку',
  ORDER_LASTMILE_CREATED:
    'Last-mile доставка уже создана — pickup point изменить нельзя',
  PICKUP_POINT_NOT_FOUND:
    'Указанный пункт выдачи не найден у выбранного перевозчика',
  IDEMPOTENCY_KEY_REUSE:
    'Этот idempotency-ключ уже использован. Сгенерируйте новый и попробуйте ещё раз.',
  // Walk-in (admin) creation — keep one human message per backend code so
  // toast policy is consistent. Field-level mapping (which SKU was unpriced,
  // which override was out-of-range) lives in the walk-in feature mutation;
  // these strings only cover the case where the UI falls back to a global
  // toast.
  WALK_IN_SKU_NOT_USABLE:
    'Один или несколько товаров недоступны для walk-in заказа. Проверьте подсветку в списке.',
  PRICE_OVERRIDE_OUT_OF_RANGE:
    'Цена выходит за допустимый диапазон. Проверьте поле с подсветкой.',
  ORDER_EMPTY: 'Добавьте хотя бы один товар',
  ORDER_ITEM_QUANTITY_ERROR: 'Количество товара должно быть от 1 до 99',
  ORDER_DELIVERY_AMOUNT_INVALID:
    'Стоимость доставки не может быть отрицательной',
  IDEMPOTENCY_KEY_CONFLICT:
    'Этот ключ уже использован с другим набором данных. Обновите страницу и попробуйте снова.',
  INSUFFICIENT_PERMISSIONS:
    'У вас нет права создавать walk-in заказы. Обратитесь к администратору.',
};

async function withCodeTranslations(promise) {
  try {
    return await promise;
  } catch (err) {
    if (err && err.code && ORDER_ERROR_TRANSLATIONS[err.code]) {
      err.message = ORDER_ERROR_TRANSLATIONS[err.code];
    }
    throw err;
  }
}

// ---------------------------------------------------------------------------
// Meta endpoints — static taxonomy fetched once per session
// ---------------------------------------------------------------------------

/**
 * Cancellation-reason taxonomy. Backend returns
 *   `{ categories: [{ code, reasons: [...] }, ...] }`
 * with the partition matching :class:`order.domain.value_objects.CancellationCategory`.
 *
 * Wrapped in `withCodeTranslations` so the same toast policy applies if
 * the backend ever surfaces an error for this lookup (currently always
 * 200 — admin permission gates upstream).
 */
export function fetchCancellationReasonsMeta() {
  return withCodeTranslations(
    apiClient.get('/api/admin/orders/meta/cancellation-reasons'),
  );
}

// ---------------------------------------------------------------------------
// Read endpoints
// ---------------------------------------------------------------------------

export function listOrders({ statuses, limit = 50, cursor } = {}) {
  const params = new URLSearchParams();
  params.set('limit', String(limit));
  if (cursor) params.set('cursor', cursor);
  if (Array.isArray(statuses)) {
    for (const s of statuses) {
      if (s) params.append('statuses', s);
    }
  }
  return withCodeTranslations(
    apiClient.get(`/api/admin/orders?${params.toString()}`),
  );
}

export function getOrderById(orderId) {
  return withCodeTranslations(apiClient.get(`/api/admin/orders/${orderId}`));
}

export function getOrderHistory(orderId) {
  return withCodeTranslations(
    apiClient.get(`/api/admin/orders/${orderId}/history`),
  );
}

// Tracking endpoint is currently the customer-facing one
// (`/api/v1/orders/{id}/tracking`), proxied through `/api/admin/orders/.../tracking`
// on the BFF for consistent ownership-aware auth. If backend exposes a
// dedicated admin variant later the BFF is the only thing that needs to flip.
export function getOrderTracking(orderId) {
  return withCodeTranslations(
    apiClient.get(`/api/admin/orders/${orderId}/tracking`),
  );
}

// ---------------------------------------------------------------------------
// Write endpoints (all return 204 — apiClient resolves to null on 204)
// ---------------------------------------------------------------------------

export function procureOrder(orderId, { incomingDeclaration }) {
  return withCodeTranslations(
    apiClient.post(`/api/admin/orders/${orderId}/procure`, {
      incomingDeclaration,
    }),
  );
}

export function holdOrder(orderId, { reason }) {
  return withCodeTranslations(
    apiClient.post(`/api/admin/orders/${orderId}/hold`, { reason }),
  );
}

export function resumeOrder(orderId) {
  return withCodeTranslations(
    apiClient.post(`/api/admin/orders/${orderId}/resume`),
  );
}

export function forceCancelOrder(orderId, { reason, idempotencyKey }) {
  return withCodeTranslations(
    apiClient.post(`/api/admin/orders/${orderId}/force-cancel`, {
      reason,
      idempotencyKey,
    }),
  );
}

export function changePickupPoint(orderId, { carrier, pointId }) {
  return withCodeTranslations(
    apiClient.patch(`/api/admin/orders/${orderId}/pickup-point`, {
      carrier,
      pointId,
    }),
  );
}

// Walk-in (admin offline) order creation. Body shape matches the backend
// AdminCreateWalkInOrderRequest schema 1:1 (camelCase per REFACT-001). The
// caller owns `idempotencyKey` lifecycle — generate at form mount via
// `generateIdempotencyKey()` and reuse the same key across retries so the
// backend's 24h idempotency cache returns the original 201 instead of
// double-creating the order.
//
// Returns 201 with `{orderId, identityId, totalAmount, currency}`.
//
// Error envelope is unwrapped to an `ApiError` by `apiClient` — the
// walk-in mutation hook in `features/walk-in-order-form` consumes
// `err.code` + `err.details` to drive field-level highlighting, and the
// global toast falls back to the translated message above.
export function createWalkInOrder(payload) {
  return withCodeTranslations(apiClient.post('/api/admin/orders', payload));
}

// ---------------------------------------------------------------------------
// Local validation helpers (mirrors backend domain rules without a 422 round-trip)
// ---------------------------------------------------------------------------

// Backend domain regex for the Chinese incoming declaration; the OpenAPI
// schema only carries minLength/maxLength so we enforce the character-class
// constraint here so the user gets immediate feedback instead of a delayed 422.
export const INCOMING_DECLARATION_RE = /^[A-Za-z0-9-]{1,15}$/;

export function validateIncomingDeclaration(value) {
  if (typeof value !== 'string') return false;
  return INCOMING_DECLARATION_RE.test(value);
}

// idempotencyKey: 8..128 chars per backend `CancelOrderRequest`. We let the
// caller generate it (`crypto.randomUUID()` works — 36 chars within range).
export function generateIdempotencyKey() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `idem-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
}
