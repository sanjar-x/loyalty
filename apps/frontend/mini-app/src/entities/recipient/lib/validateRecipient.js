/**
 * Recipient validator (CHK-002).
 *
 * This is the `recipient` entity — a validator for its required fields. Used
 * by features/recipient-form (UI sheet + draft hook) and features/checkout-flow
 * (orchestrator validateRecipientForOrder).
 *
 * Sprint 2: moved out of shared/lib/validators — this is business logic for
 * a specific entity, not shared. Phone helpers (CIS country formats) still
 * live in shared/lib/phone.
 */

import { resolvePhoneFormat } from '@/shared/lib/phone';

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
  const fmt = resolvePhoneFormat(country);
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
