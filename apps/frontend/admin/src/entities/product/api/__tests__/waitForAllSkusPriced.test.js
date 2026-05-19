import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { waitForAllSkusPriced } from '../waitForAllSkusPriced';

// Lightweight EventSource stub — same shape as the one in
// useSkuPricingEvents.test.jsx, kept local to avoid cross-test coupling.
class MockEventSource {
  static instances = [];
  constructor(url) {
    this.url = url;
    this.readyState = 0; // CONNECTING
    this.listeners = new Map();
    this.onerror = null;
    this.closed = false;
    MockEventSource.instances.push(this);
  }
  addEventListener(type, fn) {
    if (!this.listeners.has(type)) this.listeners.set(type, new Set());
    this.listeners.get(type).add(fn);
  }
  removeEventListener(type, fn) {
    this.listeners.get(type)?.delete(fn);
  }
  emit(type, data) {
    const fns = this.listeners.get(type);
    if (!fns) return;
    for (const fn of fns) fn({ data: JSON.stringify(data) });
  }
  close() {
    this.closed = true;
    this.readyState = 2; // CLOSED
  }
}
MockEventSource.CONNECTING = 0;
MockEventSource.OPEN = 1;
MockEventSource.CLOSED = 2;

describe('waitForAllSkusPriced', () => {
  beforeEach(() => {
    MockEventSource.instances.length = 0;
    vi.stubGlobal('EventSource', MockEventSource);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it('resolves true once every seen SKU is priced', async () => {
    const promise = waitForAllSkusPriced('p-1', { timeout: 5_000 });
    // Wait one microtask for the EventSource to be constructed.
    await Promise.resolve();
    const es = MockEventSource.instances[0];

    es.emit('status', { skuId: 'a', pricingStatus: 'pending' });
    es.emit('status', { skuId: 'b', pricingStatus: 'pending' });
    // First all-priced check happens after the second SKU lands.
    es.emit('status', { skuId: 'a', pricingStatus: 'priced' });
    es.emit('status', { skuId: 'b', pricingStatus: 'priced' });

    await expect(promise).resolves.toBe(true);
    expect(es.closed).toBe(true);
  });

  it('does not resolve when at least one SKU stays pending', async () => {
    vi.useFakeTimers();
    const promise = waitForAllSkusPriced('p-2', { timeout: 1_000 });
    await Promise.resolve();
    const es = MockEventSource.instances[0];

    // Both SKUs land in pending first — mirrors how the backend emits
    // initial recompute events before the priced batch lands.
    es.emit('status', { skuId: 'a', pricingStatus: 'pending' });
    es.emit('status', { skuId: 'b', pricingStatus: 'pending' });
    // Only 'a' recovers — 'b' stays pending. allPriced should remain false.
    es.emit('status', { skuId: 'a', pricingStatus: 'priced' });

    vi.advanceTimersByTime(1_500);
    await expect(promise).resolves.toBe(false);
    expect(es.closed).toBe(true);
  });

  it('resolves false on timeout with no events at all', async () => {
    vi.useFakeTimers();
    const promise = waitForAllSkusPriced('p-3', { timeout: 500 });
    await Promise.resolve();
    vi.advanceTimersByTime(600);
    await expect(promise).resolves.toBe(false);
  });

  it('ignores onerror while readyState is CONNECTING (transient blip)', async () => {
    const promise = waitForAllSkusPriced('p-4', { timeout: 5_000 });
    await Promise.resolve();
    const es = MockEventSource.instances[0];

    es.readyState = MockEventSource.CONNECTING;
    es.onerror?.();
    // After the blip, recompute completes normally.
    es.emit('status', { skuId: 'a', pricingStatus: 'priced' });

    await expect(promise).resolves.toBe(true);
  });

  it('resolves false when the connection is terminally closed', async () => {
    const promise = waitForAllSkusPriced('p-5', { timeout: 5_000 });
    await Promise.resolve();
    const es = MockEventSource.instances[0];

    es.readyState = MockEventSource.CLOSED;
    es.onerror?.();

    await expect(promise).resolves.toBe(false);
  });

  it('also accepts events delivered as default `message` type', async () => {
    const promise = waitForAllSkusPriced('p-6', { timeout: 5_000 });
    await Promise.resolve();
    const es = MockEventSource.instances[0];

    es.emit('message', { skuId: 'a', pricingStatus: 'priced' });
    await expect(promise).resolves.toBe(true);
  });
});
