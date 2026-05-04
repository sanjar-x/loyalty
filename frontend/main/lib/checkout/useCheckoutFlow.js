"use client";

import { useCallback, useEffect, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";

import {
  useGetMyCartQuery,
  useGetRateQuoteMutation,
  useInitiateCheckoutMutation,
  useConfirmCheckoutMutation,
  useCancelCheckoutMutation,
  useRemoveCartItemMutation,
} from "@/lib/store/api";
import {
  normalizeApiError,
  isQuoteExpiredError,
  isProviderRetryableError,
} from "@/lib/api/errors";
import { useCheckoutStore, CheckoutStatus } from "./store";

/**
 * useCheckoutFlow — Cart → checkout sahifasi navigatsiya va backend orchestrator.
 *
 * Mas'uliyat sohalari:
 *  1. **Selection sync** — `/trash`'dagi tanlangan SKU'lar checkout state'iga
 *  2. **Quote orqali narx** — pickup tanlangach `getRateQuote`'ni triggerlash
 *  3. **Initiate → Confirm pipeline** — pay button bosilganda atomik bajarish
 *  4. **Cancel on abandon** — sahifadan navigate qilinsa frozen cart'ni unfreeze
 *  5. **Expiry watchers** — quote (30 min) va attempt (15 min) TTL'ni kuzatish
 *
 * Pattern:
 *  ```jsx
 *  const flow = useCheckoutFlow();
 *  await flow.refreshQuote();        // pickup tanlangandan keyin
 *  await flow.placeOrder();          // pay button
 *  ```
 */
export function useCheckoutFlow() {
  const router = useRouter();
  const { data: cart } = useGetMyCartQuery();

  const status = useCheckoutStore((s) => s.status);
  const selectedSkuIds = useCheckoutStore((s) => s.selectedSkuIds);
  const pickup = useCheckoutStore((s) => s.pickup);
  const quote = useCheckoutStore((s) => s.quote);
  const attempt = useCheckoutStore((s) => s.attempt);
  const orderId = useCheckoutStore((s) => s.orderId);
  const error = useCheckoutStore((s) => s.error);

  const setSelection = useCheckoutStore((s) => s.setSelection);
  const setPickup = useCheckoutStore((s) => s.setPickup);
  const setQuote = useCheckoutStore((s) => s.setQuote);
  const clearQuote = useCheckoutStore((s) => s.clearQuote);
  const beginInitiate = useCheckoutStore((s) => s.beginInitiate);
  const setAttempt = useCheckoutStore((s) => s.setAttempt);
  const beginConfirm = useCheckoutStore((s) => s.beginConfirm);
  const setOrder = useCheckoutStore((s) => s.setOrder);
  const markCancelled = useCheckoutStore((s) => s.markCancelled);
  const setError = useCheckoutStore((s) => s.setError);
  const reset = useCheckoutStore((s) => s.reset);

  const [getRateQuote] = useGetRateQuoteMutation();
  const [initiateCheckout] = useInitiateCheckoutMutation();
  const [confirmCheckout] = useConfirmCheckoutMutation();
  const [cancelCheckout] = useCancelCheckoutMutation();
  const [removeCartItem] = useRemoveCartItemMutation();

  /* ── Selection helpers ── */

  // Cart'da hozir tanlangan elementlar (cross-reference selection ↔ cart)
  const selectedItems = useMemo(() => {
    const items = Array.isArray(cart?.items) ? cart.items : [];
    if (selectedSkuIds.length === 0) return items; // tanlov yo'q → hammasi
    const set = new Set(selectedSkuIds);
    return items.filter((it) => set.has(String(it.skuId)));
  }, [cart, selectedSkuIds]);

  /**
   * Backend `/cart/checkout` butun cart'ni freeze qiladi — partial selection
   * qo'llab-quvvatlanmaydi (Spec §7.4). Foydalanuvchi cart'dan ba'zi
   * elementlarni tanlamagan bo'lsa, ularni avval cart'dan o'chirishimiz kerak,
   * aks holda backend hammasini freeze qiladi va yakunda hammasi orderga
   * tushadi.
   *
   * Bu yerda `prepareCart` tanlanmagan elementlarni o'chirish bilan cart'ni
   * tanlovga moslashtiradi. Foydalanuvchi keyinroq qaytsa ularni qayta
   * qo'shishi kerak — bu trade-off backend cheklovi tufayli.
   */
  const prepareCart = useCallback(async () => {
    const allItems = Array.isArray(cart?.items) ? cart.items : [];
    if (allItems.length === 0) return false;
    if (selectedSkuIds.length === 0) return true; // tanlov yo'q → all-checkout
    const selectedSet = new Set(selectedSkuIds);
    const toRemove = allItems
      .map((it) => String(it.skuId))
      .filter((id) => !selectedSet.has(id));
    if (toRemove.length === 0) return true;
    // Bir vaqtning o'zida bir nechta o'chirish — RTKQ optimistic patch'lari
    // serial bajariladi, lekin parallel HTTP'lar OK.
    await Promise.all(
      toRemove.map((skuId) =>
        removeCartItem(skuId)
          .unwrap()
          .catch(() => null),
      ),
    );
    return true;
  }, [cart, selectedSkuIds, removeCartItem]);

  /* ── Quote pipeline ── */

  /**
   * Pickup-point tanlangandan keyin avtomatik chaqiriladi (yoki manual).
   * Spec §8.2: snake_case body, weight/origin/destination — server-trusted.
   */
  const refreshQuote = useCallback(async () => {
    if (!pickup?.externalId || !pickup?.providerCode) {
      setError({ code: "PICKUP_REQUIRED", message: "Выберите пункт выдачи" });
      return null;
    }
    const itemsForQuote = selectedItems
      .map((it) => ({
        skuId: String(it.skuId),
        quantity: Math.max(1, Math.floor(Number(it.quantity || 1))),
      }))
      .filter((x) => x.skuId);
    if (itemsForQuote.length === 0) {
      setError({ code: "EMPTY_CART", message: "Корзина пуста" });
      return null;
    }
    try {
      const resp = await getRateQuote({
        items: itemsForQuote,
        providerCode: pickup.providerCode,
        pickupPointExternalId: pickup.externalId,
      }).unwrap();
      const next = {
        quoteId: resp.quote_id,
        providerCode: resp.provider_code,
        serviceCode: resp.service_code,
        serviceName: resp.service_name,
        deliveryType: resp.delivery_type,
        deliveryAmount: resp.delivery_amount?.amount ?? 0, // kopecks
        currency: resp.delivery_amount?.currency || "RUB",
        deliveryDaysMin: resp.delivery_days_min ?? null,
        deliveryDaysMax: resp.delivery_days_max ?? null,
        expiresAt: resp.expires_at, // ISO, 30 min TTL
      };
      setQuote(next);
      return next;
    } catch (err) {
      const norm = normalizeApiError(err);
      if (isQuoteExpiredError(err)) {
        clearQuote();
        setError({ code: "QUOTE_EXPIRED", message: "Срок котировки истёк" });
      } else if (isProviderRetryableError(err)) {
        setError({
          code: norm.code || "PROVIDER_ERROR",
          message: "Сервис доставки временно недоступен — выберите другой ПВЗ",
        });
      } else {
        setError({
          code: norm.code,
          message: norm.message || "Не удалось рассчитать доставку",
        });
      }
      return null;
    }
  }, [pickup, selectedItems, getRateQuote, setQuote, clearQuote, setError]);

  // Pickup yangilansa avtomatik quote (idempotent — cache hit'da qayta
  // jo'natmaydi, lekin RTKQ mutation har safar yangi quote ID beradi). Bu
  // sodda implementatsiya; production'da debounce qo'shish mumkin.
  useEffect(() => {
    if (status !== CheckoutStatus.QUOTING) return;
    refreshQuote();
    // refreshQuote o'zi `setQuote → READY` yoki error qaytaradi
  }, [status, refreshQuote]);

  /* ── Place order (initiate → confirm pipeline) ── */

  /**
   * Atomik buyurtma berish:
   *  1. prepareCart (partial selection bo'lsa unselect'larni o'chirish)
   *  2. /cart/checkout {pickupPointId} → attemptId
   *  3. (kelajakda payment integration shu yerga keladi)
   *  4. /cart/checkout/confirm {attemptId} → orderId
   *  5. router.push success
   *
   * Xato yo'lda /cart/checkout/cancel chaqirilmaydi — backend snapshot
   * 15 min TTL bilan o'z-o'zidan tugaydi va cart unfreeze bo'ladi.
   */
  const placeOrder = useCallback(async () => {
    if (!pickup?.externalId) {
      setError({ code: "PICKUP_REQUIRED", message: "Выберите пункт выдачи" });
      return null;
    }
    // Optional: selection prep
    const ready = await prepareCart();
    if (!ready) {
      setError({ code: "EMPTY_CART", message: "Корзина пуста" });
      return null;
    }

    beginInitiate();
    let attemptResp;
    try {
      attemptResp = await initiateCheckout({
        pickupPointId: pickup.externalId,
      }).unwrap();
    } catch (err) {
      const norm = normalizeApiError(err);
      setError({
        code: norm.code,
        message: norm.message || "Не удалось начать оформление",
      });
      return null;
    }

    setAttempt({
      attemptId: attemptResp.attemptId,
      snapshotId: attemptResp.snapshotId,
      expiresAt: attemptResp.expiresAt,
    });

    // (Hozir payment moduli yo'q — to'g'ridan-to'g'ri confirm)
    beginConfirm();
    try {
      const confirmResp = await confirmCheckout({
        attemptId: attemptResp.attemptId,
      }).unwrap();
      const newOrderId = confirmResp?.orderId ?? null;
      setOrder(newOrderId);
      return newOrderId;
    } catch (err) {
      const norm = normalizeApiError(err);
      setError({
        code: norm.code,
        message: norm.message || "Не удалось подтвердить заказ",
      });
      // Confirm fail — cart `frozen` qoladi. Backend TTL avtomatik unfreeze
      // qiladi 15 min ichida. Foydalanuvchi qayta urinib ko'rishi mumkin.
      return null;
    }
  }, [
    pickup,
    prepareCart,
    initiateCheckout,
    confirmCheckout,
    beginInitiate,
    setAttempt,
    beginConfirm,
    setOrder,
    setError,
  ]);

  /**
   * User checkout sahifasidan qaytsa — frozen cart'ni unfreeze qilish.
   * Best-effort: fail bo'lsa silent (backend TTL barcha hollarda kafolat).
   */
  const abandon = useCallback(async () => {
    if (status === CheckoutStatus.FROZEN || status === CheckoutStatus.CONFIRMING) {
      try {
        await cancelCheckout().unwrap();
      } catch {
        // ignore — backend TTL bor
      }
    }
    markCancelled();
  }, [status, cancelCheckout, markCancelled]);

  /* ── Expiry watchers ── */

  // Quote 30 min TTL: tugashidan 1 daqiqa oldin avtomatik qayta so'rash
  const quoteRefreshTimerRef = useRef(null);
  useEffect(() => {
    clearTimeout(quoteRefreshTimerRef.current);
    if (!quote?.expiresAt || status !== CheckoutStatus.READY) return;
    const expireMs = new Date(quote.expiresAt).getTime();
    if (!Number.isFinite(expireMs)) return;
    const refreshAt = expireMs - 60_000; // 1 min before expiry
    const delay = refreshAt - Date.now();
    if (delay <= 0) {
      refreshQuote();
      return;
    }
    quoteRefreshTimerRef.current = setTimeout(refreshQuote, delay);
    return () => clearTimeout(quoteRefreshTimerRef.current);
  }, [quote?.expiresAt, status, refreshQuote]);

  // Attempt 15 min TTL: tugashidan keyin status'ni IDLE ga qaytarish
  const attemptExpireTimerRef = useRef(null);
  useEffect(() => {
    clearTimeout(attemptExpireTimerRef.current);
    if (!attempt?.expiresAt || status !== CheckoutStatus.FROZEN) return;
    const expireMs = new Date(attempt.expiresAt).getTime();
    if (!Number.isFinite(expireMs)) return;
    const delay = Math.max(0, expireMs - Date.now());
    attemptExpireTimerRef.current = setTimeout(() => {
      markCancelled();
      setError({
        code: "ATTEMPT_EXPIRED",
        message: "Срок оформления истёк, начните заново",
      });
    }, delay);
    return () => clearTimeout(attemptExpireTimerRef.current);
  }, [attempt?.expiresAt, status, markCancelled, setError]);

  /* ── Navigatsiya yordamchilari ── */

  /**
   * `/trash`'dan chaqiriladi: SKU tanlovni saqlaydi va `/checkout`'ga
   * o'tkazadi. Pickup `searchParams`'ga emas, store'ga yoziladi.
   */
  const goToCheckout = useCallback(
    (skuIds) => {
      if (Array.isArray(skuIds) && skuIds.length === 0) return;
      setSelection(skuIds || []);
      router.push("/checkout");
    },
    [setSelection, router],
  );

  /**
   * Buyurtma muvaffaqiyatli yakunlangach — success ekranga.
   * Hozir orderId Orders modulida yo'q (Spec §11), shuning uchun
   * `/trash` ga toast bilan qaytaramiz va store'ni reset qilamiz.
   */
  const onConfirmed = useCallback(() => {
    const finalOrderId = orderId;
    reset();
    if (finalOrderId) {
      router.push(`/profile/orders?new=${encodeURIComponent(finalOrderId)}`);
    } else {
      router.push("/profile/orders");
    }
  }, [orderId, reset, router]);

  /* ── Helpers ── */

  const isPickupSelected = Boolean(pickup?.externalId && pickup?.providerCode);
  // Quote validity'ni `useMemo` ichida hisoblamaymiz — `Date.now()` impure,
  // lekin uning natijasi har bir render'da yangilanadi (foydalanuvchi formani
  // to'ldirishi 30 daqiqadan kam vaqt). 1 daqiqa oldin auto-refresh effect
  // eski quote'ni yangilaydi. Render-time check shunchaki UI gating uchun.
  const quoteExpiresAtMs = quote?.expiresAt
    ? new Date(quote.expiresAt).getTime()
    : 0;
  const isQuoteValid =
    Boolean(quote) && Number.isFinite(quoteExpiresAtMs) && quoteExpiresAtMs > 0;
  const canPlaceOrder =
    isPickupSelected &&
    isQuoteValid &&
    status === CheckoutStatus.READY &&
    selectedItems.length > 0;

  return {
    // state
    status,
    selectedSkuIds,    // canonical selection (UI'da useCart bilan filter qilish uchun)
    selectedItems,     // backend cart shape (raw CartItemResponse) — quote/initiate uchun
    pickup,
    quote,
    attempt,
    orderId,
    error,
    canPlaceOrder,
    isPickupSelected,
    isQuoteValid,
    // actions
    setSelection,
    setPickup,
    refreshQuote,
    placeOrder,
    abandon,
    goToCheckout,
    onConfirmed,
    reset,
  };
}
