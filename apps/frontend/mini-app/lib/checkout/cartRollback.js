/**
 * Cart rollback helper (CHK-004).
 *
 * `prepareCart` checkout boshlanishida tanlanmagan SKU'larni cart'dan
 * o'chiradi (backend partial selection qo'llab-quvvatlamaydi — Spec §7.4).
 * Agar keyin `initiate` yoki `confirm` fail bo'lsa, foydalanuvchining
 * tovarlari yo'qotilmasligi kerak — `restoreCartItems` ularni qayta
 * `addCartItem` orqali tiklaydi.
 *
 * Pure helper — `useCheckoutFlow` hookini RTKQ mock'lar bilan to'liq
 * integratsion test qilish o'rniga, faqat shu funksiyani test qilamiz
 * (hook integratsiyasi manual QA bilan tasdiqlanadi).
 *
 * @typedef {{ skuId: string, quantity: number }} CartItemSnapshot
 *
 * @param {Array<CartItemSnapshot>} snapshot — `prepareCart` saqlagan ro'yxat
 * @param {(arg: { skuId: string, quantity: number }) => { unwrap: () => Promise<unknown> }} addCartItemTrigger
 *   RTKQ mutation trigger (yoki ekvivalent function). Har element uchun
 *   alohida chaqiriladi — serial, race oldini olish uchun.
 * @returns {Promise<{ ok: number, failed: number }>}  Statistika; UI uchun
 *   toast yoki diagnostika maqsadida foydalanish mumkin.
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
      // Backend rejection (price drift, OOS, va h.k.) — silent.
      // UI darajasidagi toast butun rollback uchun bitta marotaba
      // chaqiriladi (placeOrder ichida).
      failed += 1;
    }
  }
  return { ok, failed };
}
