'use client';

import BottomSheet from '@/components/ui/BottomSheet';
import { useCardForm } from '@/lib/checkout/hooks/useCardForm';

import CheckoutFormField from './CheckoutFormField';
import styles from './CardSheet.module.css';

/**
 * Card detail sheet (CHK-020/022).
 *
 * HOZIR ISHLATILMAYDI (CHK-021): Backend Spec §11 payment widget yo'q —
 * checkout payment selector'i Card tugmasini "Скоро" disclaim'iga
 * vaqtinchalik almashtirgan. Bu fayl kelajakda real payment provider
 * widget (Tinkoff PayLink, ЮKassa) integratsiyasi uchun zamin.
 *
 * Refer: BACK-PAY-001 (backend ticket — Payment Intent API).
 *
 * PCI: kard ma'lumotlari brauzerda saqlanmaydi — sheet yopilganda
 * draft tashlanadi. Submit faqat "validation passed" signalini beradi;
 * chaqiruvchi `paymentMethod="card"` ga o'tadi va keyingi qadamda
 * haqiqiy payment provider widget'i ochiladi.
 *
 * @param {Object} props
 * @param {boolean} props.open
 * @param {() => void} props.onClose
 * @param {(payload: import("@/lib/checkout/hooks/useCardForm").CardDraft) => void} props.onSave
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
          <CheckoutFormField
            label="Номер карты"
            value={numberFormatted}
            onChange={(e) => setNumber(e.target.value)}
            error={fieldError('numberDigits', 'Заполните номер карты', 'Проверьте номер карты')}
            inputMode="numeric"
          />

          <div className={styles.expCvcRow}>
            <CheckoutFormField
              label="MM/YY"
              value={draft.exp}
              onChange={(e) => setExp(e.target.value)}
              error={fieldError('exp', 'Срок', 'Неверный срок')}
              inputMode="numeric"
            />
            <CheckoutFormField
              label="CVV"
              value={draft.cvc}
              onChange={(e) => setCvc(e.target.value)}
              error={fieldError('cvc', 'CVV', 'Минимум 3 цифры')}
              inputMode="numeric"
            />
          </div>

          <CheckoutFormField
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
