'use client';

import { useCallback, useMemo, useState } from 'react';

import { normalizePhoneDigits, validateRecipient } from '@/lib/checkout/validators';

/**
 * Recipient sheet form hook (CHK-020). Sprint 1 pure-helper pattern davomi —
 * UI tarkibidan formani ajratadi, BottomSheet wrapper'ning content qismi
 * unga ulanadi.
 *
 * Interfeys:
 *   { draft, setField, errors, submitAttempted, handleSubmit, reset }
 *
 * Validatsiya: `errors` faqat `submitAttempted=true` bo'lganda hisoblanadi —
 * birinchi marotaba foydalanuvchi yozayotganda input "qora rangda" qoladi.
 * Submit muvaffaqiyatli bo'lsa `onSave(payload)` chaqiriladi.
 *
 * @typedef {{ fullName: string, phoneDigits: string, email: string, country: string }} RecipientDraft
 *
 * @param {Object} params
 * @param {RecipientDraft | null} params.initialValue  null → empty draft
 * @param {(payload: RecipientDraft) => void} params.onSave
 */
const EMPTY_DRAFT = Object.freeze({
  fullName: '',
  phoneDigits: '',
  email: '',
  country: 'RU',
});

/**
 * CHK-021: Telegram WebApp initData'dan recipient pre-fill.
 * `prefillSource` Telegram user shape — har maydon ixtiyoriy, bo'sh
 * source EMPTY_DRAFT'ga tushadi.
 */
function buildInitialDraft(initialValue, prefillSource) {
  if (initialValue) return { ...EMPTY_DRAFT, ...initialValue };
  if (prefillSource) {
    const fullName = [prefillSource.first_name, prefillSource.last_name]
      .filter(Boolean)
      .join(' ')
      .trim();
    return {
      ...EMPTY_DRAFT,
      fullName,
      phoneDigits: prefillSource.phoneDigits || '',
      email: prefillSource.email || '',
    };
  }
  return { ...EMPTY_DRAFT };
}

export function useRecipientForm({ initialValue, onSave, prefillSource } = {}) {
  const [draft, setDraft] = useState(() => buildInitialDraft(initialValue, prefillSource));
  const [submitAttempted, setSubmitAttempted] = useState(false);

  const setField = useCallback((field, value) => {
    setDraft((v) => ({ ...v, [field]: value }));
  }, []);

  const reset = useCallback((next) => {
    setDraft(next ? { ...EMPTY_DRAFT, ...next } : { ...EMPTY_DRAFT });
    setSubmitAttempted(false);
  }, []);

  const errors = useMemo(() => {
    if (!submitAttempted) return {};
    return validateRecipient(draft);
  }, [draft, submitAttempted]);

  const handleSubmit = useCallback(() => {
    setSubmitAttempted(true);
    const errs = validateRecipient(draft);
    if (Object.keys(errs).length > 0) return false;
    const country = draft.country || 'RU';
    onSave({
      fullName: draft.fullName.trim(),
      phoneDigits: normalizePhoneDigits(draft.phoneDigits, country),
      email: draft.email.trim(),
      country,
    });
    return true;
  }, [draft, onSave]);

  return { draft, setField, errors, submitAttempted, handleSubmit, reset };
}
