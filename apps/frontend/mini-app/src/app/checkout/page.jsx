'use client';

import { Suspense, useCallback, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { cn } from '@/shared/lib/ui-utils';

import { useCart } from '@/entities/cart';
import { useCheckoutFlow } from '@/features/checkout-flow';
import { CheckoutStatus, useCheckoutStore } from '@/features/checkout-flow';
import { usePickupFromUrl } from '@/features/pickup-selection/model/usePickupFromUrl';
import { useCheckoutPageEffects } from '@/features/checkout-flow/model/useCheckoutPageEffects';
import { computeCheckoutTotals } from '@/features/checkout-flow/lib/totals';
import { useListMyRecipientsQuery } from '@/entities/recipient';
import { validateRecipientForOrder } from '@/features/checkout-flow';
import { decideCheckoutAction } from '@/features/checkout-flow/lib/payAction';
import { providerLabel } from '@/entities/pickup-point/lib/providerLabels';
import { formatMoney } from '@/shared/lib/money';
import { toast } from '@/shared/ui/Toaster';
import { RecipientSheet } from '@/features/recipient-form';
import { CardSheet, PassportSheet, selectHasCrossBorderItems } from '@/features/checkout-flow';
import { maskPassportNumber, useGetPassportQuery } from '@/entities/passport';

import CheckoutTiles from '@/widgets/CheckoutPage/CheckoutTiles';
import CheckoutItemsList from '@/widgets/CheckoutPage/CheckoutItemsList';
import PaymentMethodPicker from '@/widgets/CheckoutPage/PaymentMethodPicker';
import CheckoutSummary from '@/widgets/CheckoutPage/CheckoutSummary';
import PayButtonFooter from '@/widgets/CheckoutPage/PayButtonFooter';
import styles from './page.module.css';

/**
 * `/checkout` — order placement page.
 *
 * Audit #1 (god-component decomposition): this used to be a single
 * 883-line file. Now it's an orchestrator:
 *  • pure helpers       → `lib/format/{plural,price}.js`
 *  • URL/store sync     → `lib/checkout/usePickupFromUrl.js`
 *  • flow side effects  → `lib/checkout/useCheckoutPageEffects.js`
 *  • presentation       → `./{CheckoutTiles,CheckoutItemsList,PaymentMethodPicker,
 *                            CheckoutSummary,PayButtonFooter}.jsx`
 *
 * Recipient / passport (ADR-011) / promo / payment — `useCheckoutStore`
 * (sessionStorage persist). Card details are not stored — in the spirit
 * of PCI DSS. Customs documents migrated to the Passport bounded context
 * — Sprint 1.5 Part 2.
 *
 * @typedef {{ fullName: string, phoneDigits: string, email: string }} CheckoutRecipient
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

  // Backend orchestrator + pickup derived from the URL + page side effects.
  const flow = useCheckoutFlow();
  const { pickup, openPickupSelection } = usePickupFromUrl();
  useCheckoutPageEffects(flow);

  // Recipient / passport / promo / payment — Zustand store
  // (sessionStorage persist).
  const recipient = useCheckoutStore((s) => s.recipient);
  const setRecipient = useCheckoutStore((s) => s.setRecipient);
  const setSelectedRecipientId = useCheckoutStore((s) => s.setSelectedRecipientId);
  const passportId = useCheckoutStore((s) => s.passportId);
  const setPassportId = useCheckoutStore((s) => s.setPassportId);
  const promo = useCheckoutStore((s) => s.promo);
  const paymentMethod = useCheckoutStore((s) => s.paymentMethod);
  const setPaymentMethod = useCheckoutStore((s) => s.setPaymentMethod);

  // ADR-011: cart-flow renders the Passport tile / sheet only when the
  // cart contains at least one cross-border item. `selectHasCrossBorderItems`
  // is exported from the store so other consumers (tests, future widgets)
  // share one definition.
  const hasCrossBorderItems = useMemo(() => selectHasCrossBorderItems(items), [items]);

  // PII-minimised passport summary for the CheckoutTiles tile. Fetched
  // lazily — only when a passport is resolved.
  const { data: selectedPassport } = useGetPassportQuery(passportId);
  const passportSummary = useMemo(() => {
    if (!selectedPassport) return null;
    return maskPassportNumber(selectedPassport.passportSerial, selectedPassport.passportNumber);
  }, [selectedPassport]);

  // Sheet open states (CHK-020/023).
  const [isRecipientModalOpen, setIsRecipientModalOpen] = useState(false);
  const [isPassportModalOpen, setIsPassportModalOpen] = useState(false);
  const [isCardModalOpen, setIsCardModalOpen] = useState(false);

  const openRecipientModal = () => setIsRecipientModalOpen(true);
  const openPassportModal = useCallback(() => setIsPassportModalOpen(true), []);
  const closePassportModal = useCallback(() => setIsPassportModalOpen(false), []);
  const openCardModal = useCallback(() => setIsCardModalOpen(true), []);
  const closeCardModal = useCallback(() => setIsCardModalOpen(false), []);

  // CHK-021: list of saved recipients — fetched when the sheet opens.
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
  // Only first_name + last_name; broken UTF-8 artifacts are sanitized.
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
  // Split payment is temporarily disabled — no backend payment module
  // (Spec §11). The `useSplit` state is kept (so setter calls keep
  // working), the UI toggle/sheet is commented out — it's always `false`.
  const [useSplit, setUseSplit] = useState(false);

  // Selected items — UI-mapped shape (`useCart().items`) intersected with
  // the selection. Empty `selectedSkuIds` → the whole cart.
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

  // Single pure totals (`lib/checkout/totals.js`). `flow.quote` provides
  // the real delivery price; the Loyalty Points module is missing from
  // the backend → `points: null`.
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

  // Card last4 is not stored — it will be shown once the payment provider
  // widget returns a masked PAN. For now the suffix is empty.
  const payButtonSuffix = '';

  const isBusy =
    flow.status === CheckoutStatus.INITIATING || flow.status === CheckoutStatus.CONFIRMING;

  // CHK-005: Pay button pre-flight — pure decision
  // (`decideCheckoutAction`) → side effect mapping. The button is always
  // enabled; the click leads to the required step or reminds via a toast.
  const handlePayClick = useCallback(async () => {
    const action = decideCheckoutAction({
      status: flow.status,
      initiatingStatus: CheckoutStatus.INITIATING,
      confirmingStatus: CheckoutStatus.CONFIRMING,
      selectedQuantity,
      isPickupSelected: flow.isPickupSelected,
      isQuoteValid: flow.isQuoteValid,
      recipient,
      hasCrossBorderItems,
      passportId,
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
      case 'NEED_PASSPORT':
        // ADR-011: cross-border cart without resolved passportId.
        toast.error(action.message);
        setIsPassportModalOpen(true);
        return;
      case 'READY':
      default:
        // placeOrder has its own inflight guard (CHK-006); store errors
        // are surfaced through the `useCheckoutPageEffects` toast watcher.
        await flow.placeOrder();
    }
  }, [flow, selectedQuantity, recipient, hasCrossBorderItems, passportId, router]);

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
            hasCrossBorderItems={hasCrossBorderItems}
            passportSummary={passportSummary}
            onOpenPickup={() => router.push(openPickupSelection)}
            onOpenRecipient={openRecipientModal}
            onOpenPassport={openPassportModal}
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

      <PassportSheet
        open={isPassportModalOpen}
        onClose={closePassportModal}
        selectedId={passportId}
        onResolved={(id) => {
          setPassportId(id);
          toast.success('Паспорт выбран');
        }}
      />

      <CardSheet
        open={isCardModalOpen}
        onClose={closeCardModal}
        onSave={() => {
          // CHK-023 PCI: card details are not stored in the browser
          // (the useCardForm draft is dropped). Only paymentMethod="card"
          // is kept in local state.
          setPaymentMethod('card');
          setIsCardModalOpen(false);
          toast.success('Карта добавлена');
        }}
      />
    </div>
  );
}
