import { cn } from '@/shared/lib/ui-utils';

import styles from './page.module.css';

/**
 * Pay button + security note + legal text (offer / agreement / personal data).
 * Audit #1: presentation component split out of the `checkout/page.jsx`
 * god component.
 *
 * The Pay button is always enabled — the pre-flight decision
 * (`decideCheckoutAction`) lives inside the page's `onPay` handler; this
 * component only renders the busy/disabled visual state.
 *
 * @param {object} props
 * @param {boolean} props.isBusy            INITIATING|CONFIRMING — "Создаём заказ…"
 * @param {boolean} props.canPlaceOrder     enabled vs disabled visual state
 * @param {string}  props.payButtonTitle    "Оплатить через СБП" / "Оплатить картой"
 * @param {string}  props.paymentMethod     "sbp" | "card"
 * @param {string}  props.payButtonSuffix   optional suffix (currently "")
 * @param {() => void} props.onPay
 */
export default function PayButtonFooter({
  isBusy,
  canPlaceOrder,
  payButtonTitle,
  paymentMethod,
  payButtonSuffix,
  onPay,
}) {
  return (
    <div>
      <div className={styles.c95}>
        <button
          type="button"
          aria-busy={isBusy}
          onClick={onPay}
          className={`${cn(
            styles.payButton,
            canPlaceOrder ? styles.payButtonEnabled : styles.payButtonDisabled
          )} ${paymentMethod === 'sbp' ? `${styles.paymentMethodSbp}` : ''}`}
        >
          <span className={styles.payButtonSide} />
          <span className={styles.payButtonLabel}>
            {isBusy ? 'Создаём заказ…' : payButtonTitle}
          </span>
          <span className={`${styles.payButtonSide}`}>
            {paymentMethod === 'sbp' ? (
              <img src="/icons/global/cbp.png" alt="" className={cn(styles.c96, styles.tw34)} />
            ) : payButtonSuffix ? (
              <span className={styles.payButtonSuffix}>{payButtonSuffix}</span>
            ) : null}
          </span>
        </button>

        <div className={cn(styles.c97, styles.tw35)}>
          <img src="/icons/global/security.svg" alt="" /> <span>Безопасное оформление заказа</span>
        </div>

        <div className={cn(styles.c98, styles.tw36)}>
          Нажимая «{payButtonTitle}
          », вы принимаете условия{' '}
          <a href="#" className={styles.c99}>
            публичной оферты
          </a>
          ,{' '}
          <a href="#" className={styles.c100}>
            пользовательского соглашения
          </a>{' '}
          и даете согласие на{' '}
          <a href="#" className={styles.c101}>
            обработку персональных данных
          </a>
          .
        </div>
      </div>
    </div>
  );
}
