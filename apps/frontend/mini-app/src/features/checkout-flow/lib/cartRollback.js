/**
 * Cart rollback helper (CHK-004).
 *
 * At checkout start `prepareCart` removes unselected SKUs from the cart
 * (backend doesn't support partial selection — Spec §7.4). If later
 * `initiate` or `confirm` fails, the user's items must not be lost —
 * `restoreCartItems` restores them via `addCartItem`.
 *
 * Pure helper — instead of fully integration-testing the `useCheckoutFlow`
 * hook with RTKQ mocks, we only test this function (hook integration is
 * confirmed via manual QA).
 *
 * @typedef {{ skuId: string, quantity: number }} CartItemSnapshot
 *
 * @param {Array<CartItemSnapshot>} snapshot — list stored by `prepareCart`
 * @param {(arg: { skuId: string, quantity: number }) => { unwrap: () => Promise<unknown> }} addCartItemTrigger
 *   RTKQ mutation trigger (or equivalent function). Called separately for
 *   each element — serial, to prevent races.
 * @returns {Promise<{ ok: number, failed: number }>}  Stats; usable by the
 *   UI for toast or diagnostics.
 */
export async function restoreCartItems(snapshot, addCartItemTrigger) {
  if (!Array.isArray(snapshot) || snapshot.length === 0) {
    return { ok: 0, failed: 0 };
  }
  if (typeof addCartItemTrigger !== 'function') {
    return { ok: 0, failed: snapshot.length };
  }
  let ok = 0;
  let failed = 0;
  for (const item of snapshot) {
    if (!item || !item.skuId) {
      failed += 1;
      continue;
    }
    const quantity = Math.max(1, Math.floor(Number(item.quantity) || 1));
    try {
      await addCartItemTrigger({ skuId: item.skuId, quantity }).unwrap();
      ok += 1;
    } catch {
      // Backend rejection (price drift, OOS, etc.) — silent.
      // The UI-level toast for the whole rollback is invoked once
      // (inside placeOrder).
      failed += 1;
    }
  }
  return { ok, failed };
}
