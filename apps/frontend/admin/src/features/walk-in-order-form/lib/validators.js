// Client-side validators that mirror backend `RecipientSnapshot.__attrs_post_init__`
// and `WalkInItemSchema` rules. The defense-in-depth duplication is
// intentional: the user gets immediate field-level feedback instead of
// a 422 round-trip, and the field with the error is unambiguous.
//
// All validators return `true` for "valid", `false` for "invalid". Empty
// strings are treated as invalid (required fields) — wrap with `optional()`
// for optional fields.

import { MAX_PRICE_OVERRIDE_RATIO } from './constants';

// Backend accepts an optional leading `+` and 8..15 digits (E.164-shape).
// We keep the same shape on the client; formatting / mask is a UI concern
// and lives in the input component.
const PHONE_RE = /^\+?\d{8,15}$/;
const EMAIL_RE = /^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$/;
const PASSPORT_SERIAL_RE = /^\d{4}$/;
const PASSPORT_NUMBER_RE = /^\d{6}$/;
// Минфин формат — 12 digits. We deliberately do not verify the checksum:
// foreign-issued INNs sometimes break it, and the backend doesn't enforce
// checksum either. Length-only keeps the validator honest.
const INN_RE = /^\d{12}$/;
const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

export function validatePhone(value) {
  return typeof value === 'string' && PHONE_RE.test(value);
}

export function validateEmail(value) {
  return typeof value === 'string' && EMAIL_RE.test(value);
}

export function validatePassportSerial(value) {
  return typeof value === 'string' && PASSPORT_SERIAL_RE.test(value);
}

export function validatePassportNumber(value) {
  return typeof value === 'string' && PASSPORT_NUMBER_RE.test(value);
}

export function validateInn(value) {
  return typeof value === 'string' && INN_RE.test(value);
}

export function validateIsoDate(value) {
  if (typeof value !== 'string' || !ISO_DATE_RE.test(value)) return false;
  const t = Date.parse(value);
  return !Number.isNaN(t);
}

export function validateNonEmptyString(value, { maxLength = Infinity } = {}) {
  return (
    typeof value === 'string' &&
    value.trim().length > 0 &&
    value.length <= maxLength
  );
}

export function validateQuantity(value) {
  return Number.isInteger(value) && value >= 1 && value <= 99;
}

// Override is optional; when present it must be a non-negative integer in
// kopecks and within ratio × base. Returning a structured result so the
// caller can show "допустимо 0 — {max}" without re-computing the bound.
export function validatePriceOverride({ override, basePrice }) {
  if (override == null) return { ok: true };
  if (!Number.isInteger(override) || override < 0) {
    return { ok: false, reason: 'must_be_non_negative_integer' };
  }
  if (!Number.isInteger(basePrice) || basePrice < 0) {
    // Cannot validate against an unknown base — caller must wait until
    // base price loads. Treat as invalid so submit stays disabled.
    return { ok: false, reason: 'missing_base_price' };
  }
  const max = basePrice * MAX_PRICE_OVERRIDE_RATIO;
  if (override > max) {
    return { ok: false, reason: 'above_max_ratio', max };
  }
  return { ok: true };
}

export function validateDeliveryAmount(value) {
  return Number.isInteger(value) && value >= 0;
}

export function validateItemsLength(items) {
  return Array.isArray(items) && items.length >= 1 && items.length <= 50;
}
