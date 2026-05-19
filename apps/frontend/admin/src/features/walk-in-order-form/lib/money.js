// Money input helpers for the walk-in form.
//
// State holds kopecks (backend smallest unit) to keep integer math safe
// when summing line totals. UI inputs accept rubles — the conversion
// happens here at the boundary, matching the convention documented in
// `shared/ui/MoneyInput`. Both inputs and labels speak rubles; only the
// outgoing payload sees kopecks.
//
// Decimal kopecks (e.g. 12.50 ₽) are intentionally rejected for the
// walk-in MVP: backend wants integer kopecks, and the offline-cash use
// case rarely needs sub-ruble precision. A future iteration can add
// decimal parsing once the UX is validated.

const MAX_SAFE_KOPECKS = Number.MAX_SAFE_INTEGER;

// String → integer kopecks. Accepts plain digits (rubles). Returns null
// for invalid input so the caller can decide whether to keep the prior
// state value or zero it out.
export function parseRublesToKopecks(input) {
  if (typeof input !== 'string') return null;
  const digits = input.replace(/\D/g, '');
  if (digits === '') return 0;
  const rubles = Number.parseInt(digits, 10);
  if (!Number.isSafeInteger(rubles)) return null;
  const kopecks = rubles * 100;
  if (kopecks > MAX_SAFE_KOPECKS) return null;
  return kopecks;
}

// Integer kopecks → string of rubles ready to drop into an <input value>.
// Truncates fractional kopecks (rounding down) — the form only enters
// whole rubles, so a fractional value means something else wrote to state.
export function formatKopecksForInput(kopecks) {
  if (!Number.isFinite(kopecks) || kopecks <= 0) return '';
  return String(Math.floor(kopecks / 100));
}
