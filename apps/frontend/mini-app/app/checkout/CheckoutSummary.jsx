import cn from 'clsx';

import { formatMoney, isPositive } from '@/lib/format/money';
import { pluralizeItemsRu } from '@/lib/format/plural';

import styles from './page.module.css';

/**
 * Checkout narx-jadvali: subtotal / скидка / доставка / списать баллы / итого.
 * Audit #1: `checkout/page.jsx` god-komponentidan ajratilgan presentation
 * komponent — barcha Money qiymatlari va toggle handler prop'lar orqali.
 *
 * Списать баллы — backend Loyalty Points moduli (Spec §11) yoqilgandan keyin
 * `pointsEnabled` totals'dagi `pointsMoney`'ni hisoblanishiga ulanadi. Hozircha
 * toggle visual'gina ishlaydi, chegirma 0 ₽.
 */
export default function CheckoutSummary({
  selectedQuantity,
  subtotalMoney,
  discountMoney,
  promo,
  deliveryPriceText,
  deliveryBulletText,
  pointsMoney,
  pointsEnabled,
  onTogglePoints,
  totalMoney,
}) {
  return (
    <div className={cn(styles.c60, styles.spaceY2)}>
      <div className={styles.c61}>
        <span>
          {selectedQuantity} {pluralizeItemsRu(selectedQuantity)}
        </span>
        <span className={styles.c62}>{formatMoney(subtotalMoney)}</span>
      </div>

      <div className={styles.c63}>
        <span className={cn(styles.c64, styles.tw20)}>
          <span>Скидка</span>
          <img src="/icons/global/small-arrow.svg" alt="" className={cn(styles.c65, styles.tw21)} />
        </span>
        <span>{isPositive(discountMoney) ? `-${formatMoney(discountMoney)}` : '0 ₽'}</span>
      </div>
      {isPositive(discountMoney) && promo ? (
        <div className={styles.c66}>
          <span className={styles.c67}>• Промокод {promo.code}</span>
          <span>-{formatMoney(discountMoney)}</span>
        </div>
      ) : null}

      <div className={styles.c68}>
        <span className={cn(styles.c69, styles.tw22)}>
          <span>Доставка</span>
          <img src="/icons/global/small-arrow.svg" alt="" className={cn(styles.c70, styles.tw23)} />
        </span>
        <span>{deliveryPriceText}</span>
      </div>
      <div className={styles.c71}>
        <span className={styles.c72}>• {deliveryBulletText}</span>
        <span>{deliveryPriceText}</span>
      </div>

      <div className={styles.c73}>
        <span className={styles.c74}>Списать баллы</span>
        <div className={cn(styles.c75, styles.tw24)}>
          <span className={styles.c76}>
            {isPositive(pointsMoney) ? `-${formatMoney(pointsMoney)}` : ''}
          </span>
          <button
            type="button"
            aria-label="Списать баллы"
            onClick={onTogglePoints}
            className={cn(styles.toggle, pointsEnabled ? styles.toggleOn : styles.toggleOff)}
          >
            <span
              className={cn(
                styles.toggleThumb,
                pointsEnabled ? styles.toggleThumbOn : styles.toggleThumbOff
              )}
            />
          </button>
        </div>
      </div>

      <div className={styles.c77}>
        <span className={styles.c78}>Итого</span>
        <span className={styles.c79}>{formatMoney(totalMoney)}</span>
      </div>
    </div>
  );
}
