'use client';

import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Trash2 } from 'lucide-react';
import Footer from '@/widgets/Footer';
import { ProductSection } from '@/entities/product';
import { useCart } from '@/entities/cart';
import { useItemFavorites } from '@/features/favorites';
import { useGetForYouFeedQuery } from '@/entities/product';
import { useCheckoutFlow } from '@/features/checkout-flow';
import BottomSheet from '@/shared/ui/BottomSheet';
import styles from './page.module.css';
import { cn } from '@/shared/lib/ui-utils';
import { mapProductCard } from '@/entities/product';
import { pluralizeItemsRu } from '@/shared/lib/i18n/plural';
import Header from '@/widgets/Header';
import { useTelegram } from '@/entities/user';
import CartItemRow from '@/widgets/CartPage/CartItemRow';
import CartSkeleton from '@/widgets/CartPage/CartSkeleton';

// Local mappers were removed — a single shared implementation from
// `lib/format/mapProductCard.js` is used (same shape on every page, no
// regression).

// Selection now lives in the `useCheckoutFlow` Zustand store (sessionStorage persist).
const CHECKOUT_PROMO_KEY = 'loyaltymarket_checkout_promo_v1';

export default function TrashBasketPage() {
  const router = useRouter();
  const { initData: tgInitData } = useTelegram();
  // The Telegram WebApp shows its own native header (title + ⋮ + X) —
  // so inside the Mini App we don't render our empty-state header bar
  // (to avoid duplication). In a regular browser/desktop environment
  // (no initData) the header bar is shown.
  const isTelegramEnv = Boolean(tgInitData);

  const {
    ready: cartReady,
    isLoading: cartIsLoading,
    isFetching: cartIsFetching,
    items,
    removeItem,
    setQuantity,
    removeMany,
  } = useCart();

  const { favoriteItemIds, toggleFavorite: toggleProductFavorite } = useItemFavorites('product');

  // "Для вас" section — the `for-you` endpoint is used project-wide
  // (same source as the home page); `/catalog/storefront/products`
  // requires `category_id` and is meant for the PLP.
  const {
    data: forYouResponse,
    isLoading: isForYouLoading,
    isFetching: isForYouFetching,
  } = useGetForYouFeedQuery({ limit: 8 });

  const forYouProducts = useMemo(() => {
    const items = Array.isArray(forYouResponse?.items) ? forYouResponse.items : [];
    return items.map((p) => mapProductCard(p, null)).filter(Boolean);
  }, [forYouResponse]);

  const isForYouInitialLoading =
    Boolean(isForYouLoading || isForYouFetching) &&
    (!Array.isArray(forYouResponse?.items) || forYouResponse.items.length === 0);

  const [unselectedIds, setUnselectedIds] = useState(() => new Set());

  const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false);
  const selectedIds = useMemo(() => {
    const next = new Set();
    for (const item of items) {
      if (!unselectedIds.has(item.id)) next.add(item.id);
    }
    return next;
  }, [items, unselectedIds]);

  const { selectedQuantity, selectedSubtotalRub } = useMemo(() => {
    let nextQuantity = 0;
    let nextSubtotalRub = 0;
    for (const item of items) {
      if (!selectedIds.has(item.id)) continue;
      nextQuantity += item.quantity;
      const line = Number(item.lineTotalRub);
      if (Number.isFinite(line)) nextSubtotalRub += line;
      else nextSubtotalRub += item.priceRub * item.quantity;
    }
    return {
      selectedQuantity: nextQuantity,
      selectedSubtotalRub: nextSubtotalRub,
    };
  }, [items, selectedIds]);

  const allSelected = items.length > 0 && selectedIds.size === items.length;

  const toggleSelect = (id) => {
    setUnselectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    setUnselectedIds((prev) => {
      if (items.length === 0) return prev;
      const areAllSelected = items.every((x) => !prev.has(x.id));
      if (areAllSelected) return new Set(items.map((x) => x.id));
      return new Set();
    });
  };

  const openDeleteConfirm = () => setIsDeleteConfirmOpen(true);
  const closeDeleteConfirm = () => setIsDeleteConfirmOpen(false);
  const confirmDeleteSelected = () => {
    removeMany(selectedIds);
    setUnselectedIds((prev) => {
      const next = new Set(prev);
      for (const id of selectedIds) next.add(id);
      return next;
    });
    setIsDeleteConfirmOpen(false);
  };

  const removeOne = (id) => {
    removeItem(id);
    setUnselectedIds((prev) => new Set(prev).add(id));
  };

  const TEST_PROMO_CODES = useMemo(
    () => [
      {
        code: 'PROMO100',
        discountRub: 500,
      },
    ],
    []
  );
  const [promoCode, setPromoCode] = useState('');
  const [promoStatus, setPromoStatus] = useState('idle');
  const [appliedPromo, setAppliedPromo] = useState(null);

  const promoActive = promoCode.trim().length > 0;
  const promoNormalized = promoCode.trim().toUpperCase();

  const onPromoChange = (value) => {
    setPromoCode(value);
    if (promoStatus !== 'idle' || appliedPromo) {
      setPromoStatus('idle');
      setAppliedPromo(null);
    }
  };

  const applyPromo = () => {
    if (!promoActive) {
      setPromoStatus('idle');
      setAppliedPromo(null);
      return;
    }

    const match = TEST_PROMO_CODES.find((p) => p.code === promoNormalized);
    if (match) {
      setPromoStatus('success');
      setAppliedPromo(match);
      return;
    }

    setPromoStatus('error');
    setAppliedPromo(null);
  };

  const { goToCheckout } = useCheckoutFlow();

  const proceedToCheckout = () => {
    if (selectedIds.size === 0) return;
    // Convert selected cart item.id values to `skuId`s — the checkout
    // flow and the backend (`/rates/quote`, `/cart/items`) work with skuId.
    const selectedSkuIds = items
      .filter((it) => selectedIds.has(it.id))
      .map((it) => String(it.skuId))
      .filter(Boolean);
    // Promo currently stays in localStorage (Spec §11: no backend module).
    // After the order is placed, the discount is computed client-side in the UI.
    try {
      if (appliedPromo) {
        localStorage.setItem(CHECKOUT_PROMO_KEY, JSON.stringify(appliedPromo));
      } else {
        localStorage.removeItem(CHECKOUT_PROMO_KEY);
      }
    } catch {
      // ignore
    }
    // Atomic: write the selection to the store, then navigate to /checkout.
    // `goToCheckout` does setSelection + router.push (race-safe).
    goToCheckout(selectedSkuIds);
  };

  const discountRub = selectedQuantity > 0 ? (appliedPromo?.discountRub ?? 0) : 0;
  const totalRub = Math.max(0, selectedSubtotalRub - discountRub);

  const itemsWord = pluralizeItemsRu(selectedQuantity);

  let showEmpty = cartReady && items.length === 0;

  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 50) {
        // change this value
        setIsScrolled(true);
      } else {
        setIsScrolled(false);
      }
    };

    window.addEventListener('scroll', handleScroll);

    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Empty state header (Basket.png empty design): "Закрыть" pill on the
  // left, centered "Корзина" title, three-dots on the right. Rendered ONLY
  // when cart is empty — normal (non-empty) flow keeps the existing sticky
  // `<Header />` + counters bar.
  const handleHeaderClose = () => {
    router.back();
  };

  return (
    <div className={styles.c1}>
      {showEmpty && !isTelegramEnv ? (
        <div className={styles.emptyHeader}>
          <button
            type="button"
            onClick={handleHeaderClose}
            className={styles.emptyHeaderPill}
            aria-label="Закрыть"
          >
            <img src="/icons/global/xiconBlack.svg" alt="" />
            <span>Закрыть</span>
          </button>
          <h1 className={styles.emptyHeaderTitle}>Корзина</h1>
          <button type="button" className={styles.emptyHeaderMore} aria-label="Меню">
            <img src="/icons/global/threeDots.svg" alt="" />
          </button>
        </div>
      ) : showEmpty && isTelegramEnv ? (
        // Inside the Telegram Mini App: the native header is already
        // there, we only need the centered "Корзина" title (for visual
        // positioning).
        <div className={styles.emptyHeaderCompact}>
          <h1 className={styles.emptyHeaderTitle}>Корзина</h1>
        </div>
      ) : (
        <div className={`${isScrolled ? `${styles.trashShow}` : `${styles.trashNone}`}`}>
          <Header title={'Корзина'} />
        </div>
      )}
      <div className={styles.c2} style={{ display: showEmpty ? 'none' : 'block' }}>
        <div className={styles.tw1}>
          <p className={styles.c4}>Корзина</p>
          {!cartReady && (cartIsLoading || cartIsFetching) ? (
            <span className={styles.skelHeaderCount} aria-hidden="true" />
          ) : items.length > 0 ? (
            <p className={styles.c5}>
              {selectedQuantity} {itemsWord}
            </p>
          ) : null}
        </div>

        {items.length > 0 ? (
          <div className={styles.c6}>
            <button
              type="button"
              onClick={openDeleteConfirm}
              className={cn(styles.c7, styles.tw2)}
              disabled={selectedIds.size === 0}
            >
              <img src="/icons/global/xicon.svg" alt="" className={cn(styles.c8, styles.tw3)} />{' '}
              <span>Удалить выбранные</span>
            </button>

            <label className={cn(styles.c9, styles.tw4)}>
              Выбрать все
              <input
                type="checkbox"
                checked={allSelected}
                onChange={toggleSelectAll}
                className="lm-checkbox"
              />
            </label>
          </div>
        ) : null}
      </div>

      <main className={styles.c10}>
        {!cartReady ? (
          <CartSkeleton count={3} />
        ) : showEmpty ? (
          <div className={styles.p0}>
            <div className={styles.c11}>
              <div className={styles.c12}>В корзине пока пусто</div>
              <div className={styles.c13}>А товаров полно — ищите их в каталоге</div>
              <Link href="/catalog" className={cn(styles.c14, styles.tw5)}>
                За покупками
              </Link>
            </div>
          </div>
        ) : (
          <>
            <div className={styles.spaceY3}>
              {items.map((item) => (
                <CartItemRow
                  key={item.id}
                  item={item}
                  isSelected={selectedIds.has(item.id)}
                  isFavorite={favoriteItemIds.has(item.productId)}
                  onToggleSelect={() => toggleSelect(item.id)}
                  onToggleFavorite={() =>
                    item.productId != null ? toggleProductFavorite(item.productId) : null
                  }
                  onRemove={() => removeOne(item.id)}
                  onSetQuantity={(q) => setQuantity(item.id, q)}
                />
              ))}
            </div>

            <div className={styles.c37}>
              <div
                className={cn(
                  styles.promoContainer,
                  promoActive ? styles.promoContainerActive : styles.promoContainerInactive
                )}
              >
                <div className={cn(styles.c38, styles.tw18)}>
                  {promoActive ? <div className={styles.c39}>Промокод</div> : null}
                  <input
                    type="text"
                    value={promoCode}
                    onChange={(e) => onPromoChange(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') applyPromo();
                    }}
                    placeholder={promoActive ? '' : 'Промокод'}
                    className={cn(
                      styles.promoInput,
                      promoStatus === 'success'
                        ? styles.promoInputSuccess
                        : promoStatus === 'error'
                          ? styles.promoInputError
                          : styles.promoInputDefault,
                      promoActive ? styles.promoInputActive : styles.promoInputInactive
                    )}
                  />
                </div>

                {promoActive ? (
                  <button
                    type="button"
                    aria-label="Применить промокод"
                    onClick={applyPromo}
                    className={cn(styles.c40, styles.tw19)}
                  >
                    <img
                      src="/icons/global/arrow.svg"
                      alt=""
                      className={cn(styles.c41, styles.tw20)}
                    />
                  </button>
                ) : null}
              </div>

              {promoStatus === 'success' ? (
                <div className={cn(styles.c42, styles.tw21)}>Промокод применён</div>
              ) : null}

              {promoStatus === 'error' ? (
                <div className={cn(styles.c43, styles.tw22)}>Такого промокода нет</div>
              ) : null}

              <div className={cn(styles.c44, styles.spaceY2)}>
                <div className={styles.c45}>
                  <span>
                    {selectedQuantity} {itemsWord}
                  </span>
                  <span className={styles.c46}>{formatRub(selectedSubtotalRub)}</span>
                </div>
                <div className={styles.c47}>
                  <span className={cn(styles.c48, styles.tw23)}>
                    <span>Скидка</span>
                    <img
                      src="/icons/global/small-arrow.svg"
                      alt=""
                      className={cn(styles.c49, styles.tw24)}
                    />
                  </span>
                  <span>{discountRub > 0 ? `-${formatRub(discountRub)}` : '0 ₽'}</span>
                </div>

                {discountRub > 0 && appliedPromo ? (
                  <div className={styles.c50}>
                    <span className={styles.c51}>• Промокод {appliedPromo.code}</span>
                    <span>-{formatRub(discountRub)}</span>
                  </div>
                ) : null}
                <div className={styles.c52}>
                  <span className={cn(styles.c53, styles.tw25)}>
                    <span>Доставка</span>
                    <span className={cn(styles.c54, styles.tw26)}>
                      <button
                        type="button"
                        aria-label="Информация о доставке"
                        className={cn(styles.c55, styles.tw27)}
                      >
                        <img
                          src="/icons/global/Info.svg"
                          alt=""
                          className={cn(styles.c56, styles.tw28)}
                        />
                      </button>
                    </span>
                  </span>
                  <span>при оформлении</span>
                </div>

                <div className={styles.c58}>
                  <span className={styles.c59}>Итого</span>
                  <div className={cn(styles.c60, styles.tw30)}>
                    {selectedQuantity > 0 ? (
                      <>
                        <span className={styles.c61}>{formatRub(totalRub)}</span>
                        {discountRub > 0 ? (
                          <span className={cn(styles.c62, styles.tw31)}>
                            {formatRub(selectedSubtotalRub)}
                          </span>
                        ) : null}
                      </>
                    ) : (
                      <span className={styles.c63}>Выберите товары</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </>
        )}

        <div className={styles.c64}>
          <ProductSection
            title="Для вас"
            products={forYouProducts}
            onToggleFavorite={toggleProductFavorite}
            favoriteItemIds={favoriteItemIds}
            layout="grid"
            isLoading={isForYouInitialLoading}
            skeletonCount={6}
          />
        </div>
      </main>

      {/* "К оформлению" button — with z-40 */}
      {items.length > 0 ? (
        <div className={cn(styles.c66, styles.tw32)}>
          <div className={styles.c67}>
            <div
              className={cn(
                styles.checkoutBar,
                selectedQuantity > 0 ? styles.checkoutBarEnabled : styles.checkoutBarDisabled
              )}
              onClick={proceedToCheckout}
            >
              {selectedQuantity > 0 ? (
                <>
                  <span className={styles.c68}>
                    {selectedQuantity} {pluralizeItemsRu(selectedQuantity)}
                  </span>
                  <p className={styles.c69}>К оформлению</p>
                  <div className={cn(styles.c70, styles.tw33)}>
                    <span className={styles.c71}>{formatRub(totalRub)}</span>
                    {discountRub > 0 ? (
                      <span className={cn(styles.c72, styles.tw34)}>
                        {formatRub(selectedSubtotalRub)}
                      </span>
                    ) : null}
                  </div>
                </>
              ) : (
                <p className={styles.c73}>Выберите товары</p>
              )}
            </div>
          </div>
        </div>
      ) : null}

      <BottomSheet
        open={isDeleteConfirmOpen}
        onClose={closeDeleteConfirm}
        ariaLabel="Удаление товаров из корзины"
        header={<div className={styles.deleteSheetHeader} />}
      >
        <div className={styles.deleteSheetContent}>
          <button
            type="button"
            onClick={confirmDeleteSelected}
            className={cn(styles.c79, styles.tw38)}
          >
            <Trash2 className={cn(styles.c80, styles.tw39)} />
            <span className={styles.c81}>Удалить товары из корзины</span>
          </button>

          <button
            type="button"
            onClick={closeDeleteConfirm}
            className={cn(styles.c82, styles.tw40)}
          >
            Отмена
          </button>
        </div>
      </BottomSheet>

      <Footer />
    </div>
  );
}
