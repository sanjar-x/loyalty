/**
 * Date format helpers — a single bridge between the UI (RU `DD.MM.YYYY`)
 * and the backend ISO format (`YYYY-MM-DD`).
 *
 * The backend expects `CreateRecipientRequest.passportIssueDate` and
 * `birthDate` in ISO format (`format: "date"`). In the UI the user enters
 * them as `15.03.1990` — passing that straight to the payload makes the
 * backend return 422 and checkout reopens indefinitely (CHK-001).
 *
 * Functions are pure — no DOM/Intl references, easy to test.
 */

const MIN_YEAR = 1900;

function currentMaxYear() {
  return new Date().getFullYear() + 1;
}

/**
 * `DD.MM.YYYY` → `YYYY-MM-DD`. Validates the day via the real Date
 * constructor, so `31.02.1990` or `29.02.2023` → null. Year bounds:
 * 1900 ≤ year ≤ currentYear + 1 (one-year tolerance for a future issueDate;
 * for birthDate the cross-field validator checks separately).
 *
 * @param {string} value
 * @returns {string|null}
 */
export function parseRuDate(value) {
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  const match = /^(\d{2})\.(\d{2})\.(\d{4})$/.exec(trimmed);
  if (!match) return null;

  const day = Number(match[1]);
  const month = Number(match[2]);
  const year = Number(match[3]);

  if (year < MIN_YEAR || year > currentMaxYear()) return null;
  if (month < 1 || month > 12) return null;
  if (day < 1 || day > 31) return null;

  // The real Date constructor normalizes 31.02 → 02.03, so we compare the
  // returned components with the input — if they do not match, the date is
  // invalid (e.g. 29.02 in a non-leap year).
  const date = new Date(year, month - 1, day);
  if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day) {
    return null;
  }

  const mm = String(month).padStart(2, '0');
  const dd = String(day).padStart(2, '0');
  return `${year}-${mm}-${dd}`;
}

/**
 * `YYYY-MM-DD` → `DD.MM.YYYY`. Invalid input — empty string. Used to fill
 * the UI input with a recipient draft returned by the backend.
 *
 * @param {string} iso
 * @returns {string}
 */
export function toRuDate(iso) {
  if (typeof iso !== 'string') return '';
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso.trim());
  if (!match) return '';
  const [, yyyy, mm, dd] = match;
  return `${dd}.${mm}.${yyyy}`;
}

/**
 * Input mask: raw digits → `DD.MM.YYYY` (partial OK). Cursor position is not
 * managed — on every keystroke the input value is fully reformatted.
 * 8+ digits — truncated to 8.
 *
 * @param {string} value
 * @returns {string}
 */
export function formatRuDateMask(value) {
  if (typeof value !== 'string') return '';
  const digits = value.replace(/\D/g, '').slice(0, 8);
  if (digits.length <= 2) return digits;
  if (digits.length <= 4) return `${digits.slice(0, 2)}.${digits.slice(2)}`;
  return `${digits.slice(0, 2)}.${digits.slice(2, 4)}.${digits.slice(4)}`;
}
