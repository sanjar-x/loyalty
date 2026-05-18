import { cn } from '@/shared/lib/ui-utils';

import { formatRubFloat } from '@/shared/lib/money';

import styles from './page.module.css';

/**
 * Checkout items list — grouped by delivery text, or in the empty state
 * shows "Выберите товары" + return-to-cart. Audit #1:
 * presentation component split out of the `checkout/page.jsx` god component.
 */
export default function CheckoutItemsList({
  selectedQuantity,
  groupedByDelivery,
  deliveryPriceText,
  onReturnToCart,
}) {
  if (selectedQuantity === 0) {
    return (
      <div className={styles.c33}>
        <div className={styles.c34}>Выберите товары</div>
        <button type="button" onClick={onReturnToCart} className={cn(styles.c35, styles.tw12)}>
          Вернуться в корзину
        </button>
      </div>
    );
  }

  return (
    <div className={cn(styles.c36, styles.spaceY2)}>
      {groupedByDelivery.map(([deliveryText, groupItems]) => {
        const first = groupItems[0];
        return (
          <div key={deliveryText} className={cn(styles.c37, styles.spaceY14)}>
            <div className={styles.c38}>
              <div className={cn(styles.c39, styles.tw13)}>
                <span className={cn(styles.c40, styles.tw14)} />
                <div>
                  <span className={styles.c41}>{deliveryText}</span>
                  <div className={styles.c42}>В пункт выдачи {deliveryPriceText}</div>
                  {first?.shippingText?.trim() ? (
                    <div className={styles.c43}>{first.shippingText}</div>
                  ) : null}
                </div>
              </div>
            </div>

            {groupItems.map((x) => (
              <div key={x.id} className={cn(styles.c44, styles.tw15)}>
                <div className={cn(styles.c45, styles.tw16)}>
                  <img src={x.image} alt={x.name} className={styles.c46} />
                </div>
                <div className={cn(styles.c47, styles.tw17)}>
                  <div className={styles.c48}>{x.name}</div>
                  <div className={styles.c49}>
                    {x.size && (
                      <>
                        Размер: <span className={styles.c50}>{x.size}</span>
                      </>
                    )}
                    {x.article && (
                      <>
                        {x.size && ' · '}Артикул: <span className={styles.c51}>{x.article}</span>
                      </>
                    )}
                  </div>
                  <div className={styles.c52}>{formatRubFloat(x.priceRub)}</div>
                </div>
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}
