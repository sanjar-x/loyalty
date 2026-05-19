/**
 * Cart-flow checkout validators.
 *
 * Scope post-ADR-011:
 *   • `validateCardDraft`           — Luhn + expiry + cvc + holder for
 *                                     the CardSheet.
 *   • `validateRecipientForOrder`   — wrapper around
 *                                     `entities/recipient.validateRecipient`
 *                                     used by `useCheckoutFlow.ensureRecipient`
 *                                     before POST /recipients.
 *
 * The customs validators (`validateCustoms`, `validateCustomsStrict`)
 * and their `passport*` / `inn` / `birthDate` fields have moved to the
 * Passport bounded context (`features/passport-form/lib/validators.js`).
 * Cart-flow no longer collects customs in its own state.
 */

import { isValidLuhn, normalizeCardNumberDigits, normalizeExpiry } from '@/shared/lib/card';
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
 * Recipient validation for cart-flow's `placeOrder` pre-flight.
 *
 * Post-ADR-011 the orchestrator only checks shipping coordinates —
 * passport documents are validated separately by `features/passport-form`
 * and resolved via `useCheckoutStore.passportId`. `payAction.js` /
 * useCheckoutFlow check that the passport is attached before posting
 * /cart/checkout when the cart has any cross-border item.
 */
export function validateRecipientForOrder({ recipient } = {}) {
  const errors = validateRecipient(recipient || {});
  if (Object.keys(errors).length === 0) return { ok: true, errors: {} };
  return { ok: false, errors };
}
