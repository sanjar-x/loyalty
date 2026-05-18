/**
 * Phone helpers — CIS country formats (RU/KZ/BY/UZ/UA).
 *
 * Sprint 2: moved out of shared/lib/validators (which held checkout
 * business validation). Phone is generic plumbing — usable from any form.
 *
 * libphonenumber-js — next iteration (P3 ticket).
 *
 *  • prefix       — E.164 country code (`+7`, `+998`, ...)
 *  • prefixDigits — digits of the prefix
 *  • lenAfter     — number of digits after the prefix
 *  • firstDigit   — first digit of the operator code (`null` — no restriction)
 *  • placeholder  — UI input placeholder
 *  • grouping     — digit groups used for formatting (each is a length)
 *  • separators   — characters between groups
 */
export const PHONE_FORMATS = Object.freeze({
  RU: {
    prefix: '+7',
    prefixDigits: '7',
    lenAfter: 10,
    firstDigit: '9',
    placeholder: '+7 9XX XXX-XX-XX',
    grouping: [3, 3, 2, 2],
    separators: [' ', '-', '-'],
  },
  KZ: {
    prefix: '+7',
    prefixDigits: '7',
    lenAfter: 10,
    firstDigit: '7',
    placeholder: '+7 7XX XXX-XX-XX',
    grouping: [3, 3, 2, 2],
    separators: [' ', '-', '-'],
  },
  BY: {
    prefix: '+375',
    prefixDigits: '375',
    lenAfter: 9,
    firstDigit: null,
    placeholder: '+375 XX XXX-XX-XX',
    grouping: [2, 3, 2, 2],
    separators: [' ', '-', '-'],
  },
  UZ: {
    prefix: '+998',
    prefixDigits: '998',
    lenAfter: 9,
    firstDigit: null,
    placeholder: '+998 XX XXX-XX-XX',
    grouping: [2, 3, 2, 2],
    separators: [' ', '-', '-'],
  },
  UA: {
    prefix: '+380',
    prefixDigits: '380',
    lenAfter: 9,
    firstDigit: null,
    placeholder: '+380 XX XXX-XX-XX',
    grouping: [2, 3, 2, 2],
    separators: [' ', '-', '-'],
  },
});

export const SUPPORTED_PHONE_COUNTRIES = Object.freeze(Object.keys(PHONE_FORMATS));

export function resolvePhoneFormat(country) {
  return PHONE_FORMATS[country] || PHONE_FORMATS.RU;
}

/**
 * Raw input → pure operator digits. The country prefix and the RU "8" trunk
 * prefix are stripped automatically.
 */
export function normalizePhoneDigits(input, country = 'RU') {
  const fmt = resolvePhoneFormat(country);
  const raw = String(input || '');
  let digits = raw.replace(/\D/g, '');
  if (!digits) return '';

  if (raw.trim().startsWith('+')) {
    if (digits.startsWith(fmt.prefixDigits)) {
      digits = digits.slice(fmt.prefixDigits.length);
    }
  }

  if (digits.length > fmt.lenAfter && digits.startsWith(fmt.prefixDigits)) {
    digits = digits.slice(fmt.prefixDigits.length);
  }

  if (country === 'RU' && digits.length > fmt.lenAfter && digits.startsWith('8')) {
    digits = digits.slice(1);
  }

  return digits.slice(0, fmt.lenAfter);
}

/**
 * Operator digits → display string per the country convention.
 * `formatPhone("9880001122", "RU")` → `"+7 988 000-11-22"`
 */
export function formatPhone(digits, country = 'RU') {
  const fmt = resolvePhoneFormat(country);
  const d = String(digits || '')
    .replace(/\D/g, '')
    .slice(0, fmt.lenAfter);
  if (!d) return '';

  let out = fmt.prefix;
  let offset = 0;
  for (let i = 0; i < fmt.grouping.length; i++) {
    const len = fmt.grouping[i];
    const part = d.slice(offset, offset + len);
    if (!part) break;
    const sep = i === 0 ? ' ' : fmt.separators[i - 1] || ' ';
    out += `${sep}${part}`;
    offset += len;
    if (offset >= d.length) break;
  }
  return out;
}
