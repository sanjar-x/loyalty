'use client';

import { useEffect } from 'react';

import BottomSheet from '@/shared/ui/BottomSheet';

import { BuyNowStep, useBuyNowStore } from '../model/useBuyNowCheckout';
import { generateBuyNowIdempotencyKey } from '../lib/idempotencyKey';

import SkuStep from './steps/SkuStep';
import RecipientStep from './steps/RecipientStep';
import PassportStep from './steps/PassportStep';
import PickupStep from './steps/PickupStep';
import ConfirmStep from './steps/ConfirmStep';
import styles from './BuyNowSheet.module.css';

/**
 * BuyNowSheet — single bottom-sheet that orchestrates the 4-step
 * standalone purchase flow. ADR-010 I1 (cart not modified) is surfaced
 * to the customer via the «Покупка без корзины» notice at the bottom.
 *
 *   ┌─────────────────────────────────────────────┐
 *   │  Купить сейчас                       ✕      │
 *   ├─────────────────────────────────────────────┤
 *   │  [Step content — see steps/* below]         │
 *   │                                             │
 *   │  ─ ─ ─ Корзина не затронута ─ ─ ─           │
 *   └─────────────────────────────────────────────┘
 *
 * Open contract — consumers call
 *   useBuyNowStore.getState().open({ skuId, quantity, productMeta })
 * which moves status from IDLE → SKU. `<GlobalBuyNowSheet />` (mounted
 * in TelegramAppShell) subscribes to the store and shows / hides the
 * sheet automatically, so callers don't need to wire props.
 *
 * Step routing is driven by `useBuyNowStore.status`; step components
 * own their own data fetching and forward state changes via store
 * actions. The wrapper here only renders the active step and the cart
 * notice.
 *
 * Idempotency key minting: deferred until the customer reaches a
 * CONFIRM-able state — opening and bouncing out of the sheet without
 * progressing doesn't burn keys. Reset on SUCCESS / explicit close
 * (`useBuyNowStore.reset()`).
 */
export default function BuyNowSheet({ open, onClose }) {
  const status = useBuyNowStore((s) => s.status);
  const close = useBuyNowStore((s) => s.close);
  const idempotencyKey = useBuyNowStore((s) => s.idempotencyKey);
  const setIdempotencyKey = useBuyNowStore((s) => s.setIdempotencyKey);

  useEffect(() => {
    const needsKey =
      status === BuyNowStep.CONFIRM ||
      status === BuyNowStep.SUBMITTING ||
      status === BuyNowStep.ERROR;
    if (needsKey && !idempotencyKey) {
      setIdempotencyKey(generateBuyNowIdempotencyKey());
    }
  }, [status, idempotencyKey, setIdempotencyKey]);

  const handleClose = () => {
    close();
    onClose?.();
  };

  return (
    <BottomSheet
      open={open}
      onClose={handleClose}
      title="Купить сейчас"
      ariaLabel="Оформление заказа без корзины"
    >
      <div className={styles.body}>
        {status === BuyNowStep.SKU && <SkuStep />}
        {status === BuyNowStep.RECIPIENT && <RecipientStep />}
        {status === BuyNowStep.PASSPORT && <PassportStep />}
        {status === BuyNowStep.PICKUP && <PickupStep />}
        {(status === BuyNowStep.CONFIRM ||
          status === BuyNowStep.SUBMITTING ||
          status === BuyNowStep.SUCCESS ||
          status === BuyNowStep.ERROR) && <ConfirmStep onClose={handleClose} />}

        {/* ADR-010 I1 surfaced to the customer. */}
        <div className={styles.cartUnchangedNotice} role="note">
          Покупка без корзины — товары в корзине не изменятся.
        </div>
      </div>
    </BottomSheet>
  );
}
