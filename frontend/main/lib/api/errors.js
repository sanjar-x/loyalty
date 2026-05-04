/**
 * Backend error envelope helpers.
 *
 * Spec: SPEC - Frontend Integration Guide §3 — barcha xatolar yagona
 * formatda:
 *   { error: { code, message, details, request_id } }
 *
 * `normalizeApiError` RTK Query `result.error` (`{status, data}`) ni qabul
 * qilib, kanonik shape qaytaradi. UI yoki baseQuery undan code/message ni
 * o'qib, mos handler'ni chaqiradi.
 */

const TOKEN_EXPIRY_CODES = new Set([
  "TOKEN_EXPIRED",
  "TOKEN_VERSION_STALE",
  "INVALID_TOKEN",
  "MISSING_TOKEN",
  "IDENTITY_INVALID",
]);

const QUOTE_EXPIRY_CODES = new Set(["QUOTE_EXPIRED", "QUOTE_NOT_FOUND"]);

const PROVIDER_RETRY_CODES = new Set([
  "RATE_CALCULATION_ERROR",
  "BOOKING_ERROR",
  "PROVIDER_UNAVAILABLE",
  "BOOKING_PENDING",
]);

export function normalizeApiError(rtkError) {
  if (!rtkError || typeof rtkError !== "object") {
    return { status: 0, code: "", message: "", details: null, requestId: "" };
  }

  const status =
    typeof rtkError.status === "number" ? rtkError.status : 0;
  const data = rtkError.data;

  // FETCH_ERROR / TIMEOUT_ERROR — RTK Query internal xatolari
  if (typeof rtkError.status === "string") {
    return {
      status: 0,
      code: rtkError.status,
      message: typeof rtkError.error === "string" ? rtkError.error : "",
      details: null,
      requestId: "",
    };
  }

  // Backend canonical envelope
  if (data && typeof data === "object" && data.error && typeof data.error === "object") {
    const e = data.error;
    return {
      status,
      code: typeof e.code === "string" ? e.code : "",
      message: typeof e.message === "string" ? e.message : "",
      details: e.details ?? null,
      requestId: typeof e.request_id === "string" ? e.request_id : "",
    };
  }

  // BFF helper xatolari (`{error: "..."}`) yoki Pydantic 422 detail array
  if (data && typeof data === "object") {
    const message =
      typeof data.error === "string"
        ? data.error
        : typeof data.detail === "string"
          ? data.detail
          : "";
    return {
      status,
      code: "",
      message,
      details: data.detail ?? data.details ?? null,
      requestId: "",
    };
  }

  return {
    status,
    code: "",
    message: typeof data === "string" ? data : "",
    details: null,
    requestId: "",
  };
}

export function isTokenExpiredError(rtkError) {
  const e = normalizeApiError(rtkError);
  if (e.status === 401) return true;
  return TOKEN_EXPIRY_CODES.has(e.code);
}

export function isQuoteExpiredError(rtkError) {
  const e = normalizeApiError(rtkError);
  return QUOTE_EXPIRY_CODES.has(e.code);
}

export function isProviderRetryableError(rtkError) {
  const e = normalizeApiError(rtkError);
  if (PROVIDER_RETRY_CODES.has(e.code)) return true;
  return e.status === 502 || e.status === 503;
}

/**
 * UI-friendly user-visible string. Code'ga qarab i18n kalit qaytaradi —
 * agar UI darajasida i18n bor bo'lsa shuni ishlatadi, aks holda raw message.
 */
export function humanizeApiError(rtkError, fallback = "Что-то пошло не так") {
  const e = normalizeApiError(rtkError);
  return e.message || fallback;
}
