'use client';

import { Suspense, useCallback, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import cn from 'clsx';

import { useCart } from '@/components/blocks/cart/useCart';
import { useCheckoutFlow } from '@/lib/checkout/useCheckoutFlow';
import { CheckoutStatus, useCheckoutStore } from '@/lib/checkout/store';
import { usePickupFromUrl } from '@/lib/checkout/usePickupFromUrl';
import { useCheckoutPageEffects } from '@/lib/checkout/useCheckoutPageEffects';
import { computeCheckoutTotals } from '@/lib/checkout/totals';
import { useListMyRecipientsQuery } from '@/lib/store/api';
import { validateRecipientForOrder } from '@/lib/checkout/validators';
import { decideCheckoutAction } from '@/lib/checkout/payAction';
import { providerLabel } from '@/lib/format/providerLabels';
import { formatMoney } from '@/lib/format/money';
import { toast } from '@/lib/ui/toast';
import RecipientSheet from '@/components/blocks/checkout/sheets/RecipientSheet';
import CustomsSheet from '@/components/blocks/checkout/sheets/CustomsSheet';
import CardSheet from '@/components/blocks/checkout/sheets/CardSheet';

import CheckoutTiles from './CheckoutTiles';
import CheckoutItemsList from './CheckoutItemsList';
import PaymentMethodPicker from './PaymentMethodPicker';
import CheckoutSummary from './CheckoutSummary';
import PayButtonFooter from './PayButtonFooter';
import styles from './page.module.css';

/**
 * `/checkout` — buyurtma rasmiylashtirish sahifasi.
 *
 * Audit #1 (god-komponentlar dekompozitsiyasi): ilgari bitta 883-satrli
 * fayl edi. Endi bu — tashkilotchi (orchestrator):
 *  • pure helper'lar  → `lib/format/{plural,price}.js`
 *  • URL/store sync   → `lib/checkout/usePickupFromUrl.js`
 *  • flow yon-effekt  → `lib/checkout/useCheckoutPageEffects.js`
 *  • presentation     → `./{CheckoutTiles,CheckoutItemsList,PaymentMethodPicker,
 *                          CheckoutSummary,PayButtonFooter}.jsx`
 *
 * Recipient/customs/promo/payment — `useCheckoutStore` (sessionStorage
 * persist). Card detail saqlanmaydi — PCI DSS spirit'i.
 *
 * @typedef {{ fullName: string, phoneDigits: string, email: string }} CheckoutRecipient
 * @typedef {{ passportSeries: string, passportNumber: string, issueDate: string, birthDate: string, inn: string }} CheckoutCustomsData
 */

export default function CheckoutPage() {
  return (
    <Suspense fallback={<div className={styles.c1} />}>
      <CheckoutPageInner />
    </Suspense>
  );
}

function CheckoutPageInner() {
  const router = useRouter();
  const { items } = useCart();

  // Backend orchestrator + URL'dan derive qilingan pickup + sahifa yon-effektlari.
  const flow = useCheckoutFlow();
  const { pickup, openPickupSelection } = usePickupFromUrl();
  useCheckoutPageEffects(flow);

  // Recipient/customs/promo/payment — Zustand store (sessionStorage persist).
  const recipient = useCheckoutStore((s) => s.recipient);
  const setRecipient = useCheckoutStore((s) => s.setRecipient);
  const setSelectedRecipientId = useCheckoutStore((s) => s.setSelectedRecipientId);
  const customs = useCheckoutStore((s) => s.customs);
  const setCustoms = useCheckoutStore((s) => s.setCustoms);
  const promo = useCheckoutStore((s) => s.promo);
  const paymentMethod = useCheckoutStore((s) => s.paymentMethod);
  const setPaymentMethod = useCheckoutStore((s) => s.setPaymentMethod);

  // Sheet open holatlari (CHK-020/023).
  const [isRecipientModalOpen, setIsRecipientModalOpen] = useState(false);
  const [isCustomsModalOpen, setIsCustomsModalOpen] = useState(false);
  const [isCardModalOpen, setIsCardModalOpen] = useState(false);

  const openRecipientModal = () => setIsRecipientModalOpen(true);
  const openCustomsModal = () => setIsCustomsModalOpen(true);
  const openCardModal = useCallback(() => setIsCardModalOpen(true), []);
  const closeCardModal = useCallback(() => setIsCardModalOpen(false), []);

  // CHK-021: saqlangan recipient ro'yxati — sheet ochilganda fetch.
  const { data: recipientsData, isLoading: isRecipientsLoading } = useListMyRecipientsQuery(
    undefined,
    { skip: !isRecipientModalOpen }
  );
  const savedRecipients = useMemo(
    () => (Array.isArray(recipientsData?.items) ? recipientsData.items : []),
    [recipientsData]
  );

  const handleSelectSavedRecipient = useCallback(
    (saved) => {
      const phoneDigits = String(saved.phone || '')
        .replace(/^\+?7/, '')
        .replace(/\D/g, '')
        .slice(0, 10);
      setRecipient({
        fullName: saved.fullNameRu || '',
        phoneDigits,
        email: saved.email || '',
        country: 'RU',
      });
      if (saved.recipientId) setSelectedRecipientId(saved.recipientId);
      setIsRecipientModalOpen(false);
      toast.success('Получатель выбран');
    },
    [setRecipient, setSelectedRecipientId]
  );

  // CHK-021/022: Telegram WebApp initData → recipient draft pre-fill.
  // Faqat first_name + last_name; broken UTF-8 artifact'lar sanitize qilinadi.
  const tgPrefillSource = useMemo(() => {
    if (recipient) return null;
    if (typeof window === 'undefined') return null;
    const tgUser = window.Telegram?.WebApp?.initDataUnsafe?.user;
    if (!tgUser) return null;
    const sanitizeName = (s) =>
      String(s || '')
        .replace(/[^А-Яа-яЁёA-Za-z'\- ]/g, '')
        .trim();
    return {
      first_name: sanitizeName(tgUser.first_name),
      last_name: sanitizeName(tgUser.last_name),
      phoneDigits: String(tgUser.phone_number || '')
        .replace(/^\+?7/, '')
        .replace(/\D/g, '')
        .slice(0, 10),
    };
  }, [recipient]);

  const [deliveryMode] = useState('pickup');
  const [pointsEnabled, setPointsEnabled] = useState(false);
  // Split to'lovi vaqtinchalik o'chirilgan — backend payment moduli yo'q
  // (Spec §11). `useSplit` state saqlanadi (setter chaqiriqlari ishlashi
  // uchun), UI toggle/sheet kommentga olingan — doim `false`.
  const [useSplit, setUseSplit] = useState(false);

  // Tanlangan tovarlar — UI-mapped shape (`useCart().items`) selection bilan
  // kesishtiriladi. `selectedSkuIds` bo'sh → butun cart.
  const selectedItems = useMemo(() => {
    const sel = flow.selectedSkuIds || [];
    if (sel.length === 0) return items;
    const set = new Set(sel.map((id) => String(id)));
    return items.filter((it) => set.has(String(it.skuId)));
  }, [items, flow.selectedSkuIds]);

  const groupedByDelivery = useMemo(() => {
    const map = new Map();
    for (const x of selectedItems) {
      const key = x.deliveryText || '';
      const bucket = map.get(key);
      if (bucket) bucket.push(x);
      else map.set(key, [x]);
    }
    return Array.from(map.entries());
  }, [selectedItems]);

  // Yagona pure totals (`lib/checkout/totals.js`). `flow.quote` haqiqiy
  // delivery narxini beradi; Loyalty Points moduli backend'da yo'q → `points: null`.
  const totals = useMemo(
    () =>
      computeCheckoutTotals({
        items: selectedItems,
        quote: flow.quote,
        promo,
        points: null,
      }),
    [selectedItems, flow.quote, promo]
  );

  const {
    itemCount: selectedQuantity,
    subtotal: subtotalMoney,
    delivery: deliveryMoney,
    discount: discountMoney,
    pointsDiscount: pointsMoney,
    total: totalMoney,
  } = totals;

  const deliveryPriceText =
    deliveryMode !== 'pickup'
      ? '—'
      : deliveryMoney == null
        ? 'Рассчитывается…'
        : formatMoney(deliveryMoney);

  const deliveryBulletText =
    deliveryMode === 'pickup' ? 'Доставка в пункт выдачи' : 'Доставка курьером';

  const payButtonTitle = useSplit
    ? 'Оформить сплит'
    : paymentMethod === 'sbp'
      ? 'Оплатить через СБП'
      : 'Оплатить картой';

  // Card last4 store'da saqlanmaydi — payment provider widget masked PAN
  // qaytarganda ko'rsatiladi. Hozircha suffix bo'sh.
  const payButtonSuffix = '';

  const isBusy =
    flow.status === CheckoutStatus.INITIATING || flow.status === CheckoutStatus.CONFIRMING;

  // CHK-005: Pay tugmasi pre-flight — pure qaror (`decideCheckoutAction`) →
  // side effect mapping. Tugma har doim enabled; click kerakli qadamga olib
  // boradi yoki toast bilan eslatadi.
  const handlePayClick = useCallback(async () => {
    const action = decideCheckoutAction({
      status: flow.status,
      initiatingStatus: CheckoutStatus.INITIATING,
      confirmingStatus: CheckoutStatus.CONFIRMING,
      selectedQuantity,
      isPickupSelected: flow.isPickupSelected,
      isQuoteValid: flow.isQuoteValid,
      recipient,
      customs,
      validate: validateRecipientForOrder,
    });
    switch (action.type) {
      case 'BUSY':
        return;
      case 'EMPTY_CART':
        toast.error(action.message);
        router.push('/cart');
        return;
      case 'NEED_PICKUP': {
        toast.error(action.message);
        const tile = document.querySelector('[data-checkout-pickup-tile]');
        tile?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return;
      }
      case 'NEED_QUOTE_REFRESH':
        toast.info(action.message);
        await flow.refreshQuote();
        return;
      case 'NEED_RECIPIENT':
        toast.error(action.message);
        setIsRecipientModalOpen(true);
        return;
      case 'NEED_CUSTOMS':
        toast.error(action.message);
        setIsCustomsModalOpen(true);
        return;
      case 'READY':
      default:
        // placeOrder o'zining inflight guard'iga ega (CHK-006); store
        // errorlari `useCheckoutPageEffects` toast watcher orqali chiqadi.
        await flow.placeOrder();
    }
  }, [flow, selectedQuantity, recipient, customs, router]);

  return (
    <div className={styles.c2}>
      <div className={styles.c3}>
        <h1 className={styles.c4}>Оформление заказа</h1>

        <div className={cn(styles.c5, styles.tw1)}>
          <button
            type="button"
            onClick={() => router.push(openPickupSelection)}
            className={cn(styles.c6, styles.tw2)}
          >
            <div className={styles.c7}>Пункт выдачи</div>
            {pickup.pickupAddress ? (
              <div className={cn(styles.c8)}>
                {pickup.pickupProvider
                  ? `${providerLabel(pickup.pickupProvider)} — ${pickup.pickupAddress}`
                  : pickup.pickupAddress}
              </div>
            ) : null}
            <div className={styles.c9}>{deliveryPriceText}</div>
          </button>
          <div className={styles.c10}>
            <div className={styles.c11}>Курьером</div>
            <div className={styles.c12}>Нет курьерской доставки</div>
          </div>
        </div>

        <div className={styles.c13}>
          <CheckoutTiles
            pickup={pickup}
            recipient={recipient}
            onOpenPickup={() => router.push(openPickupSelection)}
            onOpenRecipient={openRecipientModal}
            onOpenCustoms={openCustomsModal}
          />

          <CheckoutItemsList
            selectedQuantity={selectedQuantity}
            groupedByDelivery={groupedByDelivery}
            deliveryPriceText={deliveryPriceText}
            onReturnToCart={() => router.push('/cart')}
          />

          <div className={styles.c53}>
            <PaymentMethodPicker
              paymentMethod={paymentMethod}
              onSelectSbp={() => {
                setUseSplit(false);
                setPaymentMethod('sbp');
              }}
              onOpenCard={openCardModal}
            />

            <CheckoutSummary
              selectedQuantity={selectedQuantity}
              subtotalMoney={subtotalMoney}
              discountMoney={discountMoney}
              promo={promo}
              deliveryPriceText={deliveryPriceText}
              deliveryBulletText={deliveryBulletText}
              pointsMoney={pointsMoney}
              pointsEnabled={pointsEnabled}
              onTogglePoints={() => setPointsEnabled((v) => !v)}
              totalMoney={totalMoney}
              quote={flow.quote}
              onSelectServiceCode={flow.selectServiceCode}
              hasCrossBorderItems={flow.hasCrossBorderItems}
            />
          </div>

          {/* Split (сплит) bo'lim vaqtinchalik o'chirilgan — backend payment
              moduli yo'q (Spec §11). Tayyor bo'lganda quyidagi blokni
              kommentdan oling. */}
          {/*
          <div className={styles.c80}>
            <div className={styles.c81}>
              <div className={styles.c82}>
                <div className={cn(styles.c83, styles.tw25)}>
                  <div className={cn(styles.c84, styles.tw26)}>
                    <img
                      src="/icons/global/split.svg"
                      alt=""
                      className={cn(styles.c85, styles.tw27)}
                    />
                    <div className={cn(styles.c86, styles.tw28)}>
                      <div className={styles.c87}>4×880₽ в сплит</div>
                      <div className={styles.c88}>
                        На 2 месяца без переплаты
                      </div>
                    </div>
                  </div>

                  <button
                    type="button"
                    aria-label="Включить сплит"
                    aria-pressed={useSplit}
                    onClick={() => {
                      setUseSplit((prev) => {
                        const next = !prev;
                        if (next) {
                          setPaymentMethod("card");
                          if (!card) openCardModal();
                        }
                        return next;
                      });
                    }}
                    className={cn(
                      styles.toggle,
                      useSplit ? styles.toggleOn : styles.toggleOff,
                    )}
                  >
                    <span
                      className={cn(
                        styles.toggleThumb,
                        useSplit ? styles.toggleThumbOn : styles.toggleThumbOff,
                      )}
                    />
                  </button>
                </div>

                <div className={styles.c89}>
                  <span>Сегодня</span>
                  <span>Ещё 3 платежа раз в 2 недели</span>
                </div>
                <div className={cn(styles.c90, styles.tw29)}>
                  <div className={cn(styles.c91, styles.tw30)} />
                  <div className={cn(styles.c92, styles.tw31)} />
                  <div className={cn(styles.c93, styles.tw32)} />
                  <div className={cn(styles.c94, styles.tw33)} />
                </div>
              </div>
            </div>
          </div>
          */}

          <PayButtonFooter
            isBusy={isBusy}
            canPlaceOrder={flow.canPlaceOrder}
            payButtonTitle={payButtonTitle}
            paymentMethod={paymentMethod}
            payButtonSuffix={payButtonSuffix}
            onPay={handlePayClick}
          />
        </div>
      </div>

      <RecipientSheet
        open={isRecipientModalOpen}
        onClose={() => setIsRecipientModalOpen(false)}
        initialValue={recipient}
        prefillSource={tgPrefillSource}
        savedRecipients={savedRecipients}
        isLoadingSaved={isRecipientsLoading}
        onSelectSaved={handleSelectSavedRecipient}
        onSave={(payload) => {
          setRecipient(payload);
          setIsRecipientModalOpen(false);
          toast.success('Данные сохранены');
        }}
      />

      <CustomsSheet
        open={isCustomsModalOpen}
        onClose={() => setIsCustomsModalOpen(false)}
        initialValue={customs}
        onSave={(payload) => {
          setCustoms(payload);
          setIsCustomsModalOpen(false);
          toast.success('Данные сохранены');
        }}
      />

      <CardSheet
        open={isCardModalOpen}
        onClose={closeCardModal}
        onSave={() => {
          // CHK-023 PCI: card detail brauzerda saqlanmaydi (useCardForm draft
          // tashlab yuboriladi). Faqat paymentMethod="card" lokal state'da.
          setPaymentMethod('card');
          setIsCardModalOpen(false);
          toast.success('Карта добавлена');
        }}
      />
    </div>
  );
}
