'use client';

import { useCallback, useRef, useState } from 'react';

import BottomSheet from '@/components/ui/BottomSheet';
import { useRecipientForm } from '@/lib/checkout/hooks/useRecipientForm';
import {
  PHONE_FORMATS,
  SUPPORTED_PHONE_COUNTRIES,
  formatPhone,
  normalizePhoneDigits,
} from '@/lib/checkout/validators';

import CheckoutFormField from './CheckoutFormField';
import styles from './RecipientSheet.module.css';

const PHONE_COUNTRY_FLAGS = {
  RU: '🇷🇺',
  KZ: '🇰🇿',
  BY: '🇧🇾',
  UZ: '🇺🇿',
  UA: '🇺🇦',
};

/**
 * CHK-021: telefonni "+7 9** *** ** 23" shaklida maskalash —
 * saqlangan recipient ro'yxatida ko'rsatish uchun.
 */
function maskPhone(phone) {
  if (!phone) return '';
  const digits = String(phone).replace(/\D/g, '');
  if (digits.length < 4) return phone;
  const head = digits.length === 11 ? digits.slice(1, 4) : digits.slice(0, 3);
  const tail = digits.slice(-2);
  return `+7 ${head} *** ** ${tail}`;
}

const TG_CONTACT_SUPPORTED =
  typeof window !== 'undefined' && typeof window.Telegram?.WebApp?.requestContact === 'function';

/**
 * Recipient detail sheet (CHK-020 + CHK-021 + CHK-022).
 *
 * @param {Object} props
 * @param {boolean} props.open
 * @param {() => void} props.onClose
 * @param {(payload: import("@/lib/checkout/hooks/useRecipientForm").RecipientDraft) => void} props.onSave
 * @param {{ fullName?: string, phoneDigits?: string, email?: string, country?: string } | null} [props.initialValue]
 * @param {{ first_name?: string, last_name?: string, phoneDigits?: string, email?: string } | null} [props.prefillSource]
 * @param {Array<{ recipientId: string, fullNameRu: string, phone?: string, email?: string }>} [props.savedRecipients]
 * @param {boolean} [props.isLoadingSaved]
 * @param {(saved: any) => void} [props.onSelectSaved]
 */
export default function RecipientSheet({
  open,
  onClose,
  onSave,
  initialValue,
  prefillSource,
  savedRecipients = [],
  isLoadingSaved = false,
  onSelectSaved,
}) {
  const { draft, setField, errors, submitAttempted, handleSubmit } = useRecipientForm({
    initialValue,
    onSave,
    prefillSource,
  });

  const firstInputRef = useRef(null);
  const [phoneShareLoading, setPhoneShareLoading] = useState(false);

  const handleRequestPhone = useCallback(() => {
    const tg = typeof window !== 'undefined' ? window.Telegram?.WebApp : null;
    if (!tg?.requestContact) return;
    setPhoneShareLoading(true);
    try {
      tg.requestContact((shared) => {
        setPhoneShareLoading(false);
        if (!shared) return;
        const phone = tg.initDataUnsafe?.user?.phone_number;
        if (phone) {
          const digits = normalizePhoneDigits(phone, draft.country || 'RU');
          setField('phoneDigits', digits);
        }
      });
    } catch {
      setPhoneShareLoading(false);
    }
  }, [draft.country, setField]);

  if (!open) return null;

  const phoneFmt = PHONE_FORMATS[draft.country] || PHONE_FORMATS.RU;

  const onCountryChange = (e) => {
    const nextCountry = e.target.value;
    const nextFmt = PHONE_FORMATS[nextCountry];
    setField('country', nextCountry);
    setField('phoneDigits', (draft.phoneDigits || '').slice(0, nextFmt?.lenAfter ?? 10));
  };

  const onPhoneChange = (e) => {
    const country = draft.country || 'RU';
    const fmt = PHONE_FORMATS[country] || PHONE_FORMATS.RU;
    const el = e.target;
    const selectionStart = el.selectionStart;
    const selectionEnd = el.selectionEnd;
    const raw = el.value || '';
    const rawDigits = normalizePhoneDigits(raw, country);

    const isSelectionCollapsed =
      selectionStart != null && selectionEnd != null && selectionStart === selectionEnd;

    if (
      draft.phoneDigits.length >= fmt.lenAfter &&
      raw.replace(/\D/g, '').length > fmt.lenAfter + fmt.prefixDigits.length &&
      isSelectionCollapsed
    ) {
      return;
    }
    setField('phoneDigits', rawDigits);
  };

  const fieldErrorText = (field, requiredText, invalidText) => {
    if (!submitAttempted) return null;
    const code = errors[field];
    if (code === 'required') return requiredText;
    if (code === 'invalid') return invalidText;
    return null;
  };

  const fullNameError = fieldErrorText('fullName', 'Заполните ФИО', 'ФИО неверный формат');
  const phoneError = fieldErrorText(
    'phoneDigits',
    'Заполните телефон',
    `Укажите телефон в формате ${phoneFmt.placeholder}`
  );
  const emailError = fieldErrorText('email', 'Заполните email', 'Неверный формат');

  const hasSaved = Array.isArray(savedRecipients) && savedRecipients.length > 0;

  const countrySelect = (
    <select
      aria-label="Код страны"
      value={draft.country}
      onChange={onCountryChange}
      className={styles.countrySelectInline}
    >
      {SUPPORTED_PHONE_COUNTRIES.map((code) => (
        <option key={code} value={code}>
          {PHONE_COUNTRY_FLAGS[code]}
        </option>
      ))}
    </select>
  );

  return (
    <BottomSheet open={open} onClose={onClose} title="Получатель" initialFocusRef={firstInputRef}>
      <div className={styles.body}>
        {isLoadingSaved ? (
          <div className={styles.savedSkeleton}>
            <div className={styles.skeletonRow} />
            <div className={styles.skeletonRow} />
          </div>
        ) : hasSaved ? (
          <div className={styles.savedList}>
            <div className={styles.savedListTitle}>Сохранённые получатели</div>
            {savedRecipients.slice(0, 3).map((r) => (
              <button
                key={r.recipientId}
                type="button"
                className={styles.savedItem}
                onClick={() => onSelectSaved?.(r)}
              >
                <div className={styles.savedItemName}>{r.fullNameRu}</div>
                <div className={styles.savedItemPhone}>{maskPhone(r.phone)}</div>
              </button>
            ))}
            <div className={styles.savedDivider}>
              <span>Или добавить нового</span>
            </div>
          </div>
        ) : null}

        <div className={styles.infoBanner}>
          <img src="/icons/global/Info.svg" alt="" className={styles.infoBannerIcon} />
          <div className={styles.infoBannerText}>
            <div className={styles.infoBannerTitle}>Указывайте настоящие данные</div>
            <div className={styles.infoBannerSubtitle}>При заказе потребуется паспорт</div>
          </div>
        </div>

        <div className={styles.form}>
          <CheckoutFormField
            label="ФИО"
            value={draft.fullName}
            onChange={(e) => setField('fullName', e.target.value)}
            error={fullNameError}
            inputRef={firstInputRef}
          />

          <div>
            <CheckoutFormField
              label="Телефон"
              value={formatPhone(draft.phoneDigits, draft.country)}
              onChange={onPhoneChange}
              error={phoneError}
              type="tel"
              inputMode="tel"
              rightSlot={countrySelect}
            />
            {TG_CONTACT_SUPPORTED ? (
              <button
                type="button"
                className={styles.phoneShareLink}
                onClick={handleRequestPhone}
                disabled={phoneShareLoading}
              >
                {phoneShareLoading ? '...' : 'Поделиться номером из Telegram'}
              </button>
            ) : null}
          </div>

          <CheckoutFormField
            label="Электронная почта"
            value={draft.email}
            onChange={(e) => setField('email', e.target.value)}
            error={emailError}
            type="email"
            inputMode="email"
          />
        </div>

        <button type="button" onClick={handleSubmit} className={styles.submitBtn}>
          Сохранить
        </button>
      </div>
    </BottomSheet>
  );
}
