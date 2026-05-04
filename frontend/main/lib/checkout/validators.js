/**
 * Checkout form validators va formatter'lari.
 *
 * Pure funksiyalar — hech qanday DOM/window referensisiz, oson test qilinadi.
 * `app/checkout/page.jsx` ichida inline yozilgan logika shu yerga ajratilgan.
 */

/* ── Card helpers ── */

export function normalizeCardNumberDigits(input) {
  return (input || "").replace(/\D/g, "").slice(0, 19);
}

export function formatCardNumber(digits) {
  const d = (digits || "").replace(/\D/g, "");
  return d.replace(/(.{4})/g, "$1 ").trim();
}

export function normalizeExpiry(value) {
  const digits = (value || "").replace(/\D/g, "").slice(0, 4);
  const mm = digits.slice(0, 2);
  const yy = digits.slice(2, 4);
  return yy ? `${mm}/${yy}` : mm;
}

export function isValidLuhn(numberDigits) {
  const digits = (numberDigits || "").replace(/\D/g, "");
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

/* ── Phone helpers (Russia +7) ── */

export function normalizePhoneDigits(input) {
  const raw = input || "";
  let digits = raw.replace(/\D/g, "");
  if (!digits) return "";

  const hasPlus7Prefix = /^\s*\+7/.test(raw);
  if (hasPlus7Prefix && digits.startsWith("7")) {
    digits = digits.slice(1);
  }

  // Pasted 8XXXXXXXXXX, 7XXXXXXXXXX, +7XXXXXXXXXX — strip leading.
  if (
    digits.length >= 11 &&
    (digits.startsWith("7") || digits.startsWith("8"))
  ) {
    digits = digits.slice(1);
  }

  return digits.slice(0, 10);
}

export function formatPhone(digits10) {
  const d = (digits10 || "").replace(/\D/g, "").slice(0, 10);
  if (!d) return "";
  const a = d.slice(0, 3);
  const b = d.slice(3, 6);
  const c = d.slice(6, 8);
  const e = d.slice(8, 10);
  let out = "+7";
  if (a) out += ` ${a}`;
  if (b) out += ` ${b}`;
  if (c) out += `-${c}`;
  if (e) out += `-${e}`;
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
    errors.numberDigits = "required";
  } else if (numberDigits.length < 16 || numberDigits.length > 19) {
    errors.numberDigits = "invalid";
  } else if (!isValidLuhn(numberDigits)) {
    errors.numberDigits = "invalid";
  }

  const exp = normalizeExpiry(draft?.exp);
  if (!exp) {
    errors.exp = "required";
  } else if (!/^\d{2}\/\d{2}$/.test(exp)) {
    errors.exp = "invalid";
  } else {
    const [mmStr, yyStr] = exp.split("/");
    const mm = Number(mmStr);
    const yy = Number(yyStr);
    if (mm < 1 || mm > 12 || Number.isNaN(yy)) {
      errors.exp = "invalid";
    }
  }

  const cvc = (draft?.cvc || "").replace(/\D/g, "").slice(0, 4);
  if (!cvc) {
    errors.cvc = "required";
  } else if (cvc.length < 3) {
    errors.cvc = "invalid";
  }

  const holder = (draft?.holder || "").trim();
  if (!holder) {
    errors.holder = "required";
  } else {
    const ok = /^[A-Za-zА-Яа-яЁё\s-]+$/.test(holder);
    if (!ok || holder.replace(/\s+/g, " ").length < 3) {
      errors.holder = "invalid";
    }
  }

  return errors;
}

/**
 * Recipient (получатель) validator.
 * `phoneDigits` — 10 ta raqam, 9XXXXXXXXX bilan boshlanishi kerak (RF mobil).
 * Email — `.ru` yoki `.com` (TLD cheklov, business choice).
 */
export function validateRecipient(draft) {
  const errors = {};

  const fullName = (draft?.fullName || "").trim();
  if (!fullName) {
    errors.fullName = "required";
  } else if (/[A-Za-z]/.test(fullName)) {
    errors.fullName = "invalid";
  } else {
    const parts = fullName.split(/\s+/).filter(Boolean);
    if (parts.length < 2) {
      errors.fullName = "invalid";
    } else if (!parts.every((p) => /^[А-Яа-яЁё-]+$/.test(p))) {
      errors.fullName = "invalid";
    }
  }

  const phoneDigits = (draft?.phoneDigits || "").trim();
  if (!phoneDigits) {
    errors.phoneDigits = "required";
  } else if (phoneDigits.length !== 10 || !phoneDigits.startsWith("9")) {
    errors.phoneDigits = "invalid";
  }

  const email = (draft?.email || "").trim();
  if (!email) {
    errors.email = "required";
  } else if (!/^[^\s@]+@[^\s@]+\.(ru|com)$/i.test(email)) {
    errors.email = "invalid";
  }

  return errors;
}

/**
 * Customs (таможенные данные) validator.
 * Hozir UI bo'sh saqlash imkonini beradi (cross-border tovari yo'q
 * bo'lganda kerak emas), shuning uchun draftda hech bir maydon majburiy emas;
 * agar berilgan bo'lsa — minimal format check.
 */
export function validateCustoms(draft) {
  const errors = {};
  if (!draft) return errors;

  const inn = String(draft.inn || "").replace(/\D/g, "");
  if (inn && inn.length !== 12) errors.inn = "invalid";

  const passportSeries = String(draft.passportSeries || "").replace(/\D/g, "");
  if (passportSeries && passportSeries.length !== 4) {
    errors.passportSeries = "invalid";
  }

  const passportNumber = String(draft.passportNumber || "").replace(/\D/g, "");
  if (passportNumber && passportNumber.length !== 6) {
    errors.passportNumber = "invalid";
  }

  return errors;
}
