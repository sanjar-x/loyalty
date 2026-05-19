/**
 * Format a backend `passportIssueDate` (ISO `YYYY-MM-DD`) for display.
 *
 *   formatPassportIssueDate('1995-06-12') → '12.06.1995'
 *   formatPassportIssueDate('') → ''
 *   formatPassportIssueDate(null) → ''
 *
 * Pure helper, locale-agnostic — we keep the ru-RU DD.MM.YYYY canonical
 * form that the UI elsewhere uses (see `shared/lib/date-format`). Not
 * routed through Intl.DateTimeFormat to avoid pulling timezone state
 * for what is fundamentally a calendar date.
 */
export function formatPassportIssueDate(iso) {
  if (typeof iso !== 'string') return '';
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso.trim());
  if (!match) return '';
  const [, yyyy, mm, dd] = match;
  return `${dd}.${mm}.${yyyy}`;
}
