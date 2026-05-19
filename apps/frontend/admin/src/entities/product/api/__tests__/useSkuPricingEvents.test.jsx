/**
 * Hook-level test for `useSkuPricingEvents` (CAT-005 SSE consumer).
 *
 * The hook is a thin wrapper around the browser `EventSource` API; the
 * regression we care about is *lifecycle*: opens on mount with the right URL,
 * fires the callback on `status` and `message` events, swaps the connection
 * when productId changes, and tears the connection down on unmount.
 *
 * jsdom does not ship a real EventSource — we install a small mock that
 * records every `addEventListener` call and lets tests trigger events.
 */
import { renderHook, act } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useSkuPricingEvents } from '../useSkuPricingEvents';

class MockEventSource {
  static instances = [];
  constructor(url, init) {
    this.url = url;
    this.init = init;
    this.listeners = {};
    this.closed = false;
    MockEventSource.instances.push(this);
  }
  addEventListener(name, fn) {
    if (!this.listeners[name]) this.listeners[name] = new Set();
    this.listeners[name].add(fn);
  }
  removeEventListener(name, fn) {
    this.listeners[name]?.delete(fn);
  }
  close() {
    this.closed = true;
  }
  emit(name, data) {
    const event = { data };
    for (const fn of this.listeners[name] ?? []) fn(event);
  }
}

beforeEach(() => {
  MockEventSource.instances = [];
  vi.stubGlobal('EventSource', MockEventSource);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('useSkuPricingEvents', () => {
  it('does nothing when productId is falsy', () => {
    renderHook(() => useSkuPricingEvents(null, vi.fn()));
    expect(MockEventSource.instances).toHaveLength(0);
  });

  it('opens an EventSource pointed at the BFF route and forwards `status` events', () => {
    const onEvent = vi.fn();
    renderHook(() => useSkuPricingEvents('p-123', onEvent));
    expect(MockEventSource.instances).toHaveLength(1);
    const source = MockEventSource.instances[0];
    expect(source.url).toBe('/api/catalog/products/p-123/sku-pricing-events');
    expect(source.init).toEqual({ withCredentials: true });

    const payload = {
      skuId: 'sku-1',
      pricingStatus: 'priced',
      sellingPrice: { amount: 1290000, currency: 'RUB' },
      pricedAt: '2026-05-08T09:30:00Z',
      pricedFailureReason: null,
    };
    act(() => source.emit('status', JSON.stringify(payload)));
    expect(onEvent).toHaveBeenCalledWith(payload);
  });

  it('also forwards default `message` events for servers that omit the event field', () => {
    const onEvent = vi.fn();
    renderHook(() => useSkuPricingEvents('p-123', onEvent));
    const source = MockEventSource.instances[0];
    const payload = { skuId: 'sku-2', pricingStatus: 'pending' };
    act(() => source.emit('message', JSON.stringify(payload)));
    expect(onEvent).toHaveBeenCalledWith(payload);
  });

  it('swallows malformed JSON payloads without invoking the callback', () => {
    const onEvent = vi.fn();
    renderHook(() => useSkuPricingEvents('p-123', onEvent));
    const source = MockEventSource.instances[0];
    act(() => source.emit('status', 'not-json{'));
    expect(onEvent).not.toHaveBeenCalled();
  });

  it('uses the latest callback closure even after re-renders (no stale onEvent)', () => {
    const first = vi.fn();
    const second = vi.fn();
    const { rerender } = renderHook(
      ({ cb }) => useSkuPricingEvents('p-123', cb),
      { initialProps: { cb: first } },
    );
    rerender({ cb: second });

    const source = MockEventSource.instances[0];
    act(() => source.emit('status', JSON.stringify({ skuId: 'sku-3' })));
    expect(first).not.toHaveBeenCalled();
    expect(second).toHaveBeenCalledWith({ skuId: 'sku-3' });
  });

  it('opens a fresh connection when productId changes and closes the previous one', () => {
    const onEvent = vi.fn();
    const { rerender } = renderHook(
      ({ id }) => useSkuPricingEvents(id, onEvent),
      { initialProps: { id: 'p-1' } },
    );
    rerender({ id: 'p-2' });
    expect(MockEventSource.instances).toHaveLength(2);
    expect(MockEventSource.instances[0].closed).toBe(true);
    expect(MockEventSource.instances[1].url).toBe(
      '/api/catalog/products/p-2/sku-pricing-events',
    );
  });

  it('closes the connection on unmount', () => {
    const { unmount } = renderHook(() => useSkuPricingEvents('p-123', vi.fn()));
    unmount();
    expect(MockEventSource.instances[0].closed).toBe(true);
  });
});
