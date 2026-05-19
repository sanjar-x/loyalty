/**
 * Pure normalisers for passport form inputs.
 *
 * Each helper takes raw user input (with possible formatting artefacts:
 * spaces, dashes, dots) and returns the canonical shape the backend
 * `CreatePassportRequest` accepts (digits-only for numeric fields, ISO
 * `YYYY-MM-DD` for dates).
 */

import { formatRuDateMask, parseRuDate } from '@/shared/lib/date-format';

const digitsOnly = (value, max) =>
  typeof value === 'string' ? value.replace(/\D/g, '').slice(0, max) : '';

export function normalisePassportSerial(value) {
  return digitsOnly(value, 4);
}

export function normalisePassportNumber(value) {
  return digitsOnly(value, 6);
}

export function normaliseInn(value) {
  return digitsOnly(value, 12);
}

export function maskRuDateInput(value) {
  return formatRuDateMask(typeof value === 'string' ? value : '');
}

export function ruDateToIso(value) {
  return parseRuDate(typeof value === 'string' ? value : '');
}

export function normaliseFullName(value) {
  return typeof value === 'string' ? value.replace(/\s+/g, ' ').trim() : '';
}
