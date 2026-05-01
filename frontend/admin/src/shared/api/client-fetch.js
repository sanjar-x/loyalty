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
//   import { apiClient } from '@/shared/api/client-fetch';
//
//   export function fetchBrands() {
//     return apiClient.get('/api/catalog/brands');
//   }

const DEFAULT_TIMEOUT_MS = 30_000;

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
    raw = false,
  } = {},
) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  // Compose abort signals: caller's + our timeout.
  if (signal) {
    if (signal.aborted) controller.abort();
    else
      signal.addEventListener('abort', () => controller.abort(), {
        once: true,
      });
  }

  const init = {
    method,
    credentials: 'include',
    signal: controller.signal,
    headers: {
      ...(body != null ? { 'Content-Type': 'application/json' } : {}),
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
    const err = data?.error ?? data?.detail ?? {};
    const rawMessage = err.message ?? `Ошибка сервера (${res.status})`;
    throw new ApiError({
      message: translate(rawMessage, translations) ?? rawMessage,
      code: err.code ?? 'UNKNOWN',
      status: res.status,
      details: err.details ?? {},
    });
  }

  return data;
}

export const apiClient = {
  get: (url, opts) => request(url, { ...opts, method: 'GET' }),
  post: (url, body, opts) => request(url, { ...opts, method: 'POST', body }),
  patch: (url, body, opts) => request(url, { ...opts, method: 'PATCH', body }),
  put: (url, body, opts) => request(url, { ...opts, method: 'PUT', body }),
  del: (url, opts) => request(url, { ...opts, method: 'DELETE' }),
};
