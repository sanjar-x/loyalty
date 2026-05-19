'use client';

import { useCallback, useMemo, useState } from 'react';

import { useCreatePassportMutation } from '@/entities/passport';
import { humanizeApiError, normalizeApiError } from '@/shared/api/errors';

import {
  maskRuDateInput,
  normaliseFullName,
  normaliseInn,
  normalisePassportNumber,
  normalisePassportSerial,
  ruDateToIso,
} from '../lib/normalizers';
import { validatePassport } from '../lib/validators';

/**
 * Form hook for creating a Passport from inside `PassportStep`
 * (features/buy-now-checkout). ADR-011 — Passport is an independent
 * bounded context, so this hook owns the POST /api/v1/passports call
 * directly via the entity's RTKQ wrapper. On success it calls
 * `onSuccess(passportId)` so the parent step can auto-select the new
 * passport and advance the FSM.
 *
 * `draft` keeps date fields as the masked `DD.MM.YYYY` string so the
 * input renders natively; the validator and submit translate them to
 * the backend ISO form.
 */
const EMPTY_DRAFT = Object.freeze({
  fullNameRu: '',
  fullNameLat: '',
  passportSerial: '',
  passportNumber: '',
  passportIssueDate: '', // DD.MM.YYYY masked input
  birthDate: '', // DD.MM.YYYY masked input
  inn: '',
});

function buildValidationInput(draft) {
  return {
    fullNameRu: normaliseFullName(draft.fullNameRu),
    fullNameLat: normaliseFullName(draft.fullNameLat),
    passportSerial: draft.passportSerial,
    passportNumber: draft.passportNumber,
    passportIssueDateIso: ruDateToIso(draft.passportIssueDate) ?? '',
    birthDateIso: ruDateToIso(draft.birthDate) ?? '',
    inn: draft.inn,
  };
}

export function usePassportForm({ onSuccess, prefillSource } = {}) {
  const [draft, setDraft] = useState(() => buildInitialDraft(prefillSource));
  const [submitAttempted, setSubmitAttempted] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  const [createPassport, createState] = useCreatePassportMutation();

  const setField = useCallback((field, value) => {
    setDraft((prev) => ({ ...prev, [field]: value }));
  }, []);

  /* Field-specific setters — apply per-input normalisation as the
     customer types so the displayed value matches the canonical form. */
  const setFullNameRu = useCallback((raw) => setDraft((p) => ({ ...p, fullNameRu: raw })), []);
  const setFullNameLat = useCallback((raw) => setDraft((p) => ({ ...p, fullNameLat: raw })), []);
  const setPassportSerial = useCallback(
    (raw) => setDraft((p) => ({ ...p, passportSerial: normalisePassportSerial(raw) })),
    []
  );
  const setPassportNumber = useCallback(
    (raw) => setDraft((p) => ({ ...p, passportNumber: normalisePassportNumber(raw) })),
    []
  );
  const setIssueDate = useCallback(
    (raw) => setDraft((p) => ({ ...p, passportIssueDate: maskRuDateInput(raw) })),
    []
  );
  const setBirthDate = useCallback(
    (raw) => setDraft((p) => ({ ...p, birthDate: maskRuDateInput(raw) })),
    []
  );
  const setInn = useCallback((raw) => setDraft((p) => ({ ...p, inn: normaliseInn(raw) })), []);

  const reset = useCallback((next) => {
    setDraft(next ? { ...EMPTY_DRAFT, ...next } : { ...EMPTY_DRAFT });
    setSubmitAttempted(false);
    setSubmitError(null);
  }, []);

  /* Errors are computed only after the customer attempts to submit so
     the inputs don't show red borders during initial typing. */
  const errors = useMemo(() => {
    if (!submitAttempted) return {};
    return validatePassport(buildValidationInput(draft));
  }, [draft, submitAttempted]);

  const submit = useCallback(async () => {
    setSubmitAttempted(true);
    setSubmitError(null);
    const validation = validatePassport(buildValidationInput(draft));
    if (Object.keys(validation).length > 0) {
      return { ok: false, errors: validation };
    }

    const payload = {
      fullNameRu: normaliseFullName(draft.fullNameRu),
      fullNameLat: normaliseFullName(draft.fullNameLat),
      passportSerial: draft.passportSerial,
      passportNumber: draft.passportNumber,
      passportIssueDate: ruDateToIso(draft.passportIssueDate),
      birthDate: ruDateToIso(draft.birthDate),
      inn: draft.inn,
    };

    try {
      const resp = await createPassport(payload).unwrap();
      const id = resp?.passportId;
      if (!id) {
        const err = { code: 'PASSPORT_CREATE_FAILED', message: 'Не удалось сохранить паспорт' };
        setSubmitError(err);
        return { ok: false, error: err };
      }
      onSuccess?.(id);
      return { ok: true, passportId: id };
    } catch (err) {
      const norm = normalizeApiError(err);
      const errInfo = {
        code: norm.code || 'PASSPORT_CREATE_FAILED',
        message: norm.message || humanizeApiError(err, 'Не удалось сохранить паспорт'),
      };
      setSubmitError(errInfo);
      return { ok: false, error: errInfo };
    }
  }, [draft, createPassport, onSuccess]);

  return {
    draft,
    errors,
    submitAttempted,
    submitError,
    isSubmitting: Boolean(createState.isLoading),
    setField,
    setFullNameRu,
    setFullNameLat,
    setPassportSerial,
    setPassportNumber,
    setIssueDate,
    setBirthDate,
    setInn,
    reset,
    submit,
  };
}

/* ────────────────────────────────────────────────────────────────── */

function buildInitialDraft(prefillSource) {
  if (!prefillSource) return { ...EMPTY_DRAFT };
  const fullName = [prefillSource.first_name, prefillSource.last_name]
    .filter(Boolean)
    .join(' ')
    .trim();
  return {
    ...EMPTY_DRAFT,
    fullNameRu: fullName,
  };
}
