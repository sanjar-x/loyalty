'use client';

import { BuyNowStep, useBuyNowStore } from '../model/useBuyNowCheckout';
import BuyNowSheet from './BuyNowSheet';

/**
 * Singleton mount of `BuyNowSheet` driven by the store. Place it once,
 * high enough in the tree (currently `widgets/TelegramAppShell`), and
 * any consumer can open the buy-now flow with a plain store call:
 *
 *   useBuyNowStore.getState().open({ skuId, quantity, productMeta })
 *
 * This breaks the previous coupling where the parent rendering the CTA
 * button (ProductPage / QuickAddSheet) also had to render the sheet.
 * Closing QuickAddSheet no longer tears down the buy-now flow, which is
 * critical because we close it on tap to surface the buy-now sheet
 * cleanly.
 */
export default function GlobalBuyNowSheet() {
  const status = useBuyNowStore((s) => s.status);
  const close = useBuyNowStore((s) => s.close);
  return <BuyNowSheet open={status !== BuyNowStep.IDLE} onClose={close} />;
}
