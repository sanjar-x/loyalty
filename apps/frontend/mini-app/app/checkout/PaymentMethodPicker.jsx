import cn from 'clsx';

import styles from './page.module.css';

/**
 * To'lov usuli tanlovchi: СБП / Добавить карту. Audit #1:
 * `checkout/page.jsx` god-komponentidan ajratilgan presentation komponent.
 *
 * `onSelectSbp` — SBP'ga o'tish (split o'chiriladi). `onOpenCard` — CardSheet
 * ochish; `paymentMethod="card"` SHEET onSave'da set qilinadi (× yopilsa
 * o'zgarmaydi), shu sabab bu yerda faqat ochish handler'i.
 */
export default function PaymentMethodPicker({ paymentMethod, onSelectSbp, onOpenCard }) {
  return (
    <div className={cn(styles.c54, styles.tw18)}>
      <button
        type="button"
        aria-pressed={paymentMethod === 'sbp'}
        onClick={onSelectSbp}
        className={cn(
          styles.paymentOption,
          styles.paymentOptionSbp,
          paymentMethod === 'sbp' ? styles.paymentOptionSelected : styles.paymentOptionUnselectedSbp
        )}
      >
        <span className={cn(styles.c55, styles.tw19)}>
          <img src="/icons/global/cbp.png" alt="" className={cn(styles.c56)} />
        </span>
        <span className={styles.c57}>СБП</span>
      </button>

      {/* CHK-023: Card to'lov MVP/prototype rejimida aktiv. Backend payment
          widget'i hali yo'q (BACK-PAY-001) — order yaratiladi lekin haqiqiy
          to'lov bo'lmaydi. Manager rozi: silent activation, kelajakda backend
          ulansa transparent transition. Tugma faqat sheet'ni ochadi —
          `paymentMethod="card"` sheet onSave'da set qilinadi (× yopilsa
          o'zgarmaydi). */}
      <button
        type="button"
        aria-pressed={paymentMethod === 'card'}
        onClick={onOpenCard}
        className={cn(
          styles.paymentOption,
          styles.paymentOptionAddCard,
          paymentMethod === 'card'
            ? styles.paymentOptionSelected
            : styles.paymentOptionUnselectedCard
        )}
      >
        <span className={styles.addCardPlus}>+</span>
        <span className={styles.addCardText}>Добавить карту</span>
      </button>
    </div>
  );
}
