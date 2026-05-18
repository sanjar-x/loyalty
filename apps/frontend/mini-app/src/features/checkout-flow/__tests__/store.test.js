import { beforeEach, describe, it, expect } from 'vitest';

import { useCheckoutStore, CheckoutStatus } from '../model/store';

beforeEach(() => {
  useCheckoutStore.getState().reset();
});

describe('checkout store — removedItemsSnapshot (CHK-004)', () => {
  it('initial state — null', () => {
    expect(useCheckoutStore.getState().removedItemsSnapshot).toBeNull();
  });

  it('setRemovedSnapshot([...]) — stores array', () => {
    const items = [
      { id: 'i1', skuId: 'sku-1', quantity: 2 },
      { id: 'i2', skuId: 'sku-2', quantity: 1 },
    ];
    useCheckoutStore.getState().setRemovedSnapshot(items);
    expect(useCheckoutStore.getState().removedItemsSnapshot).toEqual(items);
  });

  it('setRemovedSnapshot([]) — coerced to null (no zombie empty array)', () => {
    useCheckoutStore.getState().setRemovedSnapshot([]);
    expect(useCheckoutStore.getState().removedItemsSnapshot).toBeNull();
  });

  it('setRemovedSnapshot(null) — null', () => {
    useCheckoutStore.getState().setRemovedSnapshot([{ skuId: 'x', quantity: 1 }]);
    useCheckoutStore.getState().setRemovedSnapshot(null);
    expect(useCheckoutStore.getState().removedItemsSnapshot).toBeNull();
  });

  it('clearRemovedSnapshot — null', () => {
    useCheckoutStore.getState().setRemovedSnapshot([{ skuId: 'x', quantity: 1 }]);
    useCheckoutStore.getState().clearRemovedSnapshot();
    expect(useCheckoutStore.getState().removedItemsSnapshot).toBeNull();
  });

  it('reset() — clears snapshot along with everything else', () => {
    useCheckoutStore.getState().setRemovedSnapshot([{ skuId: 'x', quantity: 1 }]);
    useCheckoutStore.getState().reset();
    expect(useCheckoutStore.getState().removedItemsSnapshot).toBeNull();
  });
});

describe('checkout store — idempotent action guards (CHK-015)', () => {
  const PICKUP = {
    externalId: 'pvz-1',
    providerCode: 'cdek',
    address: 'Moscow',
  };

  it('setPickup — same payload returns identical state reference (no subscriber re-fire)', () => {
    const s = useCheckoutStore.getState();
    s.setPickup(PICKUP);
    const after1 = useCheckoutStore.getState();
    s.setPickup({ ...PICKUP }); // structurally identical
    const after2 = useCheckoutStore.getState();
    expect(after2).toBe(after1);
    expect(after2.status).toBe(CheckoutStatus.QUOTING);
  });

  it('setPickup — different externalId produces new state', () => {
    const s = useCheckoutStore.getState();
    s.setPickup(PICKUP);
    const after1 = useCheckoutStore.getState();
    s.setPickup({ ...PICKUP, externalId: 'pvz-2' });
    expect(useCheckoutStore.getState()).not.toBe(after1);
    expect(useCheckoutStore.getState().pickup.externalId).toBe('pvz-2');
  });

  it('setPickup — lat/lon delta produces new state (CHK-018)', () => {
    const s = useCheckoutStore.getState();
    s.setPickup({ ...PICKUP, lat: 55.0, lon: 37.0 });
    const after1 = useCheckoutStore.getState();
    // Same coords → no-op
    s.setPickup({ ...PICKUP, lat: 55.0, lon: 37.0 });
    expect(useCheckoutStore.getState()).toBe(after1);
    // Different lat → new state
    s.setPickup({ ...PICKUP, lat: 56.0, lon: 37.0 });
    expect(useCheckoutStore.getState()).not.toBe(after1);
    expect(useCheckoutStore.getState().pickup.lat).toBe(56.0);
  });

  it('setQuote — same quoteId returns identical state', () => {
    const s = useCheckoutStore.getState();
    s.setPickup(PICKUP);
    s.setQuote({ quoteId: 'q1', deliveryAmount: 100, currency: 'RUB' });
    const after1 = useCheckoutStore.getState();
    s.setQuote({ quoteId: 'q1', deliveryAmount: 200, currency: 'RUB' });
    expect(useCheckoutStore.getState()).toBe(after1);
  });

  it('setQuote — different quoteId produces new state', () => {
    const s = useCheckoutStore.getState();
    s.setPickup(PICKUP);
    s.setQuote({ quoteId: 'q1', deliveryAmount: 100, currency: 'RUB' });
    const after1 = useCheckoutStore.getState();
    s.setQuote({ quoteId: 'q2', deliveryAmount: 100, currency: 'RUB' });
    expect(useCheckoutStore.getState()).not.toBe(after1);
    expect(useCheckoutStore.getState().quote.quoteId).toBe('q2');
  });

  it('setAttempt — same attemptId returns identical state', () => {
    const s = useCheckoutStore.getState();
    s.setAttempt({ attemptId: 'a1', snapshotId: 'snap1', expiresAt: 'x' });
    const after1 = useCheckoutStore.getState();
    s.setAttempt({ attemptId: 'a1', snapshotId: 'snap2', expiresAt: 'y' });
    expect(useCheckoutStore.getState()).toBe(after1);
  });

  it('setOrder — same orderId at CONFIRMED returns identical state', () => {
    const s = useCheckoutStore.getState();
    s.setOrder('ord-1');
    const after1 = useCheckoutStore.getState();
    s.setOrder('ord-1');
    expect(useCheckoutStore.getState()).toBe(after1);
  });

  it('setOrder — different orderId produces new state', () => {
    const s = useCheckoutStore.getState();
    s.setOrder('ord-1');
    const after1 = useCheckoutStore.getState();
    s.setOrder('ord-2');
    expect(useCheckoutStore.getState()).not.toBe(after1);
    expect(useCheckoutStore.getState().orderId).toBe('ord-2');
  });

  it('Zustand action selectors — reference-stable across getState() calls', () => {
    // useEffect dep guarantees: these functions don't change between renders.
    const a = useCheckoutStore.getState().setPickup;
    const b = useCheckoutStore.getState().setPickup;
    expect(a).toBe(b);
  });
});

describe('checkout store — setPickup quote invalidation (CHK-024)', () => {
  const PICKUP_A = { externalId: 'pvz-A', providerCode: 'cdek', address: 'A' };
  const PICKUP_B = { externalId: 'pvz-B', providerCode: 'cdek', address: 'B' };

  it('setPickup with a different externalId — quote is reset', () => {
    const s = useCheckoutStore.getState();
    s.setPickup(PICKUP_A);
    s.setQuote({
      quoteId: 'q1',
      serviceCode: 'EC',
      deliveryAmount: 32000,
      currency: 'RUB',
      expiresAt: '2026-05-16T17:30:00Z',
    });
    expect(useCheckoutStore.getState().quote?.quoteId).toBe('q1');
    s.setPickup(PICKUP_B);
    expect(useCheckoutStore.getState().quote).toBeNull();
    expect(useCheckoutStore.getState().pickup.externalId).toBe('pvz-B');
    expect(useCheckoutStore.getState().status).toBe(CheckoutStatus.QUOTING);
  });

  it('setPickup with a different providerCode — quote is reset', () => {
    const s = useCheckoutStore.getState();
    s.setPickup({ ...PICKUP_A, providerCode: 'cdek' });
    s.setQuote({ quoteId: 'q1', deliveryAmount: 100, currency: 'RUB' });
    s.setPickup({ ...PICKUP_A, providerCode: 'yandex_delivery' });
    expect(useCheckoutStore.getState().quote).toBeNull();
  });

  it('setPickup with the same externalId — quote is preserved', () => {
    const s = useCheckoutStore.getState();
    s.setPickup(PICKUP_A);
    s.setQuote({ quoteId: 'q1', deliveryAmount: 100, currency: 'RUB' });
    // Same externalId+providerCode but different lat → new state, but quote must not be reset
    s.setPickup({ ...PICKUP_A, lat: 55, lon: 37 });
    expect(useCheckoutStore.getState().quote?.quoteId).toBe('q1');
  });
});

describe('checkout store — payment (CHK-024)', () => {
  it('initial state — null', () => {
    expect(useCheckoutStore.getState().payment).toBeNull();
  });

  it('setPayment stores metadata', () => {
    const payload = {
      paymentIntentId: 'pi-1',
      clientSecret: 'secret_x',
      totalAmount: 99500,
      currency: 'RUB',
    };
    useCheckoutStore.getState().setPayment(payload);
    expect(useCheckoutStore.getState().payment).toEqual(payload);
  });

  it('reset() clears payment', () => {
    useCheckoutStore.getState().setPayment({ paymentIntentId: 'x' });
    useCheckoutStore.getState().reset();
    expect(useCheckoutStore.getState().payment).toBeNull();
  });
});

// Sprint 3e: pvzAccumCache has been moved to entities/pickup-point/model/pvzAccumStore.
// The tests have moved accordingly (see entities/pickup-point/model/__tests__).
