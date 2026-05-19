'use client';

import FormField from '@/shared/ui/FormField';

import { usePassportForm } from '../model/usePassportForm';
import styles from './PassportForm.module.css';

/**
 * Inline passport-creation form for `PassportStep`
 * (features/buy-now-checkout). ADR-011 — Passport is owned by an
 * independent bounded context, so this form posts directly to
 * `/api/v1/passports` via `usePassportForm`. On success the parent
 * step receives the new `passportId` through `onSuccess` and advances.
 *
 * Props:
 *   • onSuccess(passportId) — called after the backend returns 201
 *   • onCancel              — optional «back to list» action; when
 *                             omitted the form renders without a cancel
 *                             button (e.g. first-time customer with an
 *                             empty roster)
 *   • prefillSource         — Telegram user shape (`first_name`,
 *                             `last_name`) for ФИО prefill
 *   • testId                — `data-testid` for the FE-8 Playwright
 *                             scenarios (default `passport-form`)
 */
export default function PassportForm({
  onSuccess,
  onCancel,
  cancelLabel = 'Назад',
  prefillSource,
  testId = 'passport-form',
}) {
  const form = usePassportForm({ onSuccess, prefillSource });
  const {
    draft,
    errors,
    submitAttempted,
    submitError,
    isSubmitting,
    setFullNameRu,
    setFullNameLat,
    setPassportSerial,
    setPassportNumber,
    setIssueDate,
    setBirthDate,
    setInn,
    submit,
  } = form;

  const fieldError = (field, requiredText, invalidText, extra = {}) => {
    if (!submitAttempted) return null;
    const code = errors[field];
    if (!code) return null;
    if (code === 'required') return requiredText;
    if (extra[code]) return extra[code];
    return invalidText;
  };

  return (
    <div className={styles.root} data-testid={testId}>
      <div className={styles.section}>
        <div className={styles.sectionLabel}>Имя на латинице (как в загранпаспорте)</div>
        <FormField
          label="ФИО (RU)"
          value={draft.fullNameRu}
          onChange={(e) => setFullNameRu(e.target.value)}
          error={fieldError('fullNameRu', 'Заполните ФИО', 'Минимум имя и фамилия')}
        />
        <FormField
          label="ФИО (Latin)"
          value={draft.fullNameLat}
          onChange={(e) => setFullNameLat(e.target.value)}
          error={fieldError(
            'fullNameLat',
            'Заполните Latin ФИО',
            'Только латиница, минимум имя и фамилия'
          )}
        />
      </div>

      <div className={styles.section}>
        <div className={styles.sectionLabel}>Паспорт РФ</div>
        <div className={styles.row}>
          <FormField
            label="Серия"
            value={draft.passportSerial}
            onChange={(e) => setPassportSerial(e.target.value)}
            error={fieldError('passportSerial', 'Обязательно', '4 цифры')}
            inputMode="numeric"
            maxLength={4}
            data-testid="passport-form-serial"
          />
          <FormField
            label="Номер"
            value={draft.passportNumber}
            onChange={(e) => setPassportNumber(e.target.value)}
            error={fieldError('passportNumber', 'Обязательно', '6 цифр')}
            inputMode="numeric"
            maxLength={6}
            data-testid="passport-form-number"
          />
        </div>
        <FormField
          label="Дата выдачи (ДД.ММ.ГГГГ)"
          value={draft.passportIssueDate}
          onChange={(e) => setIssueDate(e.target.value)}
          error={fieldError('passportIssueDate', 'Обязательно', 'Неверная дата', {
            future: 'Дата из будущего',
            before_passport_era: 'Раньше 01.01.1991',
            before_owner_age: 'Паспорт раньше 14-летия',
          })}
          inputMode="numeric"
          maxLength={10}
          placeholder="ДД.ММ.ГГГГ"
          data-testid="passport-form-issue-date"
        />
      </div>

      <div className={styles.section}>
        <div className={styles.sectionLabel}>Получатель</div>
        <FormField
          label="Дата рождения (ДД.ММ.ГГГГ)"
          value={draft.birthDate}
          onChange={(e) => setBirthDate(e.target.value)}
          error={fieldError('birthDate', 'Обязательно', 'Неверная дата', {
            future: 'Дата из будущего',
            too_young: 'Получатель должен быть не младше 14 лет',
          })}
          inputMode="numeric"
          maxLength={10}
          placeholder="ДД.ММ.ГГГГ"
          data-testid="passport-form-birth-date"
        />
        <FormField
          label="ИНН (12 цифр)"
          value={draft.inn}
          onChange={(e) => setInn(e.target.value)}
          error={fieldError('inn', 'Обязательно', '12 цифр', {
            checksum: 'Неверная контрольная цифра',
          })}
          inputMode="numeric"
          maxLength={12}
          data-testid="passport-form-inn"
        />
      </div>

      {submitError ? (
        <div className={styles.error} role="alert">
          {submitError.message}
        </div>
      ) : null}

      <div className={styles.actions}>
        {onCancel ? (
          <button
            type="button"
            className={styles.secondaryBtn}
            onClick={onCancel}
            disabled={isSubmitting}
          >
            {cancelLabel}
          </button>
        ) : null}
        <button
          type="button"
          className={styles.primaryBtn}
          onClick={submit}
          disabled={isSubmitting}
          aria-busy={isSubmitting}
          data-testid="passport-form-submit"
        >
          {isSubmitting ? 'Сохраняем…' : 'Сохранить и продолжить'}
        </button>
      </div>
    </div>
  );
}
