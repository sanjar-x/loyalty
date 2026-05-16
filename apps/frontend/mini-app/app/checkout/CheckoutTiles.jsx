import cn from 'clsx';

import styles from './page.module.css';

/**
 * Checkout konfiguratsiya tile'lari: Пункт выдачи / Получатель / Данные для
 * таможни. Audit #1: `checkout/page.jsx` god-komponentidan ajratilgan sof
 * presentation komponent — barcha xulq prop'lar orqali keladi.
 */
export default function CheckoutTiles({
  pickup,
  recipient,
  onOpenPickup,
  onOpenRecipient,
  onOpenCustoms,
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

      <button type="button" onClick={onOpenCustoms} className={styles.c27}>
        <div className={cn(styles.c28, styles.tw9)}>
          <img
            src="/icons/global/personalcard.svg"
            alt="location"
            className={cn(styles.c29, styles.tw10)}
          />
          <div>
            <div className={styles.c30}>Данные для таможни</div>
            <div className={styles.c31}>Паспорт и ИНН</div>
          </div>
        </div>
        <img src="/icons/global/small-arrow.svg" alt="" className={cn(styles.c32, styles.tw11)} />
      </button>
    </div>
  );
}
