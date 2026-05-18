/**
 * Backend error envelope helpers.
 *
 * Spec: SPEC - Frontend Integration Guide §3 — all errors come in a single
 * format:
 *   { error: { code, message, details, request_id } }
 *
 * `normalizeApiError` takes the RTK Query `result.error` (`{status, data}`)
 * and returns a canonical shape. The UI or baseQuery reads code/message from
 * it and dispatches the appropriate handler.
 */

const TOKEN_EXPIRY_CODES = new Set([
  'TOKEN_EXPIRED',
  'TOKEN_VERSION_STALE',
  'INVALID_TOKEN',
  'MISSING_TOKEN',
  'IDENTITY_INVALID',
]);

// Sprint 2.2: checkout-specific error codes (QUOTE_*, PROVIDER_*,
// CURRENCY_*) moved to features/checkout-flow/lib/errors — those belong
// to a business domain, not "transport plumbing". Only token + transport
// codes remain here.

export function normalizeApiError(rtkError) {
  if (!rtkError || typeof rtkError !== 'object') {
    return { status: 0, code: '', message: '', details: null, requestId: '' };
  }

  const status = typeof rtkError.status === 'number' ? rtkError.status : 0;
  const data = rtkError.data;

  // FETCH_ERROR / TIMEOUT_ERROR — RTK Query internal errors
  if (typeof rtkError.status === 'string') {
    return {
      status: 0,
      code: rtkError.status,
      message: typeof rtkError.error === 'string' ? rtkError.error : '',
      details: null,
      requestId: '',
    };
  }

  // Backend canonical envelope
  if (data && typeof data === 'object' && data.error && typeof data.error === 'object') {
    const e = data.error;
    return {
      status,
      code: typeof e.code === 'string' ? e.code : '',
      message: typeof e.message === 'string' ? e.message : '',
      details: e.details ?? null,
      requestId: typeof e.request_id === 'string' ? e.request_id : '',
    };
  }

  // BFF helper errors (`{error: "..."}`) or a Pydantic 422 detail array
  if (data && typeof data === 'object') {
    const message =
      typeof data.error === 'string'
        ? data.error
        : typeof data.detail === 'string'
          ? data.detail
          : '';
    return {
      status,
      code: '',
      message,
      details: data.detail ?? data.details ?? null,
      requestId: '',
    };
  }

  return {
    status,
    code: '',
    message: typeof data === 'string' ? data : '',
    details: null,
    requestId: '',
  };
}

export function isTokenExpiredError(rtkError) {
  const e = normalizeApiError(rtkError);
  if (e.status === 401) return true;
  return TOKEN_EXPIRY_CODES.has(e.code);
}

/**
 * UI-friendly user-visible string. Returns an i18n key based on the code —
 * the UI uses it if i18n is available; otherwise it falls back to the raw message.
 */
export function humanizeApiError(rtkError, fallback = 'Что-то пошло не так') {
  const e = normalizeApiError(rtkError);
  return e.message || fallback;
}
