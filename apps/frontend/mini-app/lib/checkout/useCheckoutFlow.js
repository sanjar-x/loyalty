'use client';

import { useCallback, useEffect, useMemo, useRef } from 'react';
import { useRouter } from 'next/navigation';

import {
  useGetMyCartQuery,
  useGetRateQuoteMutation,
  useInitiateCheckoutMutation,
  useConfirmCheckoutMutation,
  useCancelCheckoutMutation,
  useRemoveCartItemMutation,
  useAddCartItemMutation,
  useCreateRecipientMutation,
} from '@/lib/store/api';
import { toast } from '@/lib/ui/toast';
import { normalizeApiError, isQuoteExpiredError, isProviderRetryableError } from '@/lib/api/errors';
import { useCheckoutStore, CheckoutStatus } from './store';
import { parseRuDate } from './dateFormat';
import { PHONE_FORMATS } from './validators';
import { restoreCartItems } from './cartRollback';
import { pickProviderErrorMessage } from './quoteErrorMessage';
import { acquireInflight, releaseInflight, ensureKey, resetKey } from './idempotency';
import { clearPendingIdempotencyKey, INITIATE_CHECKOUT_URL } from '@/lib/store/api';

// Cyrillic → Latin minimal transliteratsiya (GOST 7.79 system B sodda variant).
// Backend `fullNameLat` shipper hujjatlariga yozadi (e.g. CDEK customs declaration).
// UI'da alohida lotincha maydon qo'shilguncha bu yetarli — backend o'zi
// qaytadan normalize qilishi mumkin.
const RU_TO_LAT_MAP = {
  а: 'a',
  б: 'b',
  в: 'v',
  г: 'g',
  д: 'd',
  е: 'e',
  ё: 'e',
  ж: 'zh',
  з: 'z',
  и: 'i',
  й: 'i',
  к: 'k',
  л: 'l',
  м: 'm',
  н: 'n',
  о: 'o',
  п: 'p',
  р: 'r',
  с: 's',
  т: 't',
  у: 'u',
  ф: 'f',
  х: 'kh',
  ц: 'ts',
  ч: 'ch',
  ш: 'sh',
  щ: 'shch',
  ъ: '',
  ы: 'y',
  ь: '',
  э: 'e',
  ю: 'iu',
  я: 'ia',
};

function transliterateRuToLat(input) {
  if (typeof input !== 'string') return '';
  let out = '';
  for (const ch of input) {
    const lower = ch.toLowerCase();
    const mapped = RU_TO_LAT_MAP[lower];
    if (mapped == null) {
      // Latincha, raqam, tinish belgilari, bo'shliq — o'zicha
      out += ch;
      continue;
    }
    out += ch === lower ? mapped : mapped.charAt(0).toUpperCase() + mapped.slice(1);
  }
  return out;
}

/**
 * useCheckoutFlow — Cart → checkout sahifasi navigatsiya va backend orchestrator.
 *
 * Mas'uliyat sohalari:
 *  1. **Selection sync** — `/cart`'dagi tanlangan SKU'lar checkout state'iga
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
  const recipient = useCheckoutStore((s) => s.recipient);
  const customs = useCheckoutStore((s) => s.customs);
  const selectedRecipientId = useCheckoutStore((s) => s.selectedRecipientId);

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
  const setSelectedRecipientId = useCheckoutStore((s) => s.setSelectedRecipientId);
  const setRemovedSnapshot = useCheckoutStore((s) => s.setRemovedSnapshot);
  const clearRemovedSnapshot = useCheckoutStore((s) => s.clearRemovedSnapshot);
  const reset = useCheckoutStore((s) => s.reset);

  const [getRateQuote] = useGetRateQuoteMutation();
  const [initiateCheckout] = useInitiateCheckoutMutation();
  const [confirmCheckout] = useConfirmCheckoutMutation();
  const [cancelCheckout] = useCancelCheckoutMutation();
  const [removeCartItem] = useRemoveCartItemMutation();
  const [addCartItem] = useAddCartItemMutation();
  const [createRecipient] = useCreateRecipientMutation();

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
    const toRemove = allItems.filter((it) => !selectedSet.has(String(it.skuId)));
    if (toRemove.length === 0) return true;
    // CHK-004: rollback uchun snapshot — initiate/confirm fail bo'lsa
    // restoreRemoved bu rekordlardan addCartItem chaqiradi.
    setRemovedSnapshot(toRemove);
    // Bir vaqtning o'zida bir nechta o'chirish — RTKQ optimistic patch'lari
    // serial bajariladi, lekin parallel HTTP'lar OK.
    await Promise.all(
      toRemove.map((it) =>
        removeCartItem(it.skuId)
          .unwrap()
          .catch(() => null)
      )
    );
    return true;
  }, [cart, selectedSkuIds, removeCartItem, setRemovedSnapshot]);

  /**
   * Initiate/confirm fail bo'lganda `prepareCart` snapshot'idagi tovarlarni
   * cart'ga qaytaradi. Serial — bir vaqtning o'zida ko'p addCartItem
   * yuborilsa backend rate-limit yoki order ichidagi quantity drift'ga
   * sabab bo'lishi mumkin (best-effort, har bir alohida fail bo'lishi
   * silently saqlanadi).
   *
   * Tugagach `clearRemovedSnapshot()` chaqiriladi — keyingi attempt
   * uchun toza stol.
   */
  const restoreRemoved = useCallback(async () => {
    const snap = useCheckoutStore.getState().removedItemsSnapshot;
    await restoreCartItems(snap, addCartItem);
    clearRemovedSnapshot();
  }, [addCartItem, clearRemovedSnapshot]);

  /* ── Quote pipeline ── */

  /**
   * Pickup-point tanlangandan keyin avtomatik chaqiriladi (yoki manual).
   * Spec §8.2: snake_case body, weight/origin/destination — server-trusted.
   */
  const refreshQuote = useCallback(async () => {
    if (!pickup?.externalId || !pickup?.providerCode) {
      setError({ code: 'PICKUP_REQUIRED', message: 'Выберите пункт выдачи' });
      return null;
    }
    // CHK-018 Layer A: cart RTKQ hali javob bermagan bo'lsa skip qilamiz
    // — selectedItems bo'sh ko'rinishi mumkin, "Корзина пуста" false-positive
    // toast'iga olib keladi. Cart yuklangach `useCallback` deps yangilanadi
    // (`cart` ref o'zgaradi) → QUOTING effect refreshQuote'ni qayta chaqiradi.
    if (cart === undefined) return null;
    const itemsForQuote = selectedItems
      .map((it) => ({
        skuId: String(it.skuId),
        quantity: Math.max(1, Math.floor(Number(it.quantity || 1))),
      }))
      .filter((x) => x.skuId);
    if (itemsForQuote.length === 0) {
      setError({ code: 'EMPTY_CART', message: 'Корзина пуста' });
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
        currency: resp.delivery_amount?.currency || 'RUB',
        deliveryDaysMin: resp.delivery_days_min ?? null,
        deliveryDaysMax: resp.delivery_days_max ?? null,
        expiresAt: resp.expires_at, // ISO, 30 min TTL
      };
      setQuote(next);
      return next;
    } catch (err) {
      const norm = normalizeApiError(err);
      // CHK-017: har quote error'da clearQuote chaqirish — status
      // SELECTING_PICKUP'ga qaytadi, UI "Рассчитывается…" qotib qolmaydi.
      // Foydalanuvchi pickup tile'ni qayta bosib boshqa PVZ tanlay oladi.
      clearQuote();
      if (isQuoteExpiredError(err)) {
        setError({ code: 'QUOTE_EXPIRED', message: 'Срок котировки истёк' });
      } else if (isProviderRetryableError(err)) {
        // Backend ba'zan "Provider 'X' has no default_origin configured"
        // technical detail qaytaradi — pickProviderErrorMessage user-friendly
        // matnga aylantiradi (to'liq i18n alohida ticketda).
        setError({
          code: norm.code || 'PROVIDER_ERROR',
          message: pickProviderErrorMessage(norm.message),
        });
      } else {
        setError({
          code: norm.code,
          message: norm.message || 'Не удалось рассчитать доставку',
        });
      }
      return null;
    }
  }, [pickup, selectedItems, cart, getRateQuote, setQuote, clearQuote, setError]);

  // Pickup yangilansa avtomatik quote (idempotent — cache hit'da qayta
  // jo'natmaydi, lekin RTKQ mutation har safar yangi quote ID beradi). Bu
  // sodda implementatsiya; production'da debounce qo'shish mumkin.
  useEffect(() => {
    if (status !== CheckoutStatus.QUOTING) return;
    refreshQuote();
    // refreshQuote o'zi `setQuote → READY` yoki error qaytaradi
  }, [status, refreshQuote]);

  /* ── Recipient resource resolution ── */

  /**
   * Recipient resource'ni tayyorlaydi:
   *  • `selectedRecipientId` allaqachon mavjud bo'lsa — qaytaradi
   *  • Aks holda `POST /api/v1/recipients` chaqirib yangi resurs yaratadi
   *
   * Backend `CreateRecipientRequest` ham UI form ham, ham customs ham to'liq
   * to'lib bo'lishini talab qiladi. UI ushbu maydonlarni ikkita formada
   * yig'adi (recipient sheet + customs sheet) — bu yerda store'dan to'plab
   * tekshiramiz.
   *
   * Latincha ism `fullNameLat` — UI hozircha kiriladigan to'liq F.I.Sh. dan
   * naive transliteratsiya qiladi. Ideal holda foydalanuvchi alohida maydonda
   * lotinchada kiritsin (TODO P1.UI).
   */
  const ensureRecipient = useCallback(async () => {
    if (selectedRecipientId) return selectedRecipientId;

    if (!recipient || !customs) {
      setError({
        code: 'RECIPIENT_REQUIRED',
        message: 'Заполните данные получателя и таможенные реквизиты',
      });
      return null;
    }

    const fullNameRu = String(recipient.fullName || '').trim();
    const phoneRaw = String(recipient.phoneDigits || '').replace(/\D/g, '');
    const country = recipient.country || 'RU';
    const phoneFormat = PHONE_FORMATS[country] || PHONE_FORMATS.RU;
    const email = String(recipient.email || '').trim();
    const passportSerial = String(customs.passportSeries || '').replace(/\D/g, '');
    const passportNumber = String(customs.passportNumber || '').replace(/\D/g, '');
    // UI sanalarni `DD.MM.YYYY` shaklida saqlaydi (CHK-001) — backend ISO kutadi.
    const passportIssueDate = parseRuDate(customs.issueDate);
    const birthDate = parseRuDate(customs.birthDate);
    const inn = String(customs.inn || '').replace(/\D/g, '');

    if (
      !fullNameRu ||
      phoneRaw.length !== phoneFormat.lenAfter ||
      !email ||
      passportSerial.length !== 4 ||
      passportNumber.length !== 6 ||
      !passportIssueDate ||
      !birthDate ||
      inn.length !== 12
    ) {
      setError({
        code: 'RECIPIENT_INVALID',
        message: 'Заполните все поля получателя и паспортные данные',
      });
      return null;
    }

    // Ruscha → lotincha minimal transliteratsiya. Backend `fullNameLat` ni
    // shipper hujjatlariga yozadi; UI'da alohida lotincha maydon qo'shilguncha
    // shu fallback yetarli (yana backend o'zi normalize qilishi mumkin).
    const fullNameLat = transliterateRuToLat(fullNameRu);

    try {
      const resp = await createRecipient({
        fullNameRu,
        fullNameLat,
        phone: `${phoneFormat.prefix}${phoneRaw}`,
        email,
        passportSerial,
        passportNumber,
        passportIssueDate,
        birthDate,
        inn,
      }).unwrap();
      const id = resp?.recipientId;
      if (!id) {
        setError({
          code: 'RECIPIENT_CREATE_FAILED',
          message: 'Не удалось сохранить данные получателя',
        });
        return null;
      }
      setSelectedRecipientId(id);
      return id;
    } catch (err) {
      const norm = normalizeApiError(err);
      setError({
        code: norm.code || 'RECIPIENT_CREATE_FAILED',
        message: norm.message || 'Не удалось сохранить данные получателя',
      });
      return null;
    }
  }, [recipient, customs, selectedRecipientId, createRecipient, setSelectedRecipientId, setError]);

  /* ── Place order (initiate → confirm pipeline) ── */

  /**
   * Atomik buyurtma berish:
   *  1. prepareCart (partial selection bo'lsa unselect'larni o'chirish)
   *  2. ensureRecipient — yo'q bo'lsa POST /recipients
   *  3. /cart/checkout {pickupPointId, pickupCarrier, recipientId} → attemptId
   *  4. /cart/checkout/confirm {attemptId} → orderId (yangi schema'da nullable)
   *  5. (P1: agar orderId yo'q bo'lsa — POST /orders {cartId, snapshotId, idempotencyKey})
   *  6. router.push success
   *
   * Xato yo'lda /cart/checkout/cancel chaqirilmaydi — backend snapshot
   * 15 min TTL bilan o'z-o'zidan tugaydi va cart unfreeze bo'ladi.
   */
  // CHK-006: Pay double-tap'ga qarshi himoya. `inflightRef` parallel
  // chaqiruvni silent rad qiladi; `idempotencyKeyRef` retry'da bir xil
  // header beradi va success'da reset bo'ladi (yangi attempt yangi key).
  const inflightRef = useRef(false);
  const idempotencyKeyRef = useRef(null);

  const placeOrder = useCallback(async () => {
    if (!pickup?.externalId || !pickup?.providerCode) {
      setError({ code: 'PICKUP_REQUIRED', message: 'Выберите пункт выдачи' });
      return null;
    }

    if (!acquireInflight(inflightRef)) return null;

    try {
      const ready = await prepareCart();
      if (!ready) {
        setError({ code: 'EMPTY_CART', message: 'Корзина пуста' });
        return null;
      }

      const recipientId = await ensureRecipient();
      if (!recipientId) {
        // ensureRecipient already set the error
        return null;
      }

      const idempotencyKey = ensureKey(idempotencyKeyRef);

      beginInitiate();
      let attemptResp;
      try {
        attemptResp = await initiateCheckout({
          pickupPointId: pickup.externalId,
          pickupCarrier: pickup.providerCode,
          recipientId,
          __idempotencyKey: idempotencyKey,
        }).unwrap();
      } catch (err) {
        const norm = normalizeApiError(err);
        setError({
          code: norm.code,
          message: norm.message || 'Не удалось начать оформление',
        });
        // CHK-004: tanlanmagan tovarlar prepareCart'da o'chirilgan edi —
        // initiate fail bo'ldi, cart'ga qaytarish kerak.
        const snapBefore = useCheckoutStore.getState().removedItemsSnapshot?.length || 0;
        await restoreRemoved();
        if (snapBefore > 0) {
          toast.info('Не удалось оформить заказ. Товары возвращены в корзину.');
        }
        return null;
      }

      setAttempt({
        attemptId: attemptResp.attemptId,
        snapshotId: attemptResp.snapshotId,
        expiresAt: attemptResp.expiresAt,
      });

      beginConfirm();
      try {
        const confirmResp = await confirmCheckout({
          attemptId: attemptResp.attemptId,
        }).unwrap();
        const newOrderId = confirmResp?.orderId ?? null;
        setOrder(newOrderId);
        // CHK-004: muvaffaqiyatli buyurtma — snapshot endi kerak emas
        // (tanlanmagan tovarlar orderga tushmadi, lekin foydalanuvchining
        // o'zi tashlab ketdi).
        clearRemovedSnapshot();
        // CHK-006: yangi attempt yangi key olishi uchun reset.
        resetKey(idempotencyKeyRef);
        clearPendingIdempotencyKey(INITIATE_CHECKOUT_URL);
        return newOrderId;
      } catch (err) {
        const norm = normalizeApiError(err);
        setError({
          code: norm.code,
          message: norm.message || 'Не удалось подтвердить заказ',
        });
        const snapBefore = useCheckoutStore.getState().removedItemsSnapshot?.length || 0;
        await restoreRemoved();
        if (snapBefore > 0) {
          toast.info('Не удалось оформить заказ. Товары возвращены в корзину.');
        }
        return null;
      }
    } finally {
      releaseInflight(inflightRef);
    }
  }, [
    pickup,
    prepareCart,
    ensureRecipient,
    initiateCheckout,
    confirmCheckout,
    beginInitiate,
    setAttempt,
    beginConfirm,
    setOrder,
    setError,
    restoreRemoved,
    clearRemovedSnapshot,
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
        code: 'ATTEMPT_EXPIRED',
        message: 'Срок оформления истёк, начните заново',
      });
    }, delay);
    return () => clearTimeout(attemptExpireTimerRef.current);
  }, [attempt?.expiresAt, status, markCancelled, setError]);

  /* ── Navigatsiya yordamchilari ── */

  /**
   * `/cart`'dan chaqiriladi: SKU tanlovni saqlaydi va `/checkout`'ga
   * o'tkazadi. Pickup `searchParams`'ga emas, store'ga yoziladi.
   */
  const goToCheckout = useCallback(
    (skuIds) => {
      if (Array.isArray(skuIds) && skuIds.length === 0) return;
      setSelection(skuIds || []);
      router.push('/checkout');
    },
    [setSelection, router]
  );

  /**
   * Buyurtma muvaffaqiyatli yakunlangach — success ekranga.
   * Hozir orderId Orders modulida yo'q (Spec §11), shuning uchun
   * `/cart` ga toast bilan qaytaramiz va store'ni reset qilamiz.
   */
  const onConfirmed = useCallback(() => {
    const finalOrderId = orderId;
    reset();
    if (finalOrderId) {
      router.push(`/profile/orders?new=${encodeURIComponent(finalOrderId)}`);
    } else {
      router.push('/profile/orders');
    }
  }, [orderId, reset, router]);

  /* ── Helpers ── */

  const isPickupSelected = Boolean(pickup?.externalId && pickup?.providerCode);
  // Quote validity'ni `useMemo` ichida hisoblamaymiz — `Date.now()` impure,
  // lekin uning natijasi har bir render'da yangilanadi (foydalanuvchi formani
  // to'ldirishi 30 daqiqadan kam vaqt). 1 daqiqa oldin auto-refresh effect
  // eski quote'ni yangilaydi. Render-time check shunchaki UI gating uchun.
  const quoteExpiresAtMs = quote?.expiresAt ? new Date(quote.expiresAt).getTime() : 0;
  const isQuoteValid = Boolean(quote) && Number.isFinite(quoteExpiresAtMs) && quoteExpiresAtMs > 0;
  const canPlaceOrder =
    isPickupSelected && isQuoteValid && status === CheckoutStatus.READY && selectedItems.length > 0;

  // CHK-015: stable return reference. Eski versiyada har render'da
  // yangi object literal qaytarilardi — agar iste'molchi `flow`'ni
  // useEffect dep'ida ishlatsa, infinite loop. Zustand action'lari
  // o'z-o'zidan stable, state primitive yoki o'zgarganda yangi;
  // shu sababli useMemo deps massivi ishonchli.
  return useMemo(
    () => ({
      // state
      status,
      selectedSkuIds,
      selectedItems,
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
    }),
    [
      status,
      selectedSkuIds,
      selectedItems,
      pickup,
      quote,
      attempt,
      orderId,
      error,
      canPlaceOrder,
      isPickupSelected,
      isQuoteValid,
      setSelection,
      setPickup,
      refreshQuote,
      placeOrder,
      abandon,
      goToCheckout,
      onConfirmed,
      reset,
    ]
  );
}
