/**
 * `BACKEND_API_BASE_URL` ni o'qiydigan yagona helper.
 *
 * BFF route'lar (`app/api/*`) shu yerdan import qiladi — ilgari bir xil
 * funksiya har route'da copy-paste qilingan edi (6 nusxa). Audit:
 * frontend-main, 2026-05-15.
 *
 * Server-only: `process.env` ga murojaat qiladi, client bundle'ga tushmaydi.
 * Trailing slash'lar olib tashlanadi (`.../`→`...`), shunda chaqiruvchi
 * `${base}/api/v1/...` ni xavfsiz yig'a oladi.
 *
 * Yo'q yoki bo'sh bo'lsa — `throw`. `logout` route esa "best-effort"
 * (backend chaqiruvi ixtiyoriy) — u o'zi `try/catch` bilan o'raydi.
 */
export function getBackendBaseUrl() {
  const raw = process.env.BACKEND_API_BASE_URL;
  if (!raw || typeof raw !== 'string' || !raw.trim()) {
    throw new Error('Missing BACKEND_API_BASE_URL');
  }
  return raw.trim().replace(/\/+$/, '');
}
