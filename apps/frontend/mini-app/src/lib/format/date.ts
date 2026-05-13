/**
 * Format ISO date string as Russian locale datetime.
 * @example formatRuDateTime("2026-04-05T12:00:00Z") => "05 апреля 2026, 15:00"
 */
export function formatRuDateTime(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Format ISO date as "До DD.MM.YYYY".
 * @example formatUntilDate("2026-04-05") => "До 05.04.2026"
 */
export function formatUntilDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const yyyy = String(d.getFullYear());
  return `До ${dd}.${mm}.${yyyy}`;
}
