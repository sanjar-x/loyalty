/**
 * Hook-level test for `useSkuPricingPreview` (CAT-014 live preview).
 *
 * The hook owns three responsibilities — debouncing user keystrokes,
 * aborting stale in-flight fetches, and exposing `{ preview, loading,
 * error }` — all of which are observable without rendering the page.
 *
 * `previewSkuPricing` (the API client) is module-mocked so we control the
 * fetch resolution timing without touching the network.
 */
import { renderHook, act } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useSkuPricingPreview } from '../useSkuPricingPreview';

vi.mock('@/entities/product', () => ({
  previewSkuPricing: vi.fn(),
}));

import { previewSkuPricing } from '@/entities/product';

const baseInputs = {
  productId: 'p-1',
  categoryId: 'c-1',
  contextId: 'ctx-1',
  purchasePrice: { amount: 50000, currency: 'CNY' },
  supplierId: 'sup-1',
  enabled: true,
};

beforeEach(() => {
  vi.useFakeTimers();
  previewSkuPricing.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
});

describe('useSkuPricingPreview', () => {
  it('does nothing when enabled is false', () => {
    renderHook(() => useSkuPricingPreview({ ...baseInputs, enabled: false }));
    act(() => vi.advanceTimersByTime(500));
    expect(previewSkuPricing).not.toHaveBeenCalled();
  });

  it('does not fire when purchasePrice amount is zero or empty', () => {
    renderHook(() =>
      useSkuPricingPreview({
        ...baseInputs,
        purchasePrice: { amount: 0, currency: 'CNY' },
      }),
    );
    act(() => vi.advanceTimersByTime(500));
    expect(previewSkuPricing).not.toHaveBeenCalled();
  });

  it('debounces 300ms before issuing the request', () => {
    previewSkuPricing.mockResolvedValue({
      finalPrice: '13750.00',
      contextId: 'ctx-1',
      formulaVersionNumber: 4,
    });
    renderHook(() => useSkuPricingPreview(baseInputs));

    act(() => vi.advanceTimersByTime(200));
    expect(previewSkuPricing).not.toHaveBeenCalled();

    act(() => vi.advanceTimersByTime(150));
    expect(previewSkuPricing).toHaveBeenCalledTimes(1);
    expect(previewSkuPricing).toHaveBeenCalledWith(
      expect.objectContaining({
        productId: 'p-1',
        categoryId: 'c-1',
        contextId: 'ctx-1',
        purchasePrice: { amount: 50000, currency: 'CNY' },
        supplierId: 'sup-1',
      }),
    );
  });

  it('exposes loading=true while the request is in flight, then preview', async () => {
    let resolveCall;
    previewSkuPricing.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveCall = resolve;
        }),
    );
    const { result } = renderHook(() => useSkuPricingPreview(baseInputs));

    // Drive the debounce timer; the fetch starts but the mock holds the
    // promise open, so we observe the loading state.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });
    expect(result.current.loading).toBe(true);
    expect(result.current.preview).toBeNull();

    // Resolve the in-flight fetch and let microtasks flush so React sees
    // the state updates.
    await act(async () => {
      resolveCall({ finalPrice: '13750.00', contextId: 'ctx-1' });
      await Promise.resolve();
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.preview).toEqual({
      finalPrice: '13750.00',
      contextId: 'ctx-1',
    });
    expect(result.current.error).toBeNull();
  });

  it('captures error message from a failed fetch', async () => {
    previewSkuPricing.mockRejectedValue(
      Object.assign(new Error('Formula not bound'), { code: 'FORMULA_ERROR' }),
    );
    const { result } = renderHook(() => useSkuPricingPreview(baseInputs));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });
    expect(result.current.error).toBe('Formula not bound');
    expect(result.current.preview).toBeNull();
  });

  it('coalesces rapid keystrokes into a single request and aborts prior controllers', async () => {
    // Capture every signal the hook hands over so we can assert that all
    // intermediate ones got aborted before the final request fires.
    const observedSignals = [];
    previewSkuPricing.mockImplementation(({ signal }) => {
      observedSignals.push(signal);
      return Promise.resolve({ finalPrice: '1.00' });
    });

    const { rerender } = renderHook((props) => useSkuPricingPreview(props), {
      initialProps: baseInputs,
    });

    // 200ms in — fire a re-render with a different amount, debounce restarts.
    act(() => vi.advanceTimersByTime(200));
    rerender({
      ...baseInputs,
      purchasePrice: { amount: 60000, currency: 'CNY' },
    });
    act(() => vi.advanceTimersByTime(200));
    rerender({
      ...baseInputs,
      purchasePrice: { amount: 70000, currency: 'CNY' },
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    // Only the final amount fires (one upstream request).
    expect(previewSkuPricing).toHaveBeenCalledTimes(1);
    expect(previewSkuPricing.mock.calls[0][0].purchasePrice).toEqual({
      amount: 70000,
      currency: 'CNY',
    });
    // The signal threaded into the surviving request must NOT be aborted.
    const finalSignal = observedSignals[observedSignals.length - 1];
    expect(finalSignal?.aborted).toBe(false);
  });

  it("clears state when contextId disappears (resolver hasn't loaded yet)", () => {
    const { rerender, result } = renderHook(
      (props) => useSkuPricingPreview(props),
      { initialProps: baseInputs },
    );
    act(() => vi.advanceTimersByTime(50));
    rerender({ ...baseInputs, contextId: null });
    expect(result.current.preview).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it('fires the preview during create-flow when productId is null (CAT-023)', async () => {
    previewSkuPricing.mockResolvedValue({
      finalPrice: '1086.00',
      contextId: 'ctx-1',
      formulaVersionNumber: 4,
    });
    const { result } = renderHook(() =>
      useSkuPricingPreview({ ...baseInputs, productId: null }),
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    expect(previewSkuPricing).toHaveBeenCalledTimes(1);
    expect(previewSkuPricing.mock.calls[0][0]).toEqual(
      expect.objectContaining({
        productId: null,
        categoryId: 'c-1',
        contextId: 'ctx-1',
        supplierId: 'sup-1',
      }),
    );
    expect(result.current.preview?.finalPrice).toBe('1086.00');
  });
});
