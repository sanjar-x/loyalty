'use client';

import { useCallback, useMemo, useState } from 'react';

import {
  formatCardNumber,
  normalizeCardNumberDigits,
  normalizeExpiry,
  validateCardDraft,
} from '@/lib/checkout/validators';

/**
 * Card sheet form hook (CHK-020).
 *
 * **PCI Note:** card detail HECH QAERGA saqlanmaydi (sessionStorage, store,
 * URL). Sheet yopilganda draft tashlanadi. Submit'da onSave faqat
 * "validation passed" signalini beradi — chaqiruvchi `paymentMethod="card"`
 * ga o'tadi va keyingi qadamda haqiqiy provider widget'i (Tinkoff PayLink
 * va h.k.) ochiladi.
 *
 * @typedef {{ numberDigits: string, exp: string, cvc: string, holder: string }} CardDraft
 *
 * @param {Object} params
 * @param {(payload: CardDraft) => void} params.onSave
 */
const EMPTY_DRAFT = Object.freeze({
  numberDigits: '',
  exp: '',
  cvc: '',
  holder: '',
});

export function useCardForm({ onSave }) {
  const [draft, setDraft] = useState(() => ({ ...EMPTY_DRAFT }));
  const [submitAttempted, setSubmitAttempted] = useState(false);

  const setNumber = useCallback((raw) => {
    const digits = normalizeCardNumberDigits(raw);
    setDraft((v) => ({ ...v, numberDigits: digits }));
  }, []);

  const setExp = useCallback((raw) => {
    setDraft((v) => ({ ...v, exp: normalizeExpiry(raw) }));
  }, []);

  const setCvc = useCallback((raw) => {
    const digits = String(raw || '')
      .replace(/\D/g, '')
      .slice(0, 4);
    setDraft((v) => ({ ...v, cvc: digits }));
  }, []);

  const setHolder = useCallback((raw) => {
    setDraft((v) => ({ ...v, holder: String(raw || '') }));
  }, []);

  const reset = useCallback(() => {
    setDraft({ ...EMPTY_DRAFT });
    setSubmitAttempted(false);
  }, []);

  const errors = useMemo(() => {
    if (!submitAttempted) return {};
    return validateCardDraft(draft);
  }, [draft, submitAttempted]);

  const numberFormatted = useMemo(() => formatCardNumber(draft.numberDigits), [draft.numberDigits]);

  const handleSubmit = useCallback(() => {
    setSubmitAttempted(true);
    const errs = validateCardDraft(draft);
    if (Object.keys(errs).length > 0) return false;
    onSave({ ...draft });
    return true;
  }, [draft, onSave]);

  return {
    draft,
    numberFormatted,
    setNumber,
    setExp,
    setCvc,
    setHolder,
    errors,
    submitAttempted,
    handleSubmit,
    reset,
  };
}
