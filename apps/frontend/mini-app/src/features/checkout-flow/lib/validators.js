/**
 * Checkout form validators (card draft, customs, recipient-for-order
 * orchestrator). Sprint 2: extracted from shared/lib/validators into its own domain.
 *
 * Business-bound: these validators know the specific fields of the checkout form
 * (cvc, holder, exp, passportSeries, passportNumber, issueDate, birthDate,
 * inn). Generic plumbing lives in shared/lib/{card,phone}.
 */

import {
  isValidLuhn,
  normalizeCardNumberDigits,
  normalizeExpiry,
} from '@/shared/lib/card';
import { parseRuDate } from '@/shared/lib/date-format';
import { validateRecipient } from '@/entities/recipient';

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
 * Customs (customs data) soft validator — format-only in the UI form.
 * Empty fields are OK; if provided, the format is mandatory.
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
 * Customs strict validator — all fields required, with date checks.
 * Guards the UI Customs sheet's "Save" button.
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
 * Orchestrator — strict validator for the POST /api/v1/recipients payload.
 * `useCheckoutFlow.ensureRecipient` runs through this function: recipient
 * + customs are all required and valid.
 */
export function validateRecipientForOrder({ recipient, customs } = {}) {
  const errors = {
    ...validateRecipient(recipient || {}),
    ...validateCustomsStrict(customs).errors,
  };

  if (Object.keys(errors).length === 0) return { ok: true, errors: {} };
  return { ok: false, errors };
}
