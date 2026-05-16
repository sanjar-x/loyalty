/**
 * Checkout form validators va formatter'lari.
 *
 * Pure funksiyalar — hech qanday DOM/window referensisiz, oson test qilinadi.
 * `app/checkout/page.jsx` ichida inline yozilgan logika shu yerga ajratilgan.
 */

import { parseRuDate } from './dateFormat';

/* ── Card helpers ── */

export function normalizeCardNumberDigits(input) {
  return (input || '').replace(/\D/g, '').slice(0, 19);
}

export function formatCardNumber(digits) {
  const d = (digits || '').replace(/\D/g, '');
  return d.replace(/(.{4})/g, '$1 ').trim();
}

export function normalizeExpiry(value) {
  const digits = (value || '').replace(/\D/g, '').slice(0, 4);
  const mm = digits.slice(0, 2);
  const yy = digits.slice(2, 4);
  return yy ? `${mm}/${yy}` : mm;
}

export function isValidLuhn(numberDigits) {
  const digits = (numberDigits || '').replace(/\D/g, '');
  if (digits.length < 12) return false;
  let sum = 0;
  let shouldDouble = false;
  for (let i = digits.length - 1; i >= 0; i--) {
    let digit = Number(digits[i]);
    if (Number.isNaN(digit)) return false;
    if (shouldDouble) {
      digit *= 2;
      if (digit > 9) digit -= 9;
    }
    sum += digit;
    shouldDouble = !shouldDouble;
  }
  return sum % 10 === 0;
}

/* ── Phone helpers (CIS countries) ── */

/**
 * CHK-002: kontrakt mahalliy validatsiya uchun. libphonenumber-js
 * integratsiyasi P3 alohida ticket — hozircha qo'lda 5 country.
 *
 *  • prefix       — E.164 mamlakat kodi (`+7`, `+998`, ...)
 *  • prefixDigits — prefix raqamlari (1..3) `8XXX`/`7XXX` paste strip uchun
 *  • lenAfter     — prefiks tashqarisidagi raqamlar soni
 *  • firstDigit   — operator kodining birinchi raqami (`null` — cheklov yo'q)
 *  • placeholder  — UI input placeholder
 *  • grouping     — formatlash uchun raqam guruhlari (har biri o'lcham)
 *  • separators   — guruhlar orasidagi belgilar (`grouping.length - 1`)
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

function resolveFormat(country) {
  return PHONE_FORMATS[country] || PHONE_FORMATS.RU;
}

/**
 * Raw input → pure operator digits. Country prefix (`+7`, `+998`, ...) va
 * RU "8" trunk prefix avtomatik ajratiladi, natija to'g'ridan operator
 * raqamlari (`lenAfter` ga truncate). Country o'zgartirilsa wider input
 * qabul qilinishi mumkin — UI tomondan ham clamp qilinadi.
 */
export function normalizePhoneDigits(input, country = 'RU') {
  const fmt = resolveFormat(country);
  const raw = String(input || '');
  let digits = raw.replace(/\D/g, '');
  if (!digits) return '';

  // E.164 prefix strip (`+7XXX...`, `+998XXX...`)
  if (raw.trim().startsWith('+')) {
    if (digits.startsWith(fmt.prefixDigits)) {
      digits = digits.slice(fmt.prefixDigits.length);
    }
  }

  // Cleared paste: prefiks raqamlari (`7XXX`, `998XXX`) kelishi mumkin.
  if (digits.length > fmt.lenAfter && digits.startsWith(fmt.prefixDigits)) {
    digits = digits.slice(fmt.prefixDigits.length);
  }

  // RU specifik: `8XXX...` trunk prefix → operator raqamlari.
  if (country === 'RU' && digits.length > fmt.lenAfter && digits.startsWith('8')) {
    digits = digits.slice(1);
  }

  return digits.slice(0, fmt.lenAfter);
}

/**
 * Operator digits → display string country konvensiyasi bilan.
 * Misol: `formatPhone("9880001122", "RU")` → `"+7 988 000-11-22"`.
 * Partial input progressiv formatlanadi: foydalanuvchi yozayotgan paytda
 * cursor mantiqi `<input value={formatPhone(digits)} />` ishlatadigan
 * tarzda barqaror (har keystroke da to'liq qayta format).
 */
export function formatPhone(digits, country = 'RU') {
  const fmt = resolveFormat(country);
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

/* ── Validators ── */

/**
 * Card draft validator. Returns `{ field: 'required' | 'invalid' }` map.
 * Empty object — valid.
 */
export function validateCardDraft(draft) {
  const errors = {};

  const numberDigits = normalizeCardNumberDigits(draft?.numberDigits);
  if (!numberDigits) {
    errors.numberDigits = 'required';
  } else if (numberDigits.length < 16 || numberDigits.length > 19) {
    errors.numberDigits = 'invalid';
  } else if (!isValidLuhn(numberDigits)) {
    errors.numberDigits = 'invalid';
  }

  const exp = normalizeExpiry(draft?.exp);
  if (!exp) {
    errors.exp = 'required';
  } else if (!/^\d{2}\/\d{2}$/.test(exp)) {
    errors.exp = 'invalid';
  } else {
    const [mmStr, yyStr] = exp.split('/');
    const mm = Number(mmStr);
    const yy = Number(yyStr);
    if (mm < 1 || mm > 12 || Number.isNaN(yy)) {
      errors.exp = 'invalid';
    }
  }

  const cvc = (draft?.cvc || '').replace(/\D/g, '').slice(0, 4);
  if (!cvc) {
    errors.cvc = 'required';
  } else if (cvc.length < 3) {
    errors.cvc = 'invalid';
  }

  const holder = (draft?.holder || '').trim();
  if (!holder) {
    errors.holder = 'required';
  } else {
    const ok = /^[A-Za-zА-Яа-яЁё\s-]+$/.test(holder);
    if (!ok || holder.replace(/\s+/g, ' ').length < 3) {
      errors.holder = 'invalid';
    }
  }

  return errors;
}

/**
 * Recipient (получатель) validator (CHK-002).
 *
 * `draft.country` — RU/BY/KZ/UZ/UA (default RU). Phone validatsiyasi shu
 * mamlakatga mos `PHONE_FORMATS` qoidasini ishlatadi (uzunlik + ixtiyoriy
 * `firstDigit`).
 *
 * ФИО — 2..5 so'z, kirilcha + lotin + apostrof/hyphen ruxsat etilgan
 * (CIS familiyalari va xorijiy mehmonlar uchun).
 *
 * Email — global RFC-ga yaqin pattern (TLD 2..63 belgi). `.ru/.com` cheklov
 * olib tashlandi.
 */
// CHK-002: 2..5 so'z, ruxsat etilgan belgilar — Cyrillic, Latin, apostrof,
// hyphen, nuqta, bo'shliq. So'z soni alohida tekshiriladi.
const FIO_REGEX = /^[А-Яа-яЁёA-Za-z'.\- ]+$/;
const EMAIL_REGEX = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,63}$/;

export function validateRecipient(draft) {
  const errors = {};

  const fullName = (draft?.fullName || '').trim();
  if (!fullName) {
    errors.fullName = 'required';
  } else if (!FIO_REGEX.test(fullName)) {
    errors.fullName = 'invalid';
  } else {
    const parts = fullName.split(/\s+/).filter(Boolean);
    if (parts.length < 2 || parts.length > 5) {
      errors.fullName = 'invalid';
    }
  }

  const country = draft?.country || 'RU';
  const fmt = resolveFormat(country);
  const phoneDigits = String(draft?.phoneDigits || '').replace(/\D/g, '');
  if (!phoneDigits) {
    errors.phoneDigits = 'required';
  } else if (phoneDigits.length !== fmt.lenAfter) {
    errors.phoneDigits = 'invalid';
  } else if (fmt.firstDigit && phoneDigits[0] !== fmt.firstDigit) {
    errors.phoneDigits = 'invalid';
  }

  const email = (draft?.email || '').trim();
  if (!email) {
    errors.email = 'required';
  } else if (!EMAIL_REGEX.test(email)) {
    errors.email = 'invalid';
  }

  return errors;
}

/**
 * Customs (таможенные данные) soft validator — UI form'da format-only.
 * Bo'sh maydonlar OK; agar berilgan bo'lsa, format majburiy.
 */
export function validateCustoms(draft) {
  const errors = {};
  if (!draft) return errors;

  const inn = String(draft.inn || '').replace(/\D/g, '');
  if (inn && inn.length !== 12) errors.inn = 'invalid';

  const passportSeries = String(draft.passportSeries || '').replace(/\D/g, '');
  if (passportSeries && passportSeries.length !== 4) {
    errors.passportSeries = 'invalid';
  }

  const passportNumber = String(draft.passportNumber || '').replace(/\D/g, '');
  if (passportNumber && passportNumber.length !== 6) {
    errors.passportNumber = 'invalid';
  }

  return errors;
}

/**
 * Customs draft strict validator — passport/INN/dates barcha maydonlarini
 * majburiy qiladi va sana code'larini (`required`/`invalid`/`future`/
 * `before_birth`) qaytaradi. Customs sheet "Сохранить" tugmasi shu yerda
 * tekshiriladi — UI'da hammasi to'la bo'lsagina draft store'ga yoziladi.
 *
 * Recipient sheet alohida — bu funksiya recipient'siz ishlaydi.
 * `validateRecipientForOrder` ikkalasini birga tekshiradi (Pay tugmasi guard'i).
 */
export function validateCustomsStrict(customs) {
  const errors = {};
  const c = customs || {};

  const passportSeries = String(c.passportSeries || '').replace(/\D/g, '');
  if (!passportSeries) errors.passportSeries = 'required';
  else if (passportSeries.length !== 4) errors.passportSeries = 'invalid';

  const passportNumber = String(c.passportNumber || '').replace(/\D/g, '');
  if (!passportNumber) errors.passportNumber = 'required';
  else if (passportNumber.length !== 6) errors.passportNumber = 'invalid';

  const rawIssue = String(c.issueDate || '').trim();
  const rawBirth = String(c.birthDate || '').trim();
  const issueDateIso = parseRuDate(rawIssue);
  const birthDateIso = parseRuDate(rawBirth);

  if (!rawIssue) errors.issueDate = 'required';
  else if (!issueDateIso) errors.issueDate = 'invalid';

  if (!rawBirth) errors.birthDate = 'required';
  else if (!birthDateIso) errors.birthDate = 'invalid';

  if (issueDateIso && birthDateIso) {
    if (new Date(issueDateIso) < new Date(birthDateIso)) {
      errors.issueDate = 'before_birth';
    }
  }
  if (issueDateIso) {
    const today = new Date();
    today.setHours(23, 59, 59, 999);
    if (new Date(issueDateIso) > today) {
      errors.issueDate = 'future';
    }
  }

  const inn = String(c.inn || '').replace(/\D/g, '');
  if (!inn) errors.inn = 'required';
  else if (inn.length !== 12) errors.inn = 'invalid';

  if (Object.keys(errors).length === 0) return { ok: true, errors: {} };
  return { ok: false, errors };
}

/**
 * Strict validator — `POST /api/v1/recipients` payload tayyorligini tekshiradi.
 * `useCheckoutFlow.ensureRecipient` shu yerdan o'tadi: barcha maydonlar
 * majburiy va backend pattern'lariga mos bo'lishi shart.
 *
 * Returns `{ ok: true }` yoki `{ ok: false, errors: { fieldName: 'required'|'invalid' } }`.
 * `errors` recipient va customs maydonlarini bitta flat map'ga birlashtiradi —
 * UI shu kalitlarni o'zining ikkita formasiga taqsimlaydi.
 */
export function validateRecipientForOrder({ recipient, customs } = {}) {
  const errors = {
    ...validateRecipient(recipient || {}),
    ...validateCustomsStrict(customs).errors,
  };

  if (Object.keys(errors).length === 0) return { ok: true, errors: {} };
  return { ok: false, errors };
}
