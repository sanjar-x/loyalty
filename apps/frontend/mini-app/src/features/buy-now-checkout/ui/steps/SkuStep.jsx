'use client';

import { useBuyNowStore } from '../../model/useBuyNowCheckout';
import styles from '../BuyNowSheet.module.css';

/**
 * Step 1 — SKU review.
 *
 * Read-only summary of the product the customer tapped «Купить сейчас»
 * on. The (sku, quantity, productMeta) tuple is supplied by the parent
 * (ProductPage / QuickAddSheet) via `useBuyNowStore.open(...)` — this
 * step doesn't fetch product data on its own to keep the sheet snappy.
 *
 * Quantity stepper (1..99) is rendered here. SKU itself is fixed: if
 * the customer wants a different size they close the sheet and pick
 * again on PDP. This matches the «one-tap» Buy Now mental model and
 * sidesteps SKU price drift mid-flow.
 *
 * Acceptance: «Дальше» moves status to RECIPIENT.
 */
export default function SkuStep() {
  const productMeta = useBuyNowStore((s) => s.productMeta);
  const quantity = useBuyNowStore((s) => s.quantity);
  const setQuantity = useBuyNowStore((s) => s.setQuantity);
  // `nextStep()` owns the FSM branching (LOCAL → PICKUP, CROSS_BORDER →
  // PASSPORT → PICKUP — see ADR-011). Consumers don't hard-code the
  // next step here.
  const nextStep = useBuyNowStore((s) => s.nextStep);

  return (
    <div className={styles.stepRoot}>
      <div className={styles.stepTitle}>1. Товар</div>

      <div className={styles.placeholder}>
        {productMeta ? (
          <>
            <strong>{productMeta.name || 'Товар'}</strong>
            {productMeta.variantLabel ? ` · ${productMeta.variantLabel}` : ''}
            {productMeta.priceRub != null ? ` · ${productMeta.priceRub} ₽` : ''}
          </>
        ) : (
          'SKU не выбран — обнови sheet с ProductPage'
        )}
      </div>

      <div className={styles.stepHint}>
        Количество (1..99)
        <input
          type="number"
          min={1}
          max={99}
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          style={{ marginLeft: 8, width: 60 }}
        />
      </div>

      <button
        type="button"
        className={styles.primaryBtn}
        onClick={nextStep}
        disabled={!productMeta?.skuId && !useBuyNowStore.getState().skuId}
        data-testid="buy-now-sku-next"
      >
        Дальше
      </button>
    </div>
  );
}
