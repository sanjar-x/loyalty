'use client';

import { useCallback, useMemo, useState } from 'react';

import { formatRuDateMask } from '@/lib/checkout/dateFormat';
import { validateCustomsStrict } from '@/lib/checkout/validators';

/**
 * Customs sheet form hook (CHK-020).
 *
 * `issueDate` va `birthDate` UI'da `DD.MM.YYYY` shaklida saqlanadi (CHK-001);
 * backend ISO ga konvertatsiya `useCheckoutFlow.ensureRecipient`'da bo'ladi.
 *
 * `submitAttempted` falsy bo'lsa errors `{}` qaytaradi — boshlang'ich
 * to'ldirish paytida red border yo'q.
 *
 * @typedef {{ passportSeries: string, passportNumber: string, issueDate: string, birthDate: string, inn: string }} CustomsDraft
 *
 * @param {Object} params
 * @param {CustomsDraft | null} params.initialValue
 * @param {(payload: CustomsDraft) => void} params.onSave
 */
const EMPTY_DRAFT = Object.freeze({
  passportSeries: '',
  passportNumber: '',
  issueDate: '',
  birthDate: '',
  inn: '',
});

export function useCustomsForm({ initialValue, onSave }) {
  const [draft, setDraft] = useState(() =>
    initialValue ? { ...EMPTY_DRAFT, ...initialValue } : { ...EMPTY_DRAFT }
  );
  const [submitAttempted, setSubmitAttempted] = useState(false);

  const setField = useCallback((field, value) => {
    setDraft((v) => ({ ...v, [field]: value }));
  }, []);

  // Maxsus setterlar — input mask + truncation
  const setDigitsField = useCallback((field, raw, maxLen) => {
    const digits = String(raw || '')
      .replace(/\D/g, '')
      .slice(0, maxLen);
    setDraft((v) => ({ ...v, [field]: digits }));
  }, []);

  const setPassportSeriesField = useCallback((raw) => {
    const normalized = String(raw || '')
      .replace(/[^0-9A-Za-zА-Яа-яЁё]/g, '')
      .toUpperCase()
      .slice(0, 10);
    setDraft((v) => ({ ...v, passportSeries: normalized }));
  }, []);

  const setDateField = useCallback((field, raw) => {
    setDraft((v) => ({ ...v, [field]: formatRuDateMask(raw || '') }));
  }, []);

  const reset = useCallback((next) => {
    setDraft(next ? { ...EMPTY_DRAFT, ...next } : { ...EMPTY_DRAFT });
    setSubmitAttempted(false);
  }, []);

  const validation = useMemo(() => {
    return validateCustomsStrict(draft);
  }, [draft]);

  const errors = submitAttempted ? validation.errors : {};

  const handleSubmit = useCallback(() => {
    setSubmitAttempted(true);
    const guard = validateCustomsStrict(draft);
    if (!guard.ok) return { ok: false, errors: guard.errors };
    const payload = {
      passportSeries: draft.passportSeries.trim(),
      passportNumber: draft.passportNumber.trim(),
      issueDate: draft.issueDate.trim(),
      birthDate: draft.birthDate.trim(),
      inn: draft.inn.trim(),
    };
    onSave(payload);
    return { ok: true, payload };
  }, [draft, onSave]);

  return {
    draft,
    setField,
    setDigitsField,
    setPassportSeriesField,
    setDateField,
    errors,
    submitAttempted,
    handleSubmit,
    reset,
  };
}
