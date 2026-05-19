/**
 * Passport form validators. Mirrors the backend domain invariants surfaced
 * in ADR-011 (Passport bounded context):
 *
 *   - passport_serial = exactly 4 digits
 *   - passport_number = exactly 6 digits
 *   - passport_issue_date - ISO date in [1991-01-01 .. today]
 *   - birth_date - ISO date in past; bearer must be >= 14 years
 *   - inn - 12-digit individual ИНН with mod-11-twice checksum
 *   - full_name_ru - non-empty, allowed RU/EN/'.-/space/hyphen
 *   - full_name_lat - non-empty, Latin letters / spaces / hyphen / apostrophe
 *
 * Validators return `{}` (empty map) on success or
 * `{ [field]: 'required'|'invalid'|'too_young'|'before_passport_era'|... }`
 * so the UI can map error codes to localised copy.
 *
 * Pure helpers - no DOM, no i18n - easy to unit-test.
 */

import { isValidInn } from '@/shared/lib/inn-checksum';

const FULL_NAME_RU_REGEX = /^[А-Яа-яЁёA-Za-z' .\-]+$/;
const FULL_NAME_LAT_REGEX = /^[A-Za-z' .\-]+$/;
const ISO_DATE_REGEX = /^(\d{4})-(\d{2})-(\d{2})$/;
const MIN_PASSPORT_AGE_YEARS = 14;
const PASSPORT_ERA_START_ISO = '1991-01-01';

function startOfTodayUtc() {
  const now = new Date();
  return Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
}

function isoToUtcMs(iso) {
  const m = typeof iso === 'string' ? iso.match(ISO_DATE_REGEX) : null;
  if (!m) return NaN;
  const y = Number(m[1]);
  const mo = Number(m[2]);
  const d = Number(m[3]);
  return Date.UTC(y, mo - 1, d);
}

function ageInYears(birthMs, todayMs) {
  if (!Number.isFinite(birthMs) || !Number.isFinite(todayMs)) return -1;
  const yearMs = 365.25 * 24 * 60 * 60 * 1000;
  return (todayMs - birthMs) / yearMs;
}

/**
 * @typedef {Object} PassportDraft
 * @property {string} fullNameRu
 * @property {string} fullNameLat
 * @property {string} passportSerial
 * @property {string} passportNumber
 * @property {string} passportIssueDateIso  ISO `YYYY-MM-DD`
 * @property {string} birthDateIso          ISO `YYYY-MM-DD`
 * @property {string} inn                   12 digits
 */

export function validatePassport(draft) {
  const errors = {};
  const d = draft || {};
  const todayMs = startOfTodayUtc();
  const eraStartMs = isoToUtcMs(PASSPORT_ERA_START_ISO);

  const fullRu = String(d.fullNameRu || '').trim();
  if (!fullRu) {
    errors.fullNameRu = 'required';
  } else if (!FULL_NAME_RU_REGEX.test(fullRu) || fullRu.split(/\s+/).filter(Boolean).length < 2) {
    errors.fullNameRu = 'invalid';
  }

  const fullLat = String(d.fullNameLat || '').trim();
  if (!fullLat) {
    errors.fullNameLat = 'required';
  } else if (
    !FULL_NAME_LAT_REGEX.test(fullLat) ||
    fullLat.split(/\s+/).filter(Boolean).length < 2
  ) {
    errors.fullNameLat = 'invalid';
  }

  const serial = String(d.passportSerial || '').replace(/\D/g, '');
  if (!serial) {
    errors.passportSerial = 'required';
  } else if (serial.length !== 4) {
    errors.passportSerial = 'invalid';
  }

  const number = String(d.passportNumber || '').replace(/\D/g, '');
  if (!number) {
    errors.passportNumber = 'required';
  } else if (number.length !== 6) {
    errors.passportNumber = 'invalid';
  }

  const issueIso = String(d.passportIssueDateIso || '');
  const issueMs = isoToUtcMs(issueIso);
  if (!issueIso) {
    errors.passportIssueDate = 'required';
  } else if (!Number.isFinite(issueMs)) {
    errors.passportIssueDate = 'invalid';
  } else if (Number.isFinite(eraStartMs) && issueMs < eraStartMs) {
    errors.passportIssueDate = 'before_passport_era';
  } else if (issueMs > todayMs) {
    errors.passportIssueDate = 'future';
  }

  const birthIso = String(d.birthDateIso || '');
  const birthMs = isoToUtcMs(birthIso);
  if (!birthIso) {
    errors.birthDate = 'required';
  } else if (!Number.isFinite(birthMs)) {
    errors.birthDate = 'invalid';
  } else if (birthMs > todayMs) {
    errors.birthDate = 'future';
  } else if (ageInYears(birthMs, todayMs) < MIN_PASSPORT_AGE_YEARS) {
    errors.birthDate = 'too_young';
  }

  if (
    Number.isFinite(issueMs) &&
    Number.isFinite(birthMs) &&
    !errors.passportIssueDate &&
    !errors.birthDate
  ) {
    if (ageInYears(birthMs, issueMs) < MIN_PASSPORT_AGE_YEARS) {
      errors.passportIssueDate = 'before_owner_age';
    }
  }

  const inn = String(d.inn || '').replace(/\D/g, '');
  if (!inn) {
    errors.inn = 'required';
  } else if (inn.length !== 12) {
    errors.inn = 'invalid';
  } else if (!isValidInn(inn)) {
    errors.inn = 'checksum';
  }

  return errors;
}
