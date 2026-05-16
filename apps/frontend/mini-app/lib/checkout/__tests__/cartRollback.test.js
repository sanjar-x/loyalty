/**
 * CHK-004: cartRollback helper unit testlari.
 *
 * `useCheckoutFlow.placeOrder` scenariolari sahnasi:
 *   1) 5 ta tovar, 3 tanlangan, initiate fail → 2 ta restore
 *   2) 5/3, confirm fail → 2 ta restore
 *   3) 5/3, success → restore yo'q (snapshot helper darajasida bo'sh kelmasligi
 *      uchun placeOrder muvaffaqiyatdan keyin `clearRemovedSnapshot()` chaqiradi —
 *      helper hech qachon chaqirilmasligi mumkin)
 *   4) 5/3, 1 ta add fail → qolgan 1 ta qaytadi (best-effort)
 *   5) 5/5 → prepareCart early return → snapshot bo'sh → helper no-op
 *
 * Helper darajasida 1-5 ni scenariosini har xil snapshot va mutation
 * mock'lari bilan reproductiyalaymiz.
 */

import { describe, it, expect, vi } from 'vitest';

import { restoreCartItems } from '../cartRollback';

function makeTrigger(impls) {
  let i = 0;
  const fn = vi.fn((arg) => ({
    unwrap: () => {
      const handler = impls[i] || impls[impls.length - 1];
      i += 1;
      if (typeof handler === 'function') return Promise.resolve(handler(arg));
      if (handler && handler.reject) return Promise.reject(handler.reject);
      return Promise.resolve(handler);
    },
  }));
  return fn;
}

describe('restoreCartItems (CHK-004)', () => {
  it('scenario 1: initiate fail snapshot — restores both items (s4, s5)', async () => {
    const snapshot = [
      { skuId: 's4', quantity: 1 },
      { skuId: 's5', quantity: 2 },
    ];
    const trigger = makeTrigger([{ ok: true }, { ok: true }]);

    const stats = await restoreCartItems(snapshot, trigger);

    expect(trigger).toHaveBeenCalledTimes(2);
    expect(trigger.mock.calls.map((c) => c[0])).toEqual([
      { skuId: 's4', quantity: 1 },
      { skuId: 's5', quantity: 2 },
    ]);
    expect(stats).toEqual({ ok: 2, failed: 0 });
  });

  it('scenario 2: confirm fail snapshot — same restore behavior', async () => {
    const snapshot = [
      { skuId: 's4', quantity: 3 },
      { skuId: 's5', quantity: 1 },
    ];
    const trigger = makeTrigger([{ ok: true }, { ok: true }]);

    await restoreCartItems(snapshot, trigger);

    expect(trigger).toHaveBeenCalledTimes(2);
  });

  it('scenario 3: success — placeOrder does not call helper (snapshot stays cleared)', async () => {
    // Helper'ning o'zi: bo'sh snapshot → 0 chaqiruv.
    const trigger = vi.fn();
    const stats = await restoreCartItems(null, trigger);
    expect(trigger).not.toHaveBeenCalled();
    expect(stats).toEqual({ ok: 0, failed: 0 });
  });

  it('scenario 4: best-effort — one addCartItem fails, other succeeds', async () => {
    const snapshot = [
      { skuId: 's4', quantity: 1 },
      { skuId: 's5', quantity: 1 },
    ];
    const trigger = makeTrigger([{ reject: { code: 'PRICE_DRIFT' } }, { ok: true }]);

    const stats = await restoreCartItems(snapshot, trigger);

    expect(trigger).toHaveBeenCalledTimes(2);
    expect(stats).toEqual({ ok: 1, failed: 1 });
  });

  it('scenario 5: 5/5 selected → snapshot empty → no calls', async () => {
    const trigger = vi.fn();
    const stats = await restoreCartItems([], trigger);
    expect(trigger).not.toHaveBeenCalled();
    expect(stats).toEqual({ ok: 0, failed: 0 });
  });

  it('guards: invalid snapshot entries skipped, not thrown', async () => {
    const trigger = makeTrigger([{ ok: true }]);
    const stats = await restoreCartItems(
      [{ skuId: '', quantity: 1 }, null, { skuId: 's1', quantity: 0 }],
      trigger
    );
    // Only s1 valid (quantity coerced to >=1). Empty/null skipped.
    expect(trigger).toHaveBeenCalledTimes(1);
    expect(trigger.mock.calls[0][0]).toEqual({ skuId: 's1', quantity: 1 });
    expect(stats).toEqual({ ok: 1, failed: 2 });
  });

  it('non-function trigger — returns failed count without throw', async () => {
    const stats = await restoreCartItems([{ skuId: 'x', quantity: 1 }], null);
    expect(stats).toEqual({ ok: 0, failed: 1 });
  });

  it('serial execution — calls awaited in order (no parallel race)', async () => {
    const order = [];
    const trigger = vi.fn((arg) => ({
      unwrap: () =>
        new Promise((resolve) => {
          order.push(`enter:${arg.skuId}`);
          setTimeout(() => {
            order.push(`exit:${arg.skuId}`);
            resolve({});
          }, 5);
        }),
    }));
    await restoreCartItems(
      [
        { skuId: 'a', quantity: 1 },
        { skuId: 'b', quantity: 1 },
      ],
      trigger
    );
    expect(order).toEqual(['enter:a', 'exit:a', 'enter:b', 'exit:b']);
  });
});
