/**
 * Ruble float → display string (`"1 599 ₽"`). Truncates the fractional part
 * (15.99 → "15 ₽"). NaN/Infinity → empty string by default.
 *
 * Single canonical implementation across the project — previously there were
 * 11 local `formatRub` copies (different NaN handling, separators, '₽'
 * placement). Sprint 1.2 dedup.
 *
 * For the new Money primitive (kopecks-aware) — see `formatMoney(money)` in `./money`.
 *
 * @param {number} value ruble float
 * @param {object} [opts]
 * @param {string} [opts.empty=''] value returned for NaN/Infinity ('—' or '')
 * @returns {string}
 */
export function formatRub(value, opts = {}) {
  const n = Number(value);
  if (!Number.isFinite(n)) return opts.empty ?? '';
  const rounded = Math.trunc(n);
  const formatted = rounded.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  return `${formatted} ₽`;
}

/** Legacy name — kept for backwards compat; new code uses `formatRub`. */
export const formatRubFloat = formatRub;

/**
 * Compact format `15 000 → "15к ₽"`, `1 500 → "1,5к ₽"`, `&lt;1000` stays as-is.
 * For `installment plan` and other tight spots. NaN → ''.
 */
export function formatRubCompact(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) return '';
  if (n < 1000) return formatRub(n);
  const k = n / 1000;
  const display = k >= 10 ? Math.round(k).toString() : k.toFixed(1).replace('.', ',').replace(/,0$/, '');
  return `${display}к ₽`;
}
