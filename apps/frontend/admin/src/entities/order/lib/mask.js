/**
 * Recipient PII masking helpers — admin-side only.
 *
 * Backend (`RecipientSnapshotSchema`) freezes the customs-required PII at
 * checkout (passport, INN, birth date, etc.). Admin still needs to verify
 * those fields against the China-side invoice during procure, so the panel
 * shows partial values: enough for a sanity check, not enough to leak the
 * full document number into a screen recording. INN stays unmasked — it is
 * legally required at full precision for the customs declaration.
 */

const PASSPORT_PLACEHOLDER = '**** ****';
const PHONE_PLACEHOLDER = '+7 (***) ***-**-**';
const EMAIL_PLACEHOLDER = '***@***';

function safeStr(value) {
  return typeof value === 'string' ? value : '';
}

/**
 * Russian internal passport: 4-digit serial + 6-digit number.
 * Mask: `**XX **XXXX` — last 2 of serial, last 4 of number.
 *
 * Falls back to `**** ****` when either component is missing or shorter
 * than the safe slice length so we never accidentally leak the full value.
 */
export function maskPassport(serial, number) {
  const s = safeStr(serial);
  const n = safeStr(number);
  if (s.length < 2 || n.length < 4) return PASSPORT_PLACEHOLDER;
  return `**${s.slice(-2)} **${n.slice(-4)}`;
}

/**
 * Phone — Russian mobile (E.164 `+7XXXXXXXXXX`, 11 digits without `+`).
 * Mask: `+7 (***) ***-XX-XX` — last 4 digits split into two pairs.
 *
 * `slice(-4, -2)` and `slice(-2)` operate on the raw digits so a stray
 * formatting character (`+`, ` `, `-`) at the tail would still safely fall
 * through to the placeholder.
 */
export function maskPhone(phone) {
  const digits = safeStr(phone).replace(/\D/g, '');
  if (digits.length < 4) return PHONE_PLACEHOLDER;
  return `+7 (***) ***-${digits.slice(-4, -2)}-${digits.slice(-2)}`;
}

/**
 * Email — keep first letter of local part + last letter of local part +
 * full domain. Single-character locals fall back to a stricter mask that
 * just shows the domain.
 *
 * Examples:
 *   `john.doe@example.com` → `j***e@example.com`
 *   `j@example.com`        → `***@example.com`
 *   `invalid`              → `***@***`
 */
export function maskEmail(email) {
  const value = safeStr(email);
  const atIdx = value.indexOf('@');
  if (atIdx <= 0) return EMAIL_PLACEHOLDER;
  const local = value.slice(0, atIdx);
  const domain = value.slice(atIdx + 1);
  if (!domain) return EMAIL_PLACEHOLDER;
  if (local.length < 2) return `***@${domain}`;
  return `${local[0]}***${local.slice(-1)}@${domain}`;
}

/**
 * INN is intentionally NOT masked. Admin role gates access to the panel,
 * and the customs declaration requires the full 12-digit value. Exporting
 * a no-op identity helper keeps the call site symmetrical with the masked
 * fields and gives us a single seam if we ever change the policy.
 */
export function formatInn(inn) {
  return safeStr(inn);
}
