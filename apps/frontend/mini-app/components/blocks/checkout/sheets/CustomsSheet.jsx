'use client';

import { useRef } from 'react';

import BottomSheet from '@/components/ui/BottomSheet';
import { CUSTOMS_INFO_URL, INN_LOOKUP_URL } from '@/lib/checkout/constants';
import { useCustomsForm } from '@/lib/checkout/hooks/useCustomsForm';

import CheckoutFormField from './CheckoutFormField';
import styles from './CustomsSheet.module.css';

const DATE_ERROR_TEXT = {
  required: 'Заполните дату',
  invalid: 'Неверный формат. Пример: 15.03.1990',
  future: 'Дата выдачи не может быть в будущем',
  before_birth: 'Дата выдачи раньше даты рождения',
};

/**
 * Customs detail sheet (CHK-020/021/022). Pure props-driven; form state
 * `useCustomsForm` hook ichida. CHK-022: CheckoutFormField floating-label
 * pattern.
 *
 * @param {Object} props
 * @param {boolean} props.open
 * @param {() => void} props.onClose
 * @param {(payload: import("@/lib/checkout/hooks/useCustomsForm").CustomsDraft) => void} props.onSave
 * @param {Partial<import("@/lib/checkout/hooks/useCustomsForm").CustomsDraft> | null} [props.initialValue]
 */
export default function CustomsSheet({ open, onClose, onSave, initialValue }) {
  const {
    draft,
    setDigitsField,
    setPassportSeriesField,
    setDateField,
    errors,
    submitAttempted,
    handleSubmit,
  } = useCustomsForm({ initialValue, onSave });
  // CHK-021: autofocus birinchi maydon (passportSeries).
  const firstInputRef = useRef(null);

  if (!open) return null;

  const fieldError = (field, requiredText, invalidText) => {
    if (!submitAttempted) return null;
    const code = errors[field];
    if (!code) return null;
    if (code === 'required') return requiredText;
    return invalidText;
  };

  const dateError = (field) => {
    if (!submitAttempted) return null;
    const code = errors[field];
    if (!code) return null;
    return DATE_ERROR_TEXT[code] || DATE_ERROR_TEXT.invalid;
  };

  return (
    <BottomSheet
      open={open}
      onClose={onClose}
      title="Данные для таможни"
      initialFocusRef={firstInputRef}
    >
      <div className={styles.body}>
        <div className={styles.intro}>
          <div>
            Данные нужны при декларировании товаров из-за рубежа. Все товары оформляются на таможне
            согласно приказу <span className={styles.introHighlight}>ФТС от 05.07.2018 № 1060</span>
            .
          </div>
          <div className={styles.introSecondary}>
            Мы соблюдаем таможенное законодательство и передаём паспортные данные и ИНН получателя в
            защищённом виде.
          </div>
          <a
            href={CUSTOMS_INFO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className={styles.helperLink}
          >
            Подробнее
          </a>
        </div>

        <div className={styles.infoBanner}>
          <img src="/icons/global/Info.svg" alt="" className={styles.infoBannerIcon} />
          <div className={styles.infoBannerText}>
            <div className={styles.infoBannerTitle}>Указывайте настоящие данные</div>
            <div className={styles.infoBannerSubtitle}>
              При таможенном оформлении неверные данные приведут к отказу в пропуске товара.
            </div>
          </div>
        </div>

        <div className={styles.form}>
          <div className={styles.passportRow}>
            <CheckoutFormField
              label="Серия"
              value={draft.passportSeries}
              onChange={(e) => setPassportSeriesField(e.target.value)}
              error={fieldError('passportSeries', 'Заполните серию', 'Серия — 4 знака')}
              inputMode="text"
              autoCapitalize="characters"
              spellCheck={false}
              maxLength={10}
              inputRef={firstInputRef}
            />
            <CheckoutFormField
              label="Номер"
              value={draft.passportNumber}
              onChange={(e) => setDigitsField('passportNumber', e.target.value, 6)}
              error={fieldError('passportNumber', 'Заполните номер', 'Номер — 6 цифр')}
              inputMode="numeric"
              maxLength={6}
            />
          </div>

          <CheckoutFormField
            label="Дата выдачи (ДД.ММ.ГГГГ)"
            value={draft.issueDate}
            onChange={(e) => setDateField('issueDate', e.target.value)}
            error={dateError('issueDate')}
            inputMode="numeric"
            maxLength={10}
          />

          <CheckoutFormField
            label="Дата рождения (ДД.ММ.ГГГГ)"
            value={draft.birthDate}
            onChange={(e) => setDateField('birthDate', e.target.value)}
            error={dateError('birthDate')}
            inputMode="numeric"
            maxLength={10}
          />

          <div className={styles.fieldWithLink}>
            <CheckoutFormField
              label="ИНН"
              value={draft.inn}
              onChange={(e) => setDigitsField('inn', e.target.value, 12)}
              error={fieldError('inn', 'Заполните ИНН', 'ИНН — 12 цифр')}
              inputMode="numeric"
              maxLength={12}
            />
            <a
              href={INN_LOOKUP_URL}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.helperLink}
            >
              Узнать свой ИНН на Госуслугах
            </a>
          </div>
        </div>

        <div className={styles.securityNote}>
          <img src="/icons/global/security.svg" alt="" className={styles.securityIcon} />
          <span>Данные хранятся и передаются в защищённом виде</span>
        </div>

        <button type="button" onClick={handleSubmit} className={styles.submitBtn}>
          Сохранить
        </button>
      </div>
    </BottomSheet>
  );
}
