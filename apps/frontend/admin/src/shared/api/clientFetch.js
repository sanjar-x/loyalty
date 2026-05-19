// Canonical client-side fetch wrapper for BFF routes.
//
// Use from entities/*/api/*.js and features/*/api/*.js instead of calling
// fetch() directly. Handles:
//   - credentials: 'include' (cookies for JWT)
//   - JSON encoding/decoding
//   - 30s default timeout
//   - 429 Retry-After surfaced in error.retryAfter
//   - Russian error messages with optional translation map
//   - Unified Error shape: { message, code, status, details }
//
// Usage:
//   import { apiClient } from '@/shared/api/clientFetch';
//
//   export function fetchBrands() {
//     return apiClient.get('/api/catalog/brands');
//   }

import { getEtag, invalidateEtag, rememberEtag } from './etagStore';

const DEFAULT_TIMEOUT_MS = 30_000;

const MUTATING_METHODS = new Set(['POST', 'PATCH', 'PUT', 'DELETE']);

// Strip the query string before keying the ETag store. A `?cursor=abc`
// suffix shouldn't confuse the GET → PATCH round-trip (the server tags
// the resource, not the snapshot). Pass-through unchanged when the URL
// has no query.
function etagKey(url) {
  if (!url) return null;
  const qIdx = url.indexOf('?');
  return qIdx === -1 ? url : url.slice(0, qIdx);
}

const DEFAULT_ERROR_TRANSLATIONS = {
  'Not authenticated': 'Сессия истекла. Войдите заново.',
  'Backend service unreachable': 'Сервер недоступен. Попробуйте позже.',
  'Backend unavailable': 'Сервер недоступен. Попробуйте позже.',
  'Service unavailable': 'Сервис временно недоступен',
  'Image service unreachable': 'Сервис изображений недоступен',
};

export class ApiError extends Error {
  constructor({ message, code, status, details, retryAfter }) {
    super(message);
    this.name = 'ApiError';
    this.code = code ?? 'UNKNOWN';
    this.status = status ?? 0;
    this.details = details ?? {};
    if (retryAfter != null) this.retryAfter = retryAfter;
  }
}

function translate(message, extraTranslations) {
  if (!message) return null;
  return (
    extraTranslations?.[message] ?? DEFAULT_ERROR_TRANSLATIONS[message] ?? null
  );
}

// Code-keyed translation map. Preferred over message-keyed for new
// callers — backend domain codes (ORDER_*, BG_REMOVAL_*) are stable
// while the human messages may drift between releases. When a caller
// supplies both, code wins.
function translateByCode(code, translationsByCode) {
  if (!code || !translationsByCode) return null;
  return translationsByCode[code] ?? null;
}

/**
 * Low-level request. Most callers should prefer the typed helpers (`get`,
 * `post`, `patch`, `del`) on `apiClient` below.
 */
export async function request(
  url,
  {
    method = 'GET',
    body,
    headers,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    signal,
    translations,
    translationsByCode,
    raw = false,
  } = {},
) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  // Compose abort signals: caller's + our timeout. Capture the listener so
  // we can remove it explicitly in the success path — `{ once: true }` covers
  // the abort path, but a long-lived caller signal (e.g. a controller shared
  // across an entire useSubmitProduct transaction) would otherwise pile up
  // dead listeners as each request settles successfully.
  const onCallerAbort = () => controller.abort();
  if (signal) {
    if (signal.aborted) controller.abort();
    else signal.addEventListener('abort', onCallerAbort, { once: true });
  }
  const detachCallerAbort = () => {
    if (signal) signal.removeEventListener('abort', onCallerAbort);
  };

  // Auto-attach If-Match on mutating verbs when we have a cached ETag
  // for the same resource path. Caller-provided `headers['If-Match']`
  // wins (advanced callers can opt out by passing an empty string).
  const etagHeaders = {};
  const key = etagKey(url);
  if (MUTATING_METHODS.has(method) && key) {
    const cached = getEtag(key);
    if (cached) etagHeaders['If-Match'] = cached;
  }

  const init = {
    method,
    credentials: 'include',
    signal: controller.signal,
    headers: {
      ...(body != null ? { 'Content-Type': 'application/json' } : {}),
      ...etagHeaders,
      ...headers,
    },
    ...(body != null
      ? { body: typeof body === 'string' ? body : JSON.stringify(body) }
      : {}),
  };

  let res;
  try {
    res = await fetch(url, init);
  } catch (err) {
    clearTimeout(timeoutId);
    detachCallerAbort();
    if (err.name === 'AbortError') {
      throw new ApiError({
        message: 'Запрос превысил время ожидания. Проверьте соединение.',
        code: 'TIMEOUT',
        status: 0,
      });
    }
    throw new ApiError({
      message: 'Нет связи с сервером',
      code: 'NETWORK_ERROR',
      status: 0,
    });
  }

  clearTimeout(timeoutId);
  detachCallerAbort();

  // Capture the ETag header on successful GETs so the next mutating call
  // on the same path can attach If-Match. We capture before parsing the
  // body because the parse can throw on malformed JSON and we still want
  // the tag remembered for read flows.
  if (key && method === 'GET' && res.ok) {
    const tag = res.headers.get('ETag');
    if (tag) rememberEtag(key, tag);
  }

  // Mutating success → drop the cached ETag. The resource version moved
  // server-side; the next read repopulates the cache with the fresh tag.
  // (The 412 path below also invalidates so the user can refetch.)
  if (key && MUTATING_METHODS.has(method) && res.ok) {
    invalidateEtag(key);
  }

  if (res.status === 412 && key) {
    invalidateEtag(key);
    throw new ApiError({
      message:
        'Запись изменилась в другой вкладке. Обновите страницу и попробуйте снова.',
      code: 'OPTIMISTIC_LOCK_FAILED',
      status: 412,
    });
  }

  if (res.status === 429) {
    const retryAfter = Number.parseInt(
      res.headers.get('Retry-After') || '5',
      10,
    );
    throw new ApiError({
      message: `Слишком много запросов. Повторите через ${retryAfter} сек.`,
      code: 'RATE_LIMITED',
      status: 429,
      retryAfter,
    });
  }

  if (res.status === 204) {
    return null;
  }

  if (raw) return res;

  const data = await res.json().catch(() => null);

  if (!res.ok) {
    // Backend envelope: `{error: {code, message, details}}`. FastAPI default
    // (when an exception isn't translated) is `{detail: <string|object>}` —
    // detail can be a plain string for HTTPExceptions, or an object that
    // carries a code/message of its own. Normalise both shapes here so the
    // caller always gets an ApiError with a meaningful message.
    //
    // For the plain-string detail variant we infer a code from the HTTP
    // status — entity-level error dictionaries
    // (CustomerDetailModal/StaffDetailModal/RoleModal/CategoryModal/...) match
    // on `err.code` to pick the localized message; without a code they'd
    // silently fall back to whatever raw English string the backend emitted.
    let code = inferCodeFromStatus(res.status);
    let rawMessage = `Ошибка сервера (${res.status})`;
    let details = {};
    if (data && typeof data === 'object') {
      if (data.error && typeof data.error === 'object') {
        code = data.error.code ?? code;
        rawMessage = data.error.message ?? rawMessage;
        details = data.error.details ?? {};
      } else if (typeof data.detail === 'string') {
        rawMessage = data.detail;
      } else if (data.detail && typeof data.detail === 'object') {
        code = data.detail.code ?? code;
        rawMessage = data.detail.message ?? rawMessage;
        details = data.detail.details ?? {};
      }
    }
    throw new ApiError({
      message:
        translateByCode(code, translationsByCode) ??
        translate(rawMessage, translations) ??
        rawMessage,
      code,
      status: res.status,
      details,
    });
  }

  return data;
}

function inferCodeFromStatus(status) {
  switch (status) {
    case 400:
      return 'BAD_REQUEST';
    case 401:
      return 'UNAUTHORIZED';
    case 403:
      return 'FORBIDDEN';
    case 404:
      return 'NOT_FOUND';
    case 409:
      return 'CONFLICT';
    case 412:
      return 'OPTIMISTIC_LOCK_FAILED';
    case 422:
      return 'VALIDATION_ERROR';
    case 502:
    case 503:
      return 'SERVICE_UNAVAILABLE';
    default:
      return 'UNKNOWN';
  }
}

export const apiClient = {
  get: (url, opts) => request(url, { ...opts, method: 'GET' }),
  post: (url, body, opts) => request(url, { ...opts, method: 'POST', body }),
  patch: (url, body, opts) => request(url, { ...opts, method: 'PATCH', body }),
  put: (url, body, opts) => request(url, { ...opts, method: 'PUT', body }),
  del: (url, opts) => request(url, { ...opts, method: 'DELETE' }),
};
