'use client';

import BottomSheet from '@/shared/ui/BottomSheet';
import { useCardForm } from '@/features/checkout-flow/model/useCardForm';

import FormField from '@/shared/ui/FormField';
import styles from './CardSheet.module.css';

/**
 * Card detail sheet (CHK-020/022).
 *
 * CURRENTLY UNUSED (CHK-021): per Backend Spec §11 there is no payment widget —
 * the checkout payment selector temporarily replaces the Card button with a
 * "Coming soon" disclaimer. This file is the foundation for a future real payment
 * provider widget integration (Tinkoff PayLink, YuKassa).
 *
 * See: BACK-PAY-001 (backend ticket — Payment Intent API).
 *
 * PCI: card data is not stored in the browser — when the sheet closes the
 * draft is dropped. Submit only signals "validation passed"; the caller
 * switches to `paymentMethod="card"` and in the next step the real payment
 * provider widget is opened.
 *
 * @param {Object} props
 * @param {boolean} props.open
 * @param {() => void} props.onClose
 * @param {(payload: import("@/features/checkout-flow/model/useCardForm").CardDraft) => void} props.onSave
 */
export default function CardSheet({ open, onClose, onSave }) {
  const {
    draft,
    numberFormatted,
    setNumber,
    setExp,
    setCvc,
    setHolder,
    errors,
    submitAttempted,
    handleSubmit,
  } = useCardForm({ onSave });

  if (!open) return null;

  const fieldError = (field, requiredText, invalidText) => {
    if (!submitAttempted) return null;
    const code = errors[field];
    if (!code) return null;
    if (code === 'required') return requiredText;
    return invalidText;
  };

  return (
    <BottomSheet open={open} onClose={onClose} title="Добавить карту">
      <div className={styles.body}>
        <div className={styles.disclaim}>CVV-код не сохраняется и не хранится.</div>

        <div className={styles.form}>
          <FormField
            label="Номер карты"
            value={numberFormatted}
            onChange={(e) => setNumber(e.target.value)}
            error={fieldError('numberDigits', 'Заполните номер карты', 'Проверьте номер карты')}
            inputMode="numeric"
          />

          <div className={styles.expCvcRow}>
            <FormField
              label="MM/YY"
              value={draft.exp}
              onChange={(e) => setExp(e.target.value)}
              error={fieldError('exp', 'Срок', 'Неверный срок')}
              inputMode="numeric"
            />
            <FormField
              label="CVV"
              value={draft.cvc}
              onChange={(e) => setCvc(e.target.value)}
              error={fieldError('cvc', 'CVV', 'Минимум 3 цифры')}
              inputMode="numeric"
            />
          </div>

          <FormField
            label="Имя владельца"
            value={draft.holder}
            onChange={(e) => setHolder(String(e.target.value || '').replace(/\s+/g, ' '))}
            error={fieldError('holder', 'Заполните имя', 'Укажите имя латиницей или кириллицей')}
            inputMode="text"
            autoCapitalize="characters"
            spellCheck={false}
          />
        </div>

        <button type="button" onClick={handleSubmit} className={styles.submitBtn}>
          Сохранить
        </button>
      </div>
    </BottomSheet>
  );
}
