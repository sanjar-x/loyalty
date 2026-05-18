'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { cn as cx } from '@/shared/lib/ui-utils';

import BottomSheet from '@/shared/ui/BottomSheet';
// FSD: features import app/providers/store → creates a cycle when the entity
// barrel re-exports UI that consumes the feature. We use the codegen
// directly (long names) + local thin wrappers.
import {
  useGetStorefrontProductApiV1StorefrontProductsSlugGetQuery,
  useAddItemApiV1CartItemsPostMutation,
} from '@/shared/api/codegen/api';
import { normalizeApiError, humanizeApiError } from '@/shared/api/errors';
import { formatRub as formatRubShared } from '@/shared/lib/money';

const useGetProductByIdQuery = (slugOrId, opts) =>
  useGetStorefrontProductApiV1StorefrontProductsSlugGetQuery({ slug: String(slugOrId) }, opts);
const useAddCartItemMutation = () => {
  const [trigger, state] = useAddItemApiV1CartItemsPostMutation();
  const wrapped = (payload) =>
    trigger({
      'x-anonymous-token': undefined,
      addItemRequest: {
        skuId: payload?.skuId,
        quantity: Math.max(1, Math.floor(Number(payload?.quantity || 1))),
      },
      productId: payload?.productId,
      variantId: payload?.variantId,
      productName: payload?.productName,
      variantLabel: payload?.variantLabel,
      imageUrl: payload?.imageUrl,
      priceRub: payload?.priceRub,
      supplierType: payload?.supplierType,
    });
  return [wrapped, state];
};

import styles from './QuickAddSheet.module.css';

// Cart page — `/cart` route. "Buy now" leads here.
// `/checkout` is the pickup-point + order-completion page.
const CART_ROUTE = '/cart';

/**
 * Telegram Mini App haptic feedback. If the SDK isn't available, silently skip.
 *
 * Spec: Telegram WebApp `HapticFeedback.notificationOccurred(type)` —
 * `success` when add succeeds, `error` on failure.
 */
function tgHaptic(type) {
  try {
    const fn = window?.Telegram?.WebApp?.HapticFeedback?.notificationOccurred;
    if (typeof fn === 'function') fn.call(window.Telegram.WebApp.HapticFeedback, type);
  } catch {
    // ignore — haptic best-effort
  }
}

const SUBMIT_STATE = Object.freeze({
  IDLE: 'idle',
  SUBMITTING: 'submitting',
  SUCCESS: 'success',
  ERROR: 'error',
});

const SUCCESS_AUTO_CLOSE_MS = 700;

/**
 * Extract a number from a pre-formatted rubles string.
 * "5 000 ₽" / "5,000.00 RUB" / "5000" → 5000
 *
 * `mapProductCard` (legacy PLP mapper) produces `price` in this shape.
 * We need to convert it to a number before passing to `formatRub`.
 */
function parseRubString(value) {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (typeof value !== 'string') return null;
  // Keep only digits and the decimal point; thousand separators (space, comma)
  // are dropped. "5 000.50" → "5000.50"
  const cleaned = value.replace(/[^\d.]/g, '');
  if (!cleaned) return null;
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : null;
}

/**
 * Returns the first usable (>0) price from several sources.
 * Order: SKU resolvedPrice → SKU base price → merged.price → product.price (PLP).
 */
function coalescePriceRub(...candidates) {
  for (const c of candidates) {
    const n = parseRubString(c);
    if (n != null && n > 0) return n;
  }
  return null;
}

function formatRub(rub) {
  const n = parseRubString(rub);
  if (n == null || n <= 0) return '—';
  return formatRubShared(n);
}

/**
 * SKU's display label — `mapSku` already computes a `label` field
 * (clothing size pattern: XS/S/M/L/XL, numeric sizes, or skuCode tail).
 */
function skuLabel(sku) {
  if (typeof sku?.label === 'string' && sku.label.trim()) return sku.label;
  return sku?.id ? String(sku.id).slice(0, 4).toUpperCase() : '—';
}

/**
 * Flattens `variants[].skus[]` inside a mapped product (mapStorefrontProduct
 * output) into a flat SKU list, attaching the display variant group to each
 * SKU. For a single-variant product — a flat list without groups.
 */
function buildSkuGroups(product) {
  const variants = Array.isArray(product?.variants) ? product.variants : [];
  if (!variants.length) {
    const flat = Array.isArray(product?.skus) ? product.skus : [];
    return flat.length ? [{ id: null, name: '', skus: flat.filter(Boolean) }] : [];
  }
  return variants
    .map((v) => ({
      id: v?.id ?? null,
      name: typeof v?.name === 'string' ? v.name : '',
      skus: Array.isArray(v?.skus) ? v.skus.filter(Boolean) : [],
    }))
    .filter((g) => g.skus.length > 0);
}

function pickInitialSku(groups, defaultSku) {
  if (defaultSku?.id) return defaultSku;
  for (const g of groups) {
    for (const s of g.skus) if (s?.isActive !== false) return s;
  }
  return groups[0]?.skus?.[0] ?? null;
}

/**
 * QuickAddSheet — opened from the ProductCard "Delivery" button.
 *
 * Logic:
 *  1. The card passes the mapped product (`product`). If `variants` is missing
 *     (PLP card shape), we fetch PDP detail by `slug` — only after the sheet
 *     opens (`open === true`).
 *  2. SKU selection: for a single-variant/sku product, defaultSku is auto-set.
 *     For multi-variant, buttons are blocked until the user selects.
 *  3. Submit: per the backend OpenAPI contract `{skuId, quantity}` (camelCase).
 *  4. State machine: idle → submitting → success/error. On success the sheet
 *     auto-closes after ~700ms; for "Buy now" we wait for invalidation
 *     and then navigate to /checkout.
 */
export default function QuickAddSheet({ product, productSlug, open, onClose }) {
  const router = useRouter();

  // Slug — backend fetches PDP by `slug` (`/storefront/products/{slug}`).
  // ProductCard passes the `productSlug` prop; if absent, product.slug;
  // last fallback is id (UUID) — but the storefront endpoint may return 404
  // when the UUID is treated as a slug, so a real slug is strongly preferred.
  const detailKey = useMemo(() => {
    const fromProp = typeof productSlug === 'string' ? productSlug.trim() : '';
    if (fromProp) return fromProp;
    if (typeof product?.slug === 'string' && product.slug.trim()) return product.slug.trim();
    if (product?.id != null) return String(product.id);
    return '';
  }, [product, productSlug]);

  // Forward-compat guard: if the list endpoints (for-you / trending / PLP)
  // already include `variants[]` in the response, no need to re-fetch the
  // PDP detail — avoids the N+1 antipattern. When the backend adds this
  // field, the fetch will stop automatically; otherwise the old behavior
  // is preserved.
  const hasVariantsFromCard = Array.isArray(product?.variants) && product.variants.length > 0;

  const {
    data: detailProduct,
    isFetching: isDetailFetching,
    isError: isDetailError,
  } = useGetProductByIdQuery(detailKey, {
    skip: !open || !detailKey || hasVariantsFromCard,
  });

  /**
   * Merge PLP card and PDP detail. Canonical (variants, attributes, inStock,
   * defaultSku) — from PDP; fallback to PLP card if price/image/name are
   * missing. This makes the UI render fully even when backend test data is
   * incomplete.
   */
  const merged = useMemo(() => {
    if (!detailProduct && !product) return null;
    if (!detailProduct) return product; // PDP still loading
    if (!product) return detailProduct;
    return {
      ...product,
      ...detailProduct,
      // Keep the PLP fallback when missing:
      price: detailProduct.price ?? product.price ?? null,
      oldPrice: detailProduct.oldPrice ?? product.oldPrice ?? null,
      image: detailProduct.image || product.image || '',
      images:
        Array.isArray(detailProduct.images) && detailProduct.images.length
          ? detailProduct.images
          : Array.isArray(product.images)
            ? product.images
            : [],
      name: detailProduct.name || product.name || product.title || '',
      // PLP card may not have `product.in_stock`; PDP has `inStock` (camelCase)
      // — `mapStorefrontProduct` copies it into `in_stock`.
      in_stock:
        typeof detailProduct.in_stock === 'boolean'
          ? detailProduct.in_stock
          : Boolean(product.in_stock),
    };
  }, [detailProduct, product]);

  const groups = useMemo(() => buildSkuGroups(merged), [merged]);
  const skusFlat = useMemo(() => groups.flatMap((g) => g.skus), [groups]);

  // User selection (if null — defaultSku is derived).
  // The sheet is mounted/unmounted by `ProductCard` via the
  // `isQuickAddOpen ? <Sheet/> : null` pattern, so we don't need to clear
  // state via an effect on close — a re-mount gives us fresh state automatically.
  const [userSelectedSkuId, setUserSelectedSkuId] = useState(null);
  const [submitState, setSubmitState] = useState(SUBMIT_STATE.IDLE);
  const [errorMsg, setErrorMsg] = useState('');

  const successTimerRef = useRef(null);

  const [addCartItem, { isLoading: isAdding }] = useAddCartItemMutation();

  useEffect(() => {
    return () => {
      if (successTimerRef.current) clearTimeout(successTimerRef.current);
    };
  }, []);

  // Effective SKU id: the user's pick if any, otherwise defaultSku.
  // Derived state — no useEffect, doesn't cause cascading renders.
  const effectiveSelectedSkuId = useMemo(() => {
    if (userSelectedSkuId) return userSelectedSkuId;
    const fallback = pickInitialSku(groups, merged?.defaultSku);
    return fallback?.id ?? null;
  }, [userSelectedSkuId, groups, merged]);

  const selectedSku = useMemo(
    () => skusFlat.find((s) => s?.id === effectiveSelectedSkuId) ?? null,
    [skusFlat, effectiveSelectedSkuId]
  );

  const handlePickSku = useCallback((skuId) => {
    setUserSelectedSkuId(skuId);
    setSubmitState((prev) => (prev === SUBMIT_STATE.ERROR ? SUBMIT_STATE.IDLE : prev));
    setErrorMsg('');
  }, []);

  const isMultiSku = skusFlat.length > 1;
  const requiresSelection = isMultiSku && !selectedSku;

  // Stock — no longer used to block the button, only informative.
  // Backend is authoritative: if truly out of stock, `POST /cart/items` will
  // reject with 422/409 and a specific error will be shown. This approach
  // prevents stale or incorrect seed data from permanently blocking the UI.
  const inStock = Boolean(merged?.in_stock) && (!selectedSku || selectedSku.isActive !== false);

  // 0 SKU — `POST /cart/items` can't satisfy `{skuId: required}`.
  // This is the only true blocking condition.
  const hasNoVariants = skusFlat.length === 0;

  // Price fallback chain — find a usable price from any source.
  // PDP `mapStorefrontProduct` returns rubles as `number`, while PLP
  // `mapProductCard` returns a pre-formatted "5 000 ₽" string.
  // `coalescePriceRub` accepts both shapes.
  const displayPriceRub = coalescePriceRub(
    selectedSku?.resolvedPrice,
    selectedSku?.price,
    merged?.price,
    // Even when `merged` has been switched to PDP detail, the original PLP
    // `product` keeps the string price — used as a last-line defense.
    product?.price
  );

  const displayCompareRub = coalescePriceRub(
    selectedSku?.compareAtPrice,
    merged?.oldPrice,
    product?.oldPrice
  );

  const productName =
    typeof merged?.name === 'string' && merged.name.trim()
      ? merged.name.trim()
      : typeof merged?.title === 'string'
        ? merged.title.trim()
        : '';

  const imageSrc =
    typeof merged?.image === 'string' && merged.image.trim()
      ? merged.image.trim()
      : Array.isArray(merged?.images) && merged.images[0]
        ? String(merged.images[0])
        : '';

  // Skeleton — while PDP is fetching and variants aren't there yet. The
  // next re-open (cache hit) opens immediately in full state.
  const isLoadingShell = isDetailFetching && (!merged?.variants || merged.variants.length === 0);

  // Dev-time diagnostics: print to console what's missing in the backend
  // response and the raw response. This makes test data issues quick to
  // identify. No logs in production.
  useEffect(() => {
    if (process.env.NODE_ENV === 'production') return;
    if (!open || isLoadingShell || !merged?.id) return;
    const issues = [];
    if (displayPriceRub == null) issues.push('price');
    if (skusFlat.length === 0) issues.push('variants[].skus[]');
    if (!merged?.in_stock) issues.push('inStock=false');
    if (!imageSrc) issues.push('image/media');
    if (issues.length) {
      console.groupCollapsed(
        `[QuickAddSheet] %c${merged.slug || merged.id}%c — missing: ${issues.join(', ')}`,
        'color:#c93a00;font-weight:bold',
        'color:inherit'
      );
      console.log('PDP detail (mapped):', merged);
      console.log('PDP raw response:', merged._raw);
      console.log('Skus flat:', skusFlat);
      console.groupEnd();
    }
  }, [open, isLoadingShell, merged, displayPriceRub, skusFlat, imageSrc]);

  // Block only when `skuId` is missing (or during an in-flight submit). The
  // `inStock` check was removed — we trust the backend as authoritative and
  // grant the user the right to "try clicking + receive a precise backend
  // error". This is standard pragmatic UX for Telegram Mini Apps.
  const submitDisabled = !selectedSku?.id || submitState === SUBMIT_STATE.SUBMITTING || isAdding;

  async function performAdd() {
    if (!selectedSku?.id) {
      setErrorMsg('Выберите вариант');
      setSubmitState(SUBMIT_STATE.ERROR);
      tgHaptic('error');
      return null;
    }
    setSubmitState(SUBMIT_STATE.SUBMITTING);
    setErrorMsg('');
    try {
      const result = await addCartItem({
        skuId: selectedSku.id,
        quantity: 1,
        // Extra meta for RTKQ optimistic patch — backend ignores it; only
        // `skuId` and `quantity` are sent in the mutation body. Used so the
        // Cart UI shows the correct item immediately.
        productId: merged?.id ?? null,
        variantId: selectedSku?.variantAttributes?.[0]?.attributeValueId ?? null,
        productName,
        variantLabel: skuLabel(selectedSku),
        imageUrl: imageSrc,
        priceRub: Number(displayPriceRub) || 0,
      }).unwrap();
      setSubmitState(SUBMIT_STATE.SUCCESS);
      tgHaptic('success');
      return result;
    } catch (err) {
      // Backend canonical envelope (Spec §3): `{error:{code,message,...}}`.
      // `normalizeApiError` picks the message by code; the BFF helper error
      // is also caught as a fallback.
      const norm = normalizeApiError(err);
      const msg =
        norm.code === 'TOKEN_EXPIRED' || norm.code === 'MISSING_TOKEN' || norm.status === 401
          ? 'Нужно войти, чтобы добавить в корзину'
          : norm.status === 409
            ? 'Товар уже в корзине'
            : norm.status === 422 || norm.status === 400
              ? humanizeApiError(err, 'Не удалось добавить — проверьте вариант')
              : humanizeApiError(err, 'Не удалось добавить в корзину');
      setErrorMsg(msg);
      setSubmitState(SUBMIT_STATE.ERROR);
      tgHaptic('error');
      return null;
    }
  }

  async function handleAddToCart() {
    const ok = await performAdd();
    if (!ok) return;
    // "Add to cart" — the sheet closes with a success animation, the page
    // doesn't change. The user stays on the PLP and can add more.
    successTimerRef.current = setTimeout(() => {
      onClose?.();
    }, SUCCESS_AUTO_CLOSE_MS);
  }

  async function handleBuyNow() {
    const ok = await performAdd();
    if (!ok) return;
    // "Buy now" — navigates to the cart (`/cart`), the sheet closes immediately.
    onClose?.();
    router.push(CART_ROUTE);
  }

  // Label hierarchy:
  //  1. Submit state (in-flight / success) — strongest priority
  //  2. No SKU (true block) — "No variants"
  //  3. Multi-SKU, none selected — "Select size"
  //  4. Default — "Add to cart"
  // We don't put stock in the label — if it's truly out of stock the
  // backend rejects on submit and we show the precise error via `errorMsg`.
  const footerLabelMain =
    submitState === SUBMIT_STATE.SUBMITTING
      ? 'Добавляем…'
      : submitState === SUBMIT_STATE.SUCCESS
        ? 'Добавлено ✓'
        : hasNoVariants
          ? 'Нет вариантов'
          : requiresSelection
            ? 'Выберите размер'
            : 'В корзину';

  return (
    <BottomSheet
      open={open}
      onClose={onClose}
      ariaLabel="Быстрое добавление в корзину"
      footer={
        <div className={styles.footerWrap}>
          {errorMsg ? (
            <div className={styles.errorRow} role="alert">
              {errorMsg}
            </div>
          ) : null}
          <div className={styles.actions}>
            <button
              type="button"
              className={styles.btnOutline}
              onClick={handleBuyNow}
              disabled={submitDisabled}
            >
              Купить сейчас
            </button>
            <button
              type="button"
              className={cx(
                styles.btnFilled,
                submitState === SUBMIT_STATE.SUCCESS && styles.btnSuccess
              )}
              onClick={handleAddToCart}
              disabled={submitDisabled}
            >
              {footerLabelMain}
            </button>
          </div>
        </div>
      }
    >
      {isLoadingShell ? (
        <div className={styles.skeleton} aria-busy="true">
          <div className={styles.skImage} />
          <div className={styles.skLines}>
            <div className={cx(styles.skLine, styles.skLine1)} />
            <div className={cx(styles.skLine, styles.skLine2)} />
          </div>
        </div>
      ) : isDetailError && !merged?.id ? (
        <div className={styles.emptyRow} role="alert">
          Не удалось загрузить товар
        </div>
      ) : (
        <>
          <div className={styles.productRow}>
            <div className={styles.productImage}>
              {imageSrc ? <img src={imageSrc} alt={productName} /> : null}
            </div>
            <div className={styles.productInfo}>
              <span className={styles.productName}>{productName}</span>
              <div className={styles.priceLine}>
                <span className={styles.productPrice}>{formatRub(displayPriceRub)}</span>
                {!inStock && !hasNoVariants ? (
                  <span className={styles.stockBadge} aria-label="Out of stock">
                    Нет в наличии
                  </span>
                ) : null}
                {displayCompareRub != null &&
                Number(displayCompareRub) > Number(displayPriceRub) ? (
                  <span className={styles.productCompare}>{formatRub(displayCompareRub)}</span>
                ) : null}
              </div>
            </div>
          </div>

          {groups.length > 0 && isMultiSku ? (
            <div className={styles.sizesSection}>
              {groups.map((g, gi) => (
                <div key={g.id || `g${gi}`} className={styles.variantGroup}>
                  {/* For multi-dimension (size + color) the group title is
                      shown; for a single dimension it's hidden (the flat
                      grid in the mockup). */}
                  {groups.length > 1 && g.name ? (
                    <div className={styles.variantTitle}>{g.name}</div>
                  ) : null}
                  <div className={styles.sizesRow}>
                    {g.skus.map((sku) => {
                      const isSelected = sku.id === effectiveSelectedSkuId;
                      const isDisabled = sku.isActive === false;
                      return (
                        <button
                          key={sku.id}
                          type="button"
                          disabled={isDisabled}
                          onClick={() => handlePickSku(sku.id)}
                          className={cx(
                            styles.sizeButton,
                            isDisabled
                              ? styles.sizeDisabled
                              : isSelected
                                ? styles.sizeSelected
                                : styles.sizeDefault
                          )}
                          aria-pressed={isSelected}
                        >
                          {skuLabel(sku)}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          ) : skusFlat.length === 1 && selectedSku ? (
            // Single-variant product — informative pill instead of a selector.
            // The "Add to cart" button works immediately with defaultSku.
            <div className={styles.singleSizeRow} aria-live="polite">
              <span className={styles.singleSizeBadge}>Размер: {skuLabel(selectedSku)}</span>
            </div>
          ) : null}
        </>
      )}
    </BottomSheet>
  );
}
