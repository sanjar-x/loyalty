// Public API of the buy-now-checkout feature slice.
// Consumers (ProductPage, QuickAddSheet, TelegramAppShell, future tests)
// MUST import from here — deep paths are blocked by ESLint
// (FSD `no-restricted-imports`).

export { default as BuyNowSheet } from './ui/BuyNowSheet';
export { default as GlobalBuyNowSheet } from './ui/GlobalBuyNowSheet';
export { useBuyNowStore, BuyNowStep, BUY_NOW_DISABLED_TTL_MS } from './model/useBuyNowCheckout';
export {
  useBuyNowOrderMutation,
  useBuyNowRateQuoteMutation,
  isBuyNowDisabledError,
  isQuoteExpiredError,
} from './api/buyNowApi';
export { generateBuyNowIdempotencyKey } from './lib/idempotencyKey';
