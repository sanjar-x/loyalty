import { cn } from '@/shared/lib/ui-utils';

import styles from './page.module.css';

/**
 * Payment method picker: SBP / Add card. Audit #1:
 * presentation component split out of the `checkout/page.jsx` god component.
 *
 * `onSelectSbp` — switch to SBP (split is turned off). `onOpenCard` — opens
 * the CardSheet; `paymentMethod="card"` is set in the sheet's onSave (it
 * doesn't change if the sheet is closed via ×), so this just has an open
 * handler.
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

      {/* CHK-023: Card payment is active in MVP/prototype mode. There is no
          backend payment widget yet (BACK-PAY-001) — the order is created
          but no real payment happens. Manager-approved: silent activation,
          with a transparent transition once the backend is wired up. The
          button only opens the sheet — `paymentMethod="card"` is set in the
          sheet's onSave (it doesn't change if closed via ×). */}
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
