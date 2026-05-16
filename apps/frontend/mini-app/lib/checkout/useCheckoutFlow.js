'use client';

import { useCallback, useEffect, useMemo, useRef } from 'react';
import { useRouter } from 'next/navigation';

import {
  useGetMyCartQuery,
  useGetRateQuoteMutation,
  useInitiateCheckoutMutation,
  useCreateOrderMutation,
  useCancelCheckoutMutation,
  useRemoveCartItemMutation,
  useAddCartItemMutation,
  useCreateRecipientMutation,
} from '@/lib/store/api';
import { toast } from '@/lib/ui/toast';
import {
  normalizeApiError,
  isQuoteExpiredError,
  isProviderRetryableError,
  isCurrencyMismatchError,
} from '@/lib/api/errors';
import { useCheckoutStore, CheckoutStatus } from './store';
import { parseRuDate } from './dateFormat';
import { PHONE_FORMATS } from './validators';
import { restoreCartItems } from './cartRollback';
import { pickProviderErrorMessage } from './quoteErrorMessage';
import { mapRateQuoteResponseToQuote } from './quoteMapper';
import { acquireInflight, releaseInflight, ensureKey, resetKey } from './idempotency';
import {
  clearPendingIdempotencyKey,
  INITIATE_CHECKOUT_URL,
  CREATE_ORDER_URL,
} from '@/lib/store/api';

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
  const setPayment = useCheckoutStore((s) => s.setPayment);
  const markCancelled = useCheckoutStore((s) => s.markCancelled);
  const setError = useCheckoutStore((s) => s.setError);
  const setSelectedRecipientId = useCheckoutStore((s) => s.setSelectedRecipientId);
  const setRemovedSnapshot = useCheckoutStore((s) => s.setRemovedSnapshot);
  const clearRemovedSnapshot = useCheckoutStore((s) => s.clearRemovedSnapshot);
  const reset = useCheckoutStore((s) => s.reset);

  const [getRateQuote] = useGetRateQuoteMutation();
  const [initiateCheckout] = useInitiateCheckoutMutation();
  const [createOrder] = useCreateOrderMutation();
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

  // CHK-024 latest-wins: oldingi inflight quote so'rovini bekor qiladi
  // (foydalanuvchi PVZ'ni tezda almashtirsa, faqat oxirgi javob saqlanadi).
  // RTKQ mutation trigger qaytargan object'da `.abort()` mavjud.
  const inflightQuoteRef = useRef(null);

  /**
   * Pickup-point tanlangandan keyin avtomatik chaqiriladi (yoki manual).
   * Spec §8.2: weight/origin/destination — server-trusted.
   *
   * `overrides.serviceCode` — fallbackAlternatives tarif tanlash uchun
   * (toggle); null/undefined bo'lsa provider eng arzon tarifni qaytaradi.
   */
  const refreshQuote = useCallback(
    async (overrides = {}) => {
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
      // Tarif tanlovi (fallbackAlternatives): explicit `overrides.serviceCode`
      // ustun; aks holda auto-refresh joriy `quote.serviceCode`'ni saqlaydi.
      const serviceCode =
        typeof overrides?.serviceCode === 'string' && overrides.serviceCode
          ? overrides.serviceCode
          : (quote?.serviceCode ?? null);
      // Oldingi inflight'ni bekor qilamiz — RTKQ `AbortError` qaytaradi,
      // pastdagi catch uni `name === 'AbortError'` orqali ignore qiladi
      // (`clearQuote` chaqirilmaydi, status QUOTING saqlanadi keyingi
      // refreshQuote tezda kelishini kutib).
      if (inflightQuoteRef.current?.abort) {
        try {
          inflightQuoteRef.current.abort();
        } catch {
          // ignore
        }
      }
      const pendingPromise = getRateQuote({
        items: itemsForQuote,
        providerCode: pickup.providerCode,
        pickupPointExternalId: pickup.externalId,
        serviceCode: serviceCode ?? null,
      });
      inflightQuoteRef.current = pendingPromise;
      try {
        const resp = await pendingPromise.unwrap();
        // REFACT-001: wire shape camelCase. Mapping qatlami `quoteMapper`'da —
        // pure helper, alohida unit-test bilan qoplangan.
        const next = mapRateQuoteResponseToQuote(resp);
        if (!next) {
          setError({ code: 'INVALID_QUOTE_RESPONSE', message: 'Не удалось рассчитать доставку' });
          clearQuote();
          return null;
        }
        setQuote(next);
        return next;
      } catch (err) {
        // Latest-wins abort: keyingi refreshQuote allaqachon yo'lda — UI
        // QUOTING'da qoladi, hech qanday error/clearQuote chaqirilmaydi.
        if (err?.name === 'AbortError' || err?.error?.name === 'AbortError') {
          return null;
        }
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
      } finally {
        if (inflightQuoteRef.current === pendingPromise) {
          inflightQuoteRef.current = null;
        }
      }
    },
    [pickup, selectedItems, cart, quote, getRateQuote, setQuote, clearQuote, setError]
  );

  // LATEST callback in ref — placeOrder retry va auto-refresh timer
  // stale closure'siz chaqirish uchun.
  const refreshQuoteRef = useRef(refreshQuote);
  useEffect(() => {
    refreshQuoteRef.current = refreshQuote;
  }, [refreshQuote]);

  // Pickup yangilansa avtomatik quote (idempotent — cache hit'da qayta
  // jo'natmaydi, lekin RTKQ mutation har safar yangi quote ID beradi). Bu
  // sodda implementatsiya; production'da debounce qo'shish mumkin.
  useEffect(() => {
    if (status !== CheckoutStatus.QUOTING) return;
    refreshQuote();
    // refreshQuote o'zi `setQuote → READY` yoki error qaytaradi
  }, [status, refreshQuote]);

  // Cart tarkibi/miqdori o'zgarsa — quote stale (backend SKU vazni
  // bo'yicha hisoblaydi). READY holatda turgan pickup uchun avto re-quote.
  // Boshlang'ich render'da skip — `lastCartHashRef` birinchi qiymatni
  // saqlaydi va keyingi haqiqiy o'zgarishlarga reaksiya bildiradi.
  const cartHash = useMemo(
    () =>
      selectedItems
        .map((it) => `${it?.skuId ?? ''}:${Math.max(1, Math.floor(Number(it?.quantity || 1)))}`)
        .join(','),
    [selectedItems]
  );
  const lastCartHashRef = useRef(cartHash);
  useEffect(() => {
    if (lastCartHashRef.current === cartHash) return;
    lastCartHashRef.current = cartHash;
    if (status === CheckoutStatus.READY && pickup?.externalId) {
      refreshQuoteRef.current?.();
    }
  }, [cartHash, status, pickup?.externalId]);

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
   * Atomik buyurtma berish (CHK-024 — POST /orders bilan):
   *  1. prepareCart (partial selection bo'lsa unselect'larni o'chirish)
   *  2. ensureRecipient — yo'q bo'lsa POST /recipients
   *  3. /cart/checkout {pickupPointId, pickupCarrier, recipientId} → attempt + snapshot
   *  4. /orders {cartId, snapshotId, idempotencyKey, deliveryQuoteId, paymentProvider}
   *     → orderId + paymentIntentId + clientSecret + totalAmount
   *  5. router.push success (`onConfirmed` orqali profile/orders)
   *
   * Xato yo'lda /cart/checkout/cancel chaqirilmaydi — backend snapshot
   * 15 min TTL bilan o'z-o'zidan tugaydi va cart unfreeze bo'ladi.
   *
   * `ORDER_DELIVERY_QUOTE_EXPIRED` (422) — quote 30 min TTL tugagan, lekin
   * snapshot hali tirik (15 min): bir martalik avto-refresh va createOrder
   * qayta urinish. Pickup tanlovi o'zgarmaydi.
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
    if (!quote?.quoteId) {
      setError({ code: 'QUOTE_REQUIRED', message: 'Рассчитайте стоимость доставки' });
      return null;
    }
    const cartId = cart?.id;
    if (!cartId) {
      setError({ code: 'EMPTY_CART', message: 'Корзина пуста' });
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

      // CHK-024: createOrder ichida quote ID retry uchun qayta o'qiymiz
      // (auto-refresh state yangilashi mumkin).
      const tryCreate = async (deliveryQuoteId) =>
        createOrder({
          cartId,
          snapshotId: attemptResp.snapshotId,
          idempotencyKey,
          paymentProvider: 'fake',
          deliveryQuoteId,
          __idempotencyKey: idempotencyKey,
        }).unwrap();

      beginConfirm();
      let orderResp;
      try {
        orderResp = await tryCreate(quote.quoteId);
      } catch (err) {
        const norm = normalizeApiError(err);
        // ORDER_DELIVERY_QUOTE_EXPIRED — quote TTL tugagan. Pickup tirik,
        // bir martalik avto-refresh va qayta urinish.
        if (norm.code === 'ORDER_DELIVERY_QUOTE_EXPIRED') {
          const refreshed = await refreshQuoteRef.current?.();
          if (refreshed?.quoteId) {
            try {
              orderResp = await tryCreate(refreshed.quoteId);
            } catch (retryErr) {
              const r = normalizeApiError(retryErr);
              setError({
                code: r.code,
                message: r.message || 'Не удалось оформить заказ',
              });
              const snap = useCheckoutStore.getState().removedItemsSnapshot?.length || 0;
              await restoreRemoved();
              if (snap > 0) {
                toast.info('Не удалось оформить заказ. Товары возвращены в корзину.');
              }
              return null;
            }
          } else {
            setError({
              code: 'QUOTE_EXPIRED',
              message: 'Срок котировки истёк, рассчитайте заново',
            });
            const snap = useCheckoutStore.getState().removedItemsSnapshot?.length || 0;
            await restoreRemoved();
            if (snap > 0) {
              toast.info('Не удалось оформить заказ. Товары возвращены в корзину.');
            }
            return null;
          }
        } else {
          // ORDER_DELIVERY_QUOTE_CURRENCY_MISMATCH — backend bug: cart va
          // quote valyutasi farq qiladi. Same-provider holatida bo'lmasligi
          // kerak. UI uchun oddiy toast, console'ga warn (kelajakda Sentry).
          if (isCurrencyMismatchError(err)) {
            console.warn('[CHK-024] currency mismatch between cart and quote', {
              code: norm.code,
              requestId: norm.requestId,
            });
          }
          setError({
            code: norm.code,
            message: norm.message || 'Не удалось оформить заказ',
          });
          const snap = useCheckoutStore.getState().removedItemsSnapshot?.length || 0;
          await restoreRemoved();
          if (snap > 0) {
            toast.info('Не удалось оформить заказ. Товары возвращены в корзину.');
          }
          return null;
        }
      }

      const newOrderId = orderResp?.orderId ?? null;
      setPayment({
        paymentIntentId: orderResp?.paymentIntentId ?? null,
        clientSecret: orderResp?.clientSecret ?? null,
        totalAmount: orderResp?.totalAmount ?? null,
        currency: orderResp?.currency || quote.currency || 'RUB',
      });
      setOrder(newOrderId);
      // CHK-004: muvaffaqiyatli buyurtma — snapshot endi kerak emas.
      clearRemovedSnapshot();
      // CHK-006: yangi attempt yangi key olishi uchun reset.
      resetKey(idempotencyKeyRef);
      clearPendingIdempotencyKey(INITIATE_CHECKOUT_URL);
      clearPendingIdempotencyKey(CREATE_ORDER_URL);
      return newOrderId;
    } finally {
      releaseInflight(inflightRef);
    }
  }, [
    pickup,
    quote,
    cart,
    prepareCart,
    ensureRecipient,
    initiateCheckout,
    createOrder,
    beginInitiate,
    setAttempt,
    beginConfirm,
    setOrder,
    setPayment,
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

  /* ── Tariff alternatives ── */

  /**
   * Fallback tarif tanlovi (`quote.fallbackAlternatives`'dan biri).
   * Status'ni QUOTING'ga qaytaradi (`refreshQuote` `setQuote → READY`
   * qiladi yoki error qaytaradi). Joriy tanlovga teng bo'lsa — no-op.
   */
  const selectServiceCode = useCallback(
    async (nextCode) => {
      if (!nextCode || typeof nextCode !== 'string') return null;
      if (quote?.serviceCode === nextCode) return quote;
      return (await refreshQuoteRef.current?.({ serviceCode: nextCode })) ?? null;
    },
    [quote]
  );

  /* ── Cross-border detection ── */

  // Spec §8.4: cross-border tovarlar (DobroPost CN→RU) uchun /rates/quote
  // faqat oxirgi mil narxini qaytaradi — yetkazib berishning xalqaro
  // ulushini menejer order'dan keyin qo'lda hisoblaydi.
  const hasCrossBorderItems = useMemo(
    () => selectedItems.some((it) => it?.supplierType === 'cross_border'),
    [selectedItems]
  );

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
      hasCrossBorderItems,
      // actions
      setSelection,
      setPickup,
      refreshQuote,
      selectServiceCode,
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
      hasCrossBorderItems,
      setSelection,
      setPickup,
      refreshQuote,
      selectServiceCode,
      placeOrder,
      abandon,
      goToCheckout,
      onConfirmed,
      reset,
    ]
  );
}
