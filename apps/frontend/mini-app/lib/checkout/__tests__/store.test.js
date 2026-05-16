import { beforeEach, describe, it, expect } from 'vitest';

import { useCheckoutStore, CheckoutStatus } from '../store';

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
    // useEffect dep guarantees: shu funksiyalar render orasida o'zgarmaydi.
    const a = useCheckoutStore.getState().setPickup;
    const b = useCheckoutStore.getState().setPickup;
    expect(a).toBe(b);
  });
});

describe('checkout store — pvzAccumCache (CHK-016 Bug #3)', () => {
  it('initial state — null', () => {
    expect(useCheckoutStore.getState().pvzAccumCache).toBeNull();
  });

  it('setPvzAccumEntries — stores entries array verbatim', () => {
    const entries = [
      ['pvz-1', { id: 'pvz-1', lat: 55.0, lon: 37.0 }],
      ['pvz-2', { id: 'pvz-2', lat: 56.0, lon: 38.0 }],
    ];
    useCheckoutStore.getState().setPvzAccumEntries(entries);
    expect(useCheckoutStore.getState().pvzAccumCache).toEqual(entries);
  });

  it('setPvzAccumEntries — non-array coerces to null', () => {
    useCheckoutStore.getState().setPvzAccumEntries([['x', {}]]);
    useCheckoutStore.getState().setPvzAccumEntries(null);
    expect(useCheckoutStore.getState().pvzAccumCache).toBeNull();
  });

  it('setPvzAccumEntries — empty array preserved (legit clear)', () => {
    useCheckoutStore.getState().setPvzAccumEntries([]);
    expect(useCheckoutStore.getState().pvzAccumCache).toEqual([]);
  });
});
