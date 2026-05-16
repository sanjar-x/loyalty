'use client';

import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Trash2 } from 'lucide-react';
import Footer from '@/components/layout/Footer';
import ProductSection from '@/components/blocks/product/ProductSection';
import { useCart } from '@/components/blocks/cart/useCart';
import { useItemFavorites } from '@/lib/hooks/useItemFavorites';
import { useGetForYouFeedQuery } from '@/lib/store/api';
import { useCheckoutFlow } from '@/lib/checkout/useCheckoutFlow';
import BottomSheet from '@/components/ui/BottomSheet';
import styles from './page.module.css';
import cn from 'clsx';
import { mapProductCard } from '@/lib/adapters/mapProductCard';
import Header from '@/components/layout/Header';
import { useTelegram } from '@/lib/features/telegram/provider';

function formatRub(value) {
  try {
    return `${new Intl.NumberFormat('ru-RU').format(value)} ₽`;
  } catch {
    return `${value} ₽`;
  }
}

function pluralizeItemsRu(count) {
  const n = Math.abs(count);
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return 'товар';
  if (mod10 >= 2 && mod10 <= 4 && !(mod100 >= 12 && mod100 <= 14)) return 'товара';
  return 'товаров';
}

function CartSkeleton({ count = 3 }) {
  const n = Math.max(1, Math.trunc(Number(count) || 3));
  return (
    <div className={styles.p0} aria-busy="true" aria-live="polite">
      <div className={styles.spaceY3} aria-hidden="true">
        {Array.from({ length: n }).map((_, idx) => (
          <div key={idx} className={styles.c15}>
            <div className={cn(styles.c16, styles.tw6)}>
              <div className={cn(styles.c17, styles.tw7)}>
                <div className={styles.skelImg} />
              </div>

              <div className={cn(styles.c19, styles.skelBody)}>
                <div className={styles.skelLineLg} />
                <div className={styles.skelLineSm} />
                <div className={styles.skelLineXs} />
                <div className={styles.skelPrice} />
                <div className={styles.skelLineSm} />
                <div className={styles.skelRow}>
                  <div className={styles.skelIcons} />
                  <div className={styles.skelQty} />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className={styles.c37} aria-hidden="true">
        <div className={styles.skelSummaryLineLg} />
        <div className={styles.skelSummaryLineSm} />
        <div className={styles.skelSummaryLineSm} />
      </div>
    </div>
  );
}

// Lokal mapper'lar olib tashlandi — `lib/format/mapProductCard.js`
// orqali yagona umumiy implementatsiya ishlatiladi (har sahifada bir xil
// shape, regression yo'q).

// Selection endi `useCheckoutFlow` Zustand store'ida (sessionStorage persist).
const CHECKOUT_PROMO_KEY = 'loyaltymarket_checkout_promo_v1';

export default function TrashBasketPage() {
  const router = useRouter();
  const { initData: tgInitData } = useTelegram();
  // Telegram WebApp o'z native header'ini (title + ⋮ + X) ko'rsatadi —
  // shuning uchun Mini App ichida bizning empty-state header bar'ini
  // render qilmaymiz (duplikatsiyaning oldini olish). Oddiy brauzer/desktop
  // muhitida (initData yo'q) header bar ko'rinadi.
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

  // "Для вас" section — butun loyihada `for-you` endpoint ishlatiladi
  // (home sahifasi bilan bir xil source); `/catalog/storefront/products`
  // `category_id` majburiy talab qiladi va PLP uchun mo'ljallangan.
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
    // Tanlangan cart item.id larni `skuId`larga aylantirish — checkout
    // flow va backend (`/rates/quote`, `/cart/items`) skuId bilan ishlaydi.
    const selectedSkuIds = items
      .filter((it) => selectedIds.has(it.id))
      .map((it) => String(it.skuId))
      .filter(Boolean);
    // Promo hozircha localStorage'da qoldi (Spec §11: backend modul yo'q).
    // Buyurtma berilgandan keyin clientside discount UI'da hisoblanadi.
    try {
      if (appliedPromo) {
        localStorage.setItem(CHECKOUT_PROMO_KEY, JSON.stringify(appliedPromo));
      } else {
        localStorage.removeItem(CHECKOUT_PROMO_KEY);
      }
    } catch {
      // ignore
    }
    // Atomik: store'ga selection yozib, /checkout'ga navigate.
    // `goToCheckout` setSelection + router.push bajaradi (race-safe).
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
        // 👈 change this value
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
        // Telegram Mini App ichida: native header mavjud, bizga faqat
        // markaziy "Корзина" titlei kerak (vizual pozitsiya uchun).
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
                <div key={item.id} className={styles.c15}>
                  <div className={cn(styles.c16, styles.tw6)}>
                    <div className={cn(styles.c17, styles.tw7)}>
                      {item.image ? (
                        <img
                          src={item.image}
                          alt={item.name}
                          className={styles.c18}
                          loading="lazy"
                        />
                      ) : (
                        <div
                          className={styles.imagePlaceholder}
                          aria-label="Изображение недоступно"
                        >
                          <span className={styles.imagePlaceholderLetter}>
                            {item.name ? item.name.trim().charAt(0).toUpperCase() : '?'}
                          </span>
                        </div>
                      )}
                    </div>

                    <div className={cn(styles.c19, styles.tw8)}>
                      <div className={cn(styles.c20, styles.tw9)}>
                        <div className={cn(styles.c21, styles.tw10)}>
                          <div className={styles.c22}>
                            {item.isOrphaned ? 'Товар недоступен' : item.name}
                          </div>
                          {item.isOrphaned ? (
                            <div className={styles.orphanWarning}>
                              Снят с продажи — удалите из корзины
                            </div>
                          ) : null}
                          {!item.isOrphaned && item.shippingText?.trim() ? (
                            <div className={styles.c23}>{item.shippingText}</div>
                          ) : null}
                          <div className={styles.c24}>
                            {item.size ? (
                              <p>
                                Размер: <span className={styles.c24Value}>{item.size}</span>
                              </p>
                            ) : null}
                            {item.article ? (
                              <p>
                                Артикул: <span className={styles.c24Value}>{item.article}</span>
                              </p>
                            ) : null}
                          </div>
                        </div>

                        <input
                          type="checkbox"
                          checked={selectedIds.has(item.id)}
                          onChange={() => toggleSelect(item.id)}
                          className={cn(styles.c25, 'lm-checkbox')}
                        />
                      </div>

                      <div className={styles.c26}>{formatRub(item.priceRub)}</div>

                      {/* Delivery chip — dizayndagi "● 30 марта, из Китая".
                          Backend hozir aniq sana bermayotgani sababli faqat
                          supplier label'ni ko'rsatamiz; sana qo'shilganda
                          `item.deliveryEtaDisplay`'ni shu yerga qo'yamiz. */}
                      {!item.isOrphaned && item.deliveryText ? (
                        <div className={cn(styles.c27, styles.tw11)}>
                          <span className={cn(styles.c28, styles.tw12)} aria-hidden="true" />
                          <span>{item.deliveryText}</span>
                        </div>
                      ) : null}

                      <div className={styles.c29}>
                        <div className={cn(styles.c30, styles.tw13)}>
                          <button
                            type="button"
                            onClick={() =>
                              item.productId != null ? toggleProductFavorite(item.productId) : null
                            }
                            aria-label={
                              favoriteItemIds.has(item.productId)
                                ? 'Убрать из избранного'
                                : 'Добавить в избранное'
                            }
                            className={styles.iconButton}
                          >
                            <img
                              src={
                                favoriteItemIds.has(item.productId)
                                  ? '/icons/global/active-heart.svg'
                                  : '/icons/global/not-active-heart.svg'
                              }
                              alt=""
                              className={cn(styles.c31, styles.tw14)}
                            />
                          </button>

                          <button
                            type="button"
                            onClick={() => removeOne(item.id)}
                            aria-label="Удалить"
                            className={styles.iconButton}
                          >
                            <img
                              src="/icons/global/xicon.svg"
                              alt="Удалить"
                              className={cn(styles.c32, styles.tw15)}
                            />
                          </button>
                        </div>

                        <div className={cn(styles.c33, styles.tw16)}>
                          <button
                            type="button"
                            onClick={() => setQuantity(item.id, item.quantity - 1)}
                            className={styles.c34}
                          >
                            −
                          </button>
                          <span className={cn(styles.c35, styles.tw17)}>{item.quantity}</span>
                          <button
                            type="button"
                            onClick={() => setQuantity(item.id, item.quantity + 1)}
                            className={styles.c36}
                          >
                            +
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
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

      {/* К оформлению tugmasi - z-40 bilan */}
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
