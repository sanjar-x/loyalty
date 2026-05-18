/**
 * Single helper that reads `BACKEND_API_BASE_URL`.
 *
 * BFF routes (`app/api/*`) import it from here — previously the same function
 * was copy-pasted in every route (6 copies). Audit: frontend-main, 2026-05-15.
 *
 * Server-only: accesses `process.env`, does not end up in the client bundle.
 * Trailing slashes are stripped (`.../`→`...`), so the caller can safely
 * assemble `${base}/api/v1/...`.
 *
 * If missing or empty — `throw`. The `logout` route is "best-effort"
 * (calling the backend is optional) — it wraps the call in `try/catch` itself.
 */
export function getBackendBaseUrl() {
  const raw = process.env.BACKEND_API_BASE_URL;
  if (!raw || typeof raw !== 'string' || !raw.trim()) {
    throw new Error('Missing BACKEND_API_BASE_URL');
  }
  return raw.trim().replace(/\/+$/, '');
}
