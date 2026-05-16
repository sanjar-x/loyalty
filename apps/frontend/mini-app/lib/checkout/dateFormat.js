/**
 * Sana format yordamchilari — UI (RU `DD.MM.YYYY`) va backend ISO
 * (`YYYY-MM-DD`) o'rtasidagi yagona ko'prik.
 *
 * Backend `CreateRecipientRequest.passportIssueDate` va `birthDate` ISO
 * formatida kutadi (`format: "date"`). UI'da foydalanuvchi `15.03.1990`
 * shaklida kiritadi — to'g'ridan-to'g'ri payload'ga uzatilsa backend 422
 * qaytaradi va checkout cheksiz qayta ochiladi (CHK-001).
 *
 * Funksiyalar pure — DOM/Intl referensisiz, oson test qilinadi.
 */

const MIN_YEAR = 1900;

function currentMaxYear() {
  return new Date().getFullYear() + 1;
}

/**
 * `DD.MM.YYYY` → `YYYY-MM-DD`. Real Date konstruktor orqali kunni tasdiqlaydi,
 * shuning uchun `31.02.1990` yoki `29.02.2023` → null. Yil cheklovi:
 * 1900 ≤ year ≤ currentYear + 1 (kelajakda issueDate uchun bir yil tolerans,
 * birthDate uchun cross-field validator tashqarida tekshiradi).
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

  // Real Date konstruktor: 31.02 → 02.03 normalize qiladi, shuning uchun
  // qaytgan komponentalarni kirish bilan solishtiramiz — moslik bo'lmasa
  // sana yo'q (masalan 29.02 leap-bo'lmagan yilda).
  const date = new Date(year, month - 1, day);
  if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day) {
    return null;
  }

  const mm = String(month).padStart(2, '0');
  const dd = String(day).padStart(2, '0');
  return `${year}-${mm}-${dd}`;
}

/**
 * `YYYY-MM-DD` → `DD.MM.YYYY`. Yaroqsiz kirish — bo'sh string. Backend'dan
 * kelgan recipient draft'ni UI input'ga to'ldirish uchun ishlatiladi.
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
 * Input mask: raw digits → `DD.MM.YYYY` (partial OK). Kursor pozitsiyasi
 * boshqarilmaydi — har keystroke'da input value to'liq qayta-format qilinadi.
 * 8+ raqam — 8 ga truncate.
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
