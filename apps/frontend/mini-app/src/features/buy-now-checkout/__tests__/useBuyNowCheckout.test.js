/**
 * FSM-store tests for `useBuyNowStore`. Covers:
 *  • happy-path step transitions (SKU → RECIPIENT → PICKUP → CONFIRM → SUCCESS)
 *  • partialize whitelist (quote / idempotencyKey / orderId / payment /
 *    error / disabledReason MUST NOT persist)
 *  • re-hydrate from sessionStorage
 *  • reset() wipes both runtime state and persisted blob
 *  • error propagation: setError moves status to ERROR but keeps step data
 *  • Sprint 1.5 kill-switch: disabledReason TTL self-heal + non-persist
 *
 * Notes:
 *  • Tests run against the real Zustand store; we use sessionStorage
 *    (provided by jsdom) and reset between cases via `store.reset() +
 *    sessionStorage.clear()`.
 *  • `vi.useFakeTimers()` for the TTL test — `Date.now()` is mocked so
 *    we don't sleep 5 min in CI.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  BUY_NOW_DISABLED_TTL_MS,
  BuyNowStep,
  supplierTypeRequiresPassport,
  useBuyNowStore,
} from '../model/useBuyNowCheckout';

const STORAGE_KEY = 'lm-buy-now-store';

function snapshot() {
  return useBuyNowStore.getState();
}

function readPersisted() {
  const raw = sessionStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    const doc = JSON.parse(raw);
    return doc?.state ?? doc;
  } catch {
    return null;
  }
}

beforeEach(() => {
  useBuyNowStore.getState().reset();
  sessionStorage.clear();
});

afterEach(() => {
  vi.useRealTimers();
  useBuyNowStore.getState().reset();
  sessionStorage.clear();
});

describe('useBuyNowStore — lifecycle and step transitions', () => {
  it('starts in IDLE with default fields', () => {
    const s = snapshot();
    expect(s.status).toBe(BuyNowStep.IDLE);
    expect(s.skuId).toBeNull();
    expect(s.recipientId).toBeNull();
    expect(s.pickup).toBeNull();
    expect(s.quote).toBeNull();
    expect(s.orderId).toBeNull();
    expect(s.payment).toBeNull();
    expect(s.error).toBeNull();
    expect(s.disabledReason).toBeNull();
  });

  it('open(...) moves IDLE → SKU and stores skuId / quantity / productMeta', () => {
    snapshot().open({
      skuId: 'sku-1',
      quantity: 2,
      productMeta: { name: 'X', priceRub: 100 },
    });
    const s = snapshot();
    expect(s.status).toBe(BuyNowStep.SKU);
    expect(s.skuId).toBe('sku-1');
    expect(s.quantity).toBe(2);
    expect(s.productMeta).toEqual({ name: 'X', priceRub: 100 });
  });

  it('clamps quantity to [1..99] on open and setQuantity', () => {
    const { open, setQuantity } = snapshot();
    open({ skuId: 'sku-1', quantity: 9999 });
    expect(snapshot().quantity).toBe(99);
    setQuantity(0);
    expect(snapshot().quantity).toBe(1);
    setQuantity(50);
    expect(snapshot().quantity).toBe(50);
  });

  it('happy-path: SKU → RECIPIENT → PICKUP → CONFIRM → SUBMITTING → SUCCESS', () => {
    const { open, goToStep, setRecipientId, setPickup, setQuote, beginSubmit, setSuccess } =
      snapshot();
    open({ skuId: 'sku-1', quantity: 1 });
    expect(snapshot().status).toBe(BuyNowStep.SKU);

    goToStep(BuyNowStep.RECIPIENT);
    setRecipientId('rcp-1');
    expect(snapshot().status).toBe(BuyNowStep.RECIPIENT);
    expect(snapshot().recipientId).toBe('rcp-1');

    goToStep(BuyNowStep.PICKUP);
    setPickup({ externalId: 'pvz-1', providerCode: 'cdek', address: 'Адрес' });
    setQuote({ quoteId: 'q-1', deliveryAmount: 50000, currency: 'RUB' });
    expect(snapshot().pickup.externalId).toBe('pvz-1');
    expect(snapshot().quote.quoteId).toBe('q-1');

    goToStep(BuyNowStep.CONFIRM);
    beginSubmit();
    expect(snapshot().status).toBe(BuyNowStep.SUBMITTING);

    setSuccess({
      orderId: 'order-1',
      payment: {
        paymentIntentId: 'pi-1',
        clientSecret: null,
        totalAmount: 12500,
        currency: 'RUB',
        autoCaptured: true,
      },
    });
    const s = snapshot();
    expect(s.status).toBe(BuyNowStep.SUCCESS);
    expect(s.orderId).toBe('order-1');
    expect(s.payment.autoCaptured).toBe(true);
    expect(s.error).toBeNull();
  });

  it('setPickup drops stale quote when externalId or providerCode changes', () => {
    const { open, setPickup, setQuote } = snapshot();
    open({ skuId: 'sku-1', quantity: 1 });
    setPickup({ externalId: 'pvz-1', providerCode: 'cdek' });
    setQuote({ quoteId: 'q-1', deliveryAmount: 100 });

    // Same point — quote preserved.
    setPickup({ externalId: 'pvz-1', providerCode: 'cdek' });
    expect(snapshot().quote?.quoteId).toBe('q-1');

    // Different point — quote cleared so PickupStep refetches.
    setPickup({ externalId: 'pvz-2', providerCode: 'cdek' });
    expect(snapshot().quote).toBeNull();
  });

  it('open with a different skuId clears stale quote / orderId / payment', () => {
    const { open, setQuote, setSuccess } = snapshot();
    open({ skuId: 'sku-1', quantity: 1 });
    setQuote({ quoteId: 'q-1', deliveryAmount: 100 });
    setSuccess({
      orderId: 'order-x',
      payment: { paymentIntentId: 'pi-x', autoCaptured: true },
    });

    open({ skuId: 'sku-2', quantity: 1 });
    const s = snapshot();
    expect(s.skuId).toBe('sku-2');
    expect(s.quote).toBeNull();
    expect(s.orderId).toBeNull();
    expect(s.payment).toBeNull();
  });

  it('setError moves status to ERROR but preserves step data', () => {
    const { open, setRecipientId, setError } = snapshot();
    open({ skuId: 'sku-1', quantity: 1 });
    setRecipientId('rcp-1');

    setError({ code: 'ORDER_DELIVERY_QUOTE_EXPIRED', message: 'Срок истёк' });
    const s = snapshot();
    expect(s.status).toBe(BuyNowStep.ERROR);
    expect(s.error?.code).toBe('ORDER_DELIVERY_QUOTE_EXPIRED');
    expect(s.recipientId).toBe('rcp-1');
    expect(s.skuId).toBe('sku-1');
  });

  it('close() returns to IDLE and clears error', () => {
    const { open, setError, close } = snapshot();
    open({ skuId: 'sku-1', quantity: 1 });
    setError({ code: 'X' });
    close();
    expect(snapshot().status).toBe(BuyNowStep.IDLE);
    expect(snapshot().error).toBeNull();
  });

  it('reset() wipes all state, including sessionStorage blob', () => {
    const { open, setRecipientId, setPassportId, reset } = snapshot();
    open({ skuId: 'sku-1', quantity: 1 });
    setRecipientId('rcp-1');
    setPassportId('pp-1');
    expect(readPersisted()?.recipientId).toBe('rcp-1');
    expect(readPersisted()?.passportId).toBe('pp-1');

    reset();
    const s = snapshot();
    expect(s.status).toBe(BuyNowStep.IDLE);
    expect(s.skuId).toBeNull();
    expect(s.recipientId).toBeNull();
    expect(s.passportId).toBeNull();
    // Persisted snapshot also reflects the wipe (initialState).
    expect(readPersisted()?.recipientId).toBeNull();
    expect(readPersisted()?.passportId).toBeNull();
  });
});

describe('useBuyNowStore — Passport FSM branch (ADR-011)', () => {
  it('supplierTypeRequiresPassport recognises only "cross_border"', () => {
    expect(supplierTypeRequiresPassport('cross_border')).toBe(true);
    expect(supplierTypeRequiresPassport('CROSS_BORDER')).toBe(true);
    expect(supplierTypeRequiresPassport('local')).toBe(false);
    expect(supplierTypeRequiresPassport(null)).toBe(false);
    expect(supplierTypeRequiresPassport(undefined)).toBe(false);
    expect(supplierTypeRequiresPassport('')).toBe(false);
  });

  it('LOCAL supplier: nextStep() skips PASSPORT (SKU → RECIPIENT → PICKUP → CONFIRM)', () => {
    const { open, nextStep } = snapshot();
    open({
      skuId: 'sku-local',
      quantity: 1,
      productMeta: { name: 'Local', supplierType: 'local' },
    });
    expect(snapshot().status).toBe(BuyNowStep.SKU);
    nextStep();
    expect(snapshot().status).toBe(BuyNowStep.RECIPIENT);
    nextStep();
    expect(snapshot().status).toBe(BuyNowStep.PICKUP);
    nextStep();
    expect(snapshot().status).toBe(BuyNowStep.CONFIRM);
  });

  it('CROSS_BORDER supplier: nextStep() routes through PASSPORT', () => {
    const { open, nextStep } = snapshot();
    open({
      skuId: 'sku-xb',
      quantity: 1,
      productMeta: { name: 'XB', supplierType: 'cross_border' },
    });
    nextStep(); // SKU → RECIPIENT
    expect(snapshot().status).toBe(BuyNowStep.RECIPIENT);
    nextStep(); // RECIPIENT → PASSPORT
    expect(snapshot().status).toBe(BuyNowStep.PASSPORT);
    nextStep(); // PASSPORT → PICKUP
    expect(snapshot().status).toBe(BuyNowStep.PICKUP);
    nextStep(); // PICKUP → CONFIRM
    expect(snapshot().status).toBe(BuyNowStep.CONFIRM);
  });

  it('prevStep() reverses the FSM symmetrically for both supplier types', () => {
    const { open, nextStep, prevStep } = snapshot();
    open({
      skuId: 'sku-xb',
      quantity: 1,
      productMeta: { name: 'XB', supplierType: 'cross_border' },
    });
    nextStep();
    nextStep();
    nextStep();
    expect(snapshot().status).toBe(BuyNowStep.PICKUP);
    prevStep();
    expect(snapshot().status).toBe(BuyNowStep.PASSPORT);
    prevStep();
    expect(snapshot().status).toBe(BuyNowStep.RECIPIENT);

    // LOCAL: PICKUP → RECIPIENT (skip PASSPORT)
    snapshot().reset();
    open({
      skuId: 'sku-local',
      quantity: 1,
      productMeta: { name: 'Local', supplierType: 'local' },
    });
    nextStep();
    nextStep();
    expect(snapshot().status).toBe(BuyNowStep.PICKUP);
    prevStep();
    expect(snapshot().status).toBe(BuyNowStep.RECIPIENT);
  });

  it('setPassportId stores the id and clears error; clearPassportId wipes it', () => {
    const { open, setPassportId, clearPassportId, setError } = snapshot();
    open({
      skuId: 'sku-xb',
      quantity: 1,
      productMeta: { supplierType: 'cross_border' },
    });
    setError({ code: 'X' });
    setPassportId('pp-1');
    expect(snapshot().passportId).toBe('pp-1');
    expect(snapshot().error).toBeNull();

    clearPassportId();
    expect(snapshot().passportId).toBeNull();
  });

  it('open() with a different skuId clears passportId (alongside quote/orderId/payment)', () => {
    const { open, setPassportId } = snapshot();
    open({ skuId: 'sku-1', quantity: 1 });
    setPassportId('pp-1');
    expect(snapshot().passportId).toBe('pp-1');

    open({ skuId: 'sku-2', quantity: 1 });
    expect(snapshot().passportId).toBeNull();
  });

  it('persisted blob carries passportId (whitelist contains it)', () => {
    const { open, setPassportId } = snapshot();
    open({
      skuId: 'sku-xb',
      quantity: 1,
      productMeta: { supplierType: 'cross_border' },
    });
    setPassportId('pp-99');
    expect(readPersisted()?.passportId).toBe('pp-99');
  });

  it('re-hydrate from sessionStorage restores passportId', () => {
    sessionStorage.setItem(
      'lm-buy-now-store',
      JSON.stringify({
        state: {
          status: BuyNowStep.PASSPORT,
          skuId: 'sku-restore',
          quantity: 1,
          productMeta: { supplierType: 'cross_border' },
          recipientId: 'rcp-7',
          passportId: 'pp-7',
          pickup: null,
        },
        version: 0,
      })
    );

    return useBuyNowStore.persist.rehydrate().then(() => {
      const s = snapshot();
      expect(s.status).toBe(BuyNowStep.PASSPORT);
      expect(s.recipientId).toBe('rcp-7');
      expect(s.passportId).toBe('pp-7');
    });
  });
});

describe('useBuyNowStore — persist contract', () => {
  it('partialize whitelist excludes volatile / per-attempt / kill-switch fields', () => {
    const {
      open,
      setRecipientId,
      setPickup,
      setQuote,
      setIdempotencyKey,
      beginSubmit,
      setSuccess,
      setError,
      markDisabled,
    } = snapshot();

    open({ skuId: 'sku-1', quantity: 3, productMeta: { name: 'Y' } });
    setRecipientId('rcp-1');
    setPickup({ externalId: 'pvz-1', providerCode: 'cdek', address: 'Адрес' });
    setQuote({ quoteId: 'q-1', deliveryAmount: 100, currency: 'RUB' });
    setIdempotencyKey('buy-now-20260519-aabbccdd');
    beginSubmit();
    setSuccess({
      orderId: 'order-1',
      payment: { paymentIntentId: 'pi-1', autoCaptured: true },
    });
    setError({ code: 'X', message: 'oops' });
    markDisabled('BUY_NOW_DISABLED');

    const persisted = readPersisted();
    expect(persisted).not.toBeNull();

    // PERSIST: identity + step + selections + productMeta.
    expect(persisted.skuId).toBe('sku-1');
    expect(persisted.quantity).toBe(3);
    expect(persisted.recipientId).toBe('rcp-1');
    expect(persisted.pickup?.externalId).toBe('pvz-1');
    expect(persisted.productMeta?.name).toBe('Y');

    // SKIP: every volatile / per-attempt / kill-switch field.
    expect(persisted.quote).toBeUndefined();
    expect(persisted.idempotencyKey).toBeUndefined();
    expect(persisted.orderId).toBeUndefined();
    expect(persisted.payment).toBeUndefined();
    expect(persisted.error).toBeUndefined();
    expect(persisted.disabledReason).toBeUndefined();
    expect(persisted.disabledUntil).toBeUndefined();
  });

  it('SUBMITTING status is downgraded to CONFIRM in the persisted blob', () => {
    const { open, beginSubmit } = snapshot();
    open({ skuId: 'sku-1', quantity: 1 });
    beginSubmit();
    expect(snapshot().status).toBe(BuyNowStep.SUBMITTING);

    // Mid-flight reload must not resume the in-flight POST; CONFIRM is
    // the safe step for the customer to retry from.
    expect(readPersisted()?.status).toBe(BuyNowStep.CONFIRM);
  });

  it('persisted blob round-trips through reset → manual restore', () => {
    // Simulate a fresh page load by pre-seeding sessionStorage with a
    // persisted snapshot, then calling the store's persist API.
    sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        state: {
          status: BuyNowStep.PICKUP,
          skuId: 'sku-99',
          quantity: 1,
          productMeta: { name: 'Re-hydrated' },
          recipientId: 'rcp-99',
          pickup: { externalId: 'pvz-99', providerCode: 'cdek' },
        },
        version: 0,
      })
    );

    return useBuyNowStore.persist.rehydrate().then(() => {
      const s = snapshot();
      expect(s.status).toBe(BuyNowStep.PICKUP);
      expect(s.skuId).toBe('sku-99');
      expect(s.recipientId).toBe('rcp-99');
      expect(s.productMeta?.name).toBe('Re-hydrated');
      // Volatile fields stay at initialState defaults.
      expect(s.quote).toBeNull();
      expect(s.idempotencyKey).toBeNull();
      expect(s.orderId).toBeNull();
      expect(s.payment).toBeNull();
      expect(s.error).toBeNull();
      expect(s.disabledReason).toBeNull();
    });
  });
});

describe('useBuyNowStore — kill-switch (BUY_NOW_DISABLED)', () => {
  it('markDisabled() sets reason + deadline = now + TTL', () => {
    vi.useFakeTimers();
    const t0 = 1_700_000_000_000;
    vi.setSystemTime(t0);

    snapshot().markDisabled('BUY_NOW_DISABLED');
    const s = snapshot();
    expect(s.disabledReason).toBe('BUY_NOW_DISABLED');
    expect(s.disabledUntil).toBe(t0 + BUY_NOW_DISABLED_TTL_MS);
  });

  it('isDisabledNow() returns true within TTL, false (self-heal) after', () => {
    vi.useFakeTimers();
    const t0 = 1_700_000_000_000;
    vi.setSystemTime(t0);
    snapshot().markDisabled();

    expect(snapshot().isDisabledNow()).toBe(true);

    vi.setSystemTime(t0 + BUY_NOW_DISABLED_TTL_MS + 1);
    expect(snapshot().isDisabledNow()).toBe(false);
    // self-heal cleared the fields.
    expect(snapshot().disabledReason).toBeNull();
    expect(snapshot().disabledUntil).toBe(0);
  });

  it('clearDisabled() resets the kill-switch immediately', () => {
    snapshot().markDisabled();
    snapshot().clearDisabled();
    expect(snapshot().disabledReason).toBeNull();
    expect(snapshot().disabledUntil).toBe(0);
  });

  it('disabledReason / disabledUntil never appear in the persisted blob', () => {
    snapshot().markDisabled();
    const persisted = readPersisted();
    // partialize keeps only the whitelist — verify both keys are absent.
    expect(persisted?.disabledReason).toBeUndefined();
    expect(persisted?.disabledUntil).toBeUndefined();
  });
});
