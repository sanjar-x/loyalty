import { cn } from '@/shared/lib/ui-utils';

import { formatMoney, isPositive } from '@/shared/lib/money';
import { pluralizeItemsRu } from '@/shared/lib/i18n';

import styles from './page.module.css';

/**
 * Checkout price table: subtotal / discount / delivery / points / total.
 * Audit #1: a presentation component split out of the `checkout/page.jsx`
 * god component — all Money values and the toggle handler come in via props.
 *
 * CHK-024 additions (via props, optional):
 *  • `quote` — current RateQuote (serviceName, deliveryDaysMin/Max,
 *    fallbackAlternatives, serviceCode). For ETA and the tariff switcher.
 *  • `onSelectServiceCode(code)` — switch to an alternative tariff.
 *  • `hasCrossBorderItems` — whether to show the DobroPost warning.
 *
 * "Списать баллы" — once the backend Loyalty Points module (Spec §11) is
 * enabled, `pointsEnabled` will be wired to the calculation of `pointsMoney`
 * in totals. For now the toggle only works visually, the discount is 0 ₽.
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
