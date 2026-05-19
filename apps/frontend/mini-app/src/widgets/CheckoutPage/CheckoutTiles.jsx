import { cn } from '@/shared/lib/ui-utils';

import styles from './page.module.css';

/**
 * Checkout configuration tiles: Pickup point / Recipient / Passport.
 * Audit #1: pure presentation component split out of the `checkout/page.jsx`
 * god component — all behavior comes in via props.
 *
 * Sprint 1.5 Part 2 (ADR-011):
 *  • «Данные для таможни» tile renamed to «Паспорт для таможни» and is
 *    now conditional on `hasCrossBorderItems`. Local-only carts render
 *    only Pickup + Recipient — there's nothing customs-related to show.
 *  • Passport sub-label surfaces the masked passport identifier
 *    («1234 5****0») when a passport is resolved; otherwise «Не выбран».
 *  • `onOpenPassport` opens `<PassportSheet />` (composed in
 *    `app/checkout/page.jsx`).
 */
export default function CheckoutTiles({
  pickup,
  recipient,
  hasCrossBorderItems = false,
  passportSummary = null,
  onOpenPickup,
  onOpenRecipient,
  onOpenPassport,
}) {
  return (
    <div className={styles.c14}>
      <button
        type="button"
        data-checkout-pickup-tile="true"
        onClick={onOpenPickup}
        className={cn(styles.c15)}
      >
        <div className={cn(styles.c16, styles.tw3)}>
          <img
            src="/icons/global/location.svg"
            alt="location"
            className={cn(styles.c17, styles.tw4)}
          />
          <div>
            <div className={styles.c18}>Пункт выдачи</div>
            <div className={styles.c19}>{pickup.pickupAddress ?? 'Не выбран'}</div>
          </div>
        </div>
        <img src="/icons/global/small-arrow.svg" alt="" className={cn(styles.c20, styles.tw5)} />
      </button>

      <button type="button" onClick={onOpenRecipient} className={cn(styles.c21)}>
        <div className={cn(styles.c22, styles.tw6)}>
          <img src="/icons/global/user.svg" alt="location" className={cn(styles.c23, styles.tw7)} />
          <div>
            <div className={styles.c24}>Получатель</div>
            <div className={styles.c25}>
              {recipient?.fullName?.trim() ? recipient.fullName : 'Не указан'}
            </div>
          </div>
        </div>
        <img src="/icons/global/small-arrow.svg" alt="" className={cn(styles.c26, styles.tw8)} />
      </button>

      {hasCrossBorderItems ? (
        <button
          type="button"
          data-checkout-passport-tile="true"
          onClick={onOpenPassport}
          className={styles.c27}
        >
          <div className={cn(styles.c28, styles.tw9)}>
            <img
              src="/icons/global/personalcard.svg"
              alt="passport"
              className={cn(styles.c29, styles.tw10)}
            />
            <div>
              <div className={styles.c30}>Паспорт для таможни</div>
              <div className={styles.c31}>{passportSummary || 'Не выбран'}</div>
            </div>
          </div>
          <img src="/icons/global/small-arrow.svg" alt="" className={cn(styles.c32, styles.tw11)} />
        </button>
      ) : null}
    </div>
  );
}
