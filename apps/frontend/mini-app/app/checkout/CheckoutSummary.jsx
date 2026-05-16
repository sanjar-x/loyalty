import cn from 'clsx';

import { formatMoney, isPositive } from '@/lib/format/money';
import { pluralizeItemsRu } from '@/lib/format/plural';

import styles from './page.module.css';

/**
 * Checkout narx-jadvali: subtotal / скидка / доставка / списать баллы / итого.
 * Audit #1: `checkout/page.jsx` god-komponentidan ajratilgan presentation
 * komponent — barcha Money qiymatlari va toggle handler prop'lar orqali.
 *
 * CHK-024 qo'shimchalari (prop'lar orqali, optional):
 *  • `quote` — joriy RateQuote (serviceName, deliveryDaysMin/Max,
 *    fallbackAlternatives, serviceCode). ETA va tarif switcher uchun.
 *  • `onSelectServiceCode(code)` — alternativ tarifga o'tish.
 *  • `hasCrossBorderItems` — DobroPost ogohlantirish ko'rsatiladimi.
 *
 * Списать баллы — backend Loyalty Points moduli (Spec §11) yoqilgandan keyin
 * `pointsEnabled` totals'dagi `pointsMoney`'ni hisoblanishiga ulanadi. Hozircha
 * toggle visual'gina ishlaydi, chegirma 0 ₽.
 */
function formatEta(quote) {
  const min = Number(quote?.deliveryDaysMin);
  const max = Number(quote?.deliveryDaysMax);
  const hasMin = Number.isFinite(min);
  const hasMax = Number.isFinite(max);
  if (!hasMin && !hasMax) return '';
  if (hasMin && hasMax && min !== max) return `${min}–${max} дн.`;
  return `${hasMin ? min : max} дн.`;
}

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
  quote = null,
  onSelectServiceCode = null,
  hasCrossBorderItems = false,
}) {
  const eta = formatEta(quote);
  const deliveryWithEta = eta ? `${deliveryPriceText} · ${eta}` : deliveryPriceText;
  const alternatives = Array.isArray(quote?.fallbackAlternatives)
    ? quote.fallbackAlternatives.filter((c) => typeof c === 'string' && c)
    : [];
  const hasAlternatives = alternatives.length > 0 && typeof onSelectServiceCode === 'function';

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
        <span>{deliveryWithEta}</span>
      </div>
      <div className={styles.c71}>
        <span className={styles.c72}>
          • {quote?.serviceName ? quote.serviceName : deliveryBulletText}
        </span>
        <span>{deliveryWithEta}</span>
      </div>

      {hasAlternatives ? (
        <div className={styles.c71} role="group" aria-label="Альтернативные тарифы">
          <span className={styles.c72}>Другие тарифы:</span>
          <span className={styles.tw20}>
            {alternatives.map((code) => (
              <button
                key={code}
                type="button"
                onClick={() => onSelectServiceCode(code)}
                aria-label={`Выбрать тариф ${code}`}
                className={cn(styles.c72)}
                style={{
                  marginLeft: 8,
                  textDecoration: 'underline',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                {code}
              </button>
            ))}
          </span>
        </div>
      ) : null}

      {hasCrossBorderItems ? (
        <div className={styles.c71} role="note">
          <span className={styles.c72}>
            ⚠ Стоимость международной доставки рассчитает менеджер после оформления заказа. Сейчас
            отображается только последняя миля по России.
          </span>
        </div>
      ) : null}

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
