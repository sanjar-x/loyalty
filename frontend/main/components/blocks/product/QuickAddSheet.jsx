"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import cx from "clsx";

import BottomSheet from "@/components/ui/BottomSheet";
import {
  useGetProductByIdQuery,
  useAddCartItemMutation,
} from "@/lib/store/api";
import { normalizeApiError, humanizeApiError } from "@/lib/api/errors";

import styles from "./QuickAddSheet.module.css";

// Cart sahifasi ushbu loyihada `/trash` (legacy nom). `Купить сейчас` shu yerga
// olib boradi. `/checkout` esa pickup-point + buyurtma yakunlash sahifasi.
const CART_ROUTE = "/trash";

/**
 * Telegram Mini App haptic feedback. SDK mavjud bo'lmasa silently skip.
 *
 * Spec: Telegram WebApp `HapticFeedback.notificationOccurred(type)` —
 * `success` add muvaffaqiyatli, `error` xato bo'lganda.
 */
function tgHaptic(type) {
  try {
    const fn = window?.Telegram?.WebApp?.HapticFeedback?.notificationOccurred;
    if (typeof fn === "function") fn.call(window.Telegram.WebApp.HapticFeedback, type);
  } catch {
    // ignore — haptic best-effort
  }
}

const SUBMIT_STATE = Object.freeze({
  IDLE: "idle",
  SUBMITTING: "submitting",
  SUCCESS: "success",
  ERROR: "error",
});

const SUCCESS_AUTO_CLOSE_MS = 700;

/**
 * Pre-formatted rubles string'dan raqamni ekstrakt qilish.
 * "5 000 ₽" / "5,000.00 RUB" / "5000" → 5000
 *
 * `mapProductCard` (legacy PLP mapper) `price`'ni shu shaklda yaratadi.
 * Bizga `formatRub`'ga uzatishdan oldin number ga aylantirish kerak.
 */
function parseRubString(value) {
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value !== "string") return null;
  // Faqat raqamlar va decimal nuqtani saqlaymiz; mingdagi ajratuvchi (probel,
  // vergul) tashlanadi. "5 000.50" → "5000.50"
  const cleaned = value.replace(/[^\d.]/g, "");
  if (!cleaned) return null;
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : null;
}

/**
 * Bir nechta manbadan birinchi ishga yaroqli (>0) narxni qaytaradi.
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
  if (n == null || n <= 0) return "—";
  return `${Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ")} ₽`;
}

/**
 * SKU'ning displaylab labeli — `mapSku` allaqachon `label` field hisoblab beradi
 * (clothing size pattern: XS/S/M/L/XL, raqamli o'lchamlar yoki skuCode tail).
 */
function skuLabel(sku) {
  if (typeof sku?.label === "string" && sku.label.trim()) return sku.label;
  return sku?.id ? String(sku.id).slice(0, 4).toUpperCase() : "—";
}

/**
 * Mapped product (mapStorefrontProduct chiqishi) ichidagi `variants[].skus[]`'ni
 * tekis SKU ro'yxatiga aylantirib, har bir SKU uchun displaylab variant
 * gruppasini biriktiradi. Bitta variantli mahsulotda — gruppasiz tekis ro'yxat.
 */
function buildSkuGroups(product) {
  const variants = Array.isArray(product?.variants) ? product.variants : [];
  if (!variants.length) {
    const flat = Array.isArray(product?.skus) ? product.skus : [];
    return flat.length
      ? [{ id: null, name: "", skus: flat.filter(Boolean) }]
      : [];
  }
  return variants
    .map((v) => ({
      id: v?.id ?? null,
      name: typeof v?.name === "string" ? v.name : "",
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
 * QuickAddSheet — ProductCard'dagi "Доставка" tugmasi orqali ochiladi.
 *
 * Mintiq:
 *  1. Card mapped product'ni uzatadi (`product`). Agar `variants` yo'q bo'lsa
 *     (PLP card shape), `slug` orqali PDP detail fetch qilamiz — faqat sheet
 *     ochilgandan keyin (`open === true`).
 *  2. SKU tanlash: bitta variantli/skusli mahsulotda avtomatik defaultSku.
 *     Variantli holatda foydalanuvchi tanlamaguncha tugmalar bloklanadi.
 *  3. Submit: backend OpenAPI shartiga ko'ra `{skuId, quantity}` (camelCase).
 *  4. State machine: idle → submitting → success/error. Success'da sheet
 *     ~700ms keyin avto-yopiladi, "Купить сейчас"da invalidation kutib,
 *     keyin /checkout'ga o'tadi.
 */
export default function QuickAddSheet({ product, productSlug, open, onClose }) {
  const router = useRouter();

  // Slug — backend PDP ni `slug` orqali oladi (`/storefront/products/{slug}`).
  // ProductCard `productSlug` propini uzatadi; agar yo'q bo'lsa product.slug,
  // oxirgi fallback id (UUID) — ammo storefront endpoint UUID slug deb 404
  // qaytarishi mumkin, shuning uchun slug bo'lishi kuchli rad etilgan.
  const detailKey = useMemo(() => {
    const fromProp = typeof productSlug === "string" ? productSlug.trim() : "";
    if (fromProp) return fromProp;
    if (typeof product?.slug === "string" && product.slug.trim())
      return product.slug.trim();
    if (product?.id != null) return String(product.id);
    return "";
  }, [product, productSlug]);

  // Forward-compat guard: agar list endpoint (for-you / trending / PLP)
  // response'larida `variants[]` allaqachon bo'lsa, PDP detail'ni qayta
  // olishga hojat yo'q — N+1 antipattern oldini olamiz. Backend bu fielldni
  // qo'shganda fetch avtomatik to'xtaydi; bo'lmasa eski xulq saqlanadi.
  const hasVariantsFromCard =
    Array.isArray(product?.variants) && product.variants.length > 0;

  const {
    data: detailProduct,
    isFetching: isDetailFetching,
    isError: isDetailError,
  } = useGetProductByIdQuery(detailKey, {
    skip: !open || !detailKey || hasVariantsFromCard,
  });

  /**
   * PLP card va PDP detail'ni birlashtiramiz. Canonical (variants, attributes,
   * inStock, defaultSku) — PDP'dan; price/image/name yetishmasa PLP card'dan
   * fallback. Bu backend test data noto'liq bo'lganda ham UI to'liq ko'rinadi.
   */
  const merged = useMemo(() => {
    if (!detailProduct && !product) return null;
    if (!detailProduct) return product; // PDP hali yuklanmoqda
    if (!product) return detailProduct;
    return {
      ...product,
      ...detailProduct,
      // Yetishmasa PLP fallback'ni saqlash:
      price: detailProduct.price ?? product.price ?? null,
      oldPrice: detailProduct.oldPrice ?? product.oldPrice ?? null,
      image: detailProduct.image || product.image || "",
      images:
        Array.isArray(detailProduct.images) && detailProduct.images.length
          ? detailProduct.images
          : Array.isArray(product.images)
            ? product.images
            : [],
      name: detailProduct.name || product.name || product.title || "",
      // PLP card `product.in_stock` bo'lmasligi mumkin; PDP `inStock` (camelCase)
      // bo'ladi — `mapStorefrontProduct` `in_stock`'ga ko'chiradi.
      in_stock:
        typeof detailProduct.in_stock === "boolean"
          ? detailProduct.in_stock
          : Boolean(product.in_stock),
    };
  }, [detailProduct, product]);

  const groups = useMemo(() => buildSkuGroups(merged), [merged]);
  const skusFlat = useMemo(
    () => groups.flatMap((g) => g.skus),
    [groups],
  );

  // Foydalanuvchi tanlovi (null bo'lsa — defaultSku derived).
  // Sheet `ProductCard` tomonidan `quickAddOpen ? <Sheet/> : null` pattern bilan
  // mount/unmount qilinadi, shuning uchun yopilganda state effect orqali
  // tozalashga hojat yo'q — re-mount avtomatik fresh state beradi.
  const [userSelectedSkuId, setUserSelectedSkuId] = useState(null);
  const [submitState, setSubmitState] = useState(SUBMIT_STATE.IDLE);
  const [errorMsg, setErrorMsg] = useState("");

  const successTimerRef = useRef(null);

  const [addCartItem, { isLoading: isAdding }] = useAddCartItemMutation();

  useEffect(() => {
    return () => {
      if (successTimerRef.current) clearTimeout(successTimerRef.current);
    };
  }, []);

  // Effective SKU id: foydalanuvchi tanlasa shu, aks holda defaultSku.
  // Derived state — useEffect'siz, cascading render keltirib chiqarmaydi.
  const effectiveSelectedSkuId = useMemo(() => {
    if (userSelectedSkuId) return userSelectedSkuId;
    const fallback = pickInitialSku(groups, merged?.defaultSku);
    return fallback?.id ?? null;
  }, [userSelectedSkuId, groups, merged]);

  const selectedSku = useMemo(
    () => skusFlat.find((s) => s?.id === effectiveSelectedSkuId) ?? null,
    [skusFlat, effectiveSelectedSkuId],
  );

  const handlePickSku = useCallback(
    (skuId) => {
      setUserSelectedSkuId(skuId);
      setSubmitState((prev) =>
        prev === SUBMIT_STATE.ERROR ? SUBMIT_STATE.IDLE : prev,
      );
      setErrorMsg("");
    },
    [],
  );

  const isMultiSku = skusFlat.length > 1;
  const requiresSelection = isMultiSku && !selectedSku;

  // Stock — endi tugmani bloklash uchun ishlatilmaydi, faqat informativ.
  // Backend autoritative: haqiqatan ham sotuvda bo'lmasa `POST /cart/items`
  // 422/409 bilan rad etadi va aniq xato xabari ko'rinadi. Bu yondashuv stale
  // yoki noto'g'ri seed data UI'ni hammavaqt bloklab qo'yishini oldini oladi.
  const inStock =
    Boolean(merged?.in_stock) &&
    (!selectedSku || selectedSku.isActive !== false);

  // 0 SKU — `POST /cart/items` `{skuId: required}` ni qondirib bo'lmaydi.
  // Bu yagona haqiqiy bloklash sharti.
  const hasNoVariants = skusFlat.length === 0;

  // Price fallback chain — har qanday manbadan ishlaydigan narxni topish.
  // PDP `mapStorefrontProduct` rubles `number`, PLP `mapProductCard` esa
  // pre-formatted "5 000 ₽" string qaytaradi. `coalescePriceRub` ikkala
  // shaklni ham qabul qiladi.
  const displayPriceRub = coalescePriceRub(
    selectedSku?.resolvedPrice,
    selectedSku?.price,
    merged?.price,
    // `merged` PDP detail'ga almashtirilgan bo'lsa ham, asl PLP `product`
    // string narxni saqlab turadi — eng so'nggi himoya sifatida.
    product?.price,
  );

  const displayCompareRub = coalescePriceRub(
    selectedSku?.compareAtPrice,
    merged?.oldPrice,
    product?.oldPrice,
  );

  const productName =
    typeof merged?.name === "string" && merged.name.trim()
      ? merged.name.trim()
      : typeof merged?.title === "string"
        ? merged.title.trim()
        : "";

  const imageSrc =
    typeof merged?.image === "string" && merged.image.trim()
      ? merged.image.trim()
      : Array.isArray(merged?.images) && merged.images[0]
        ? String(merged.images[0])
        : "";

  // Skeleton — PDP fetch jarayonida va variants hali yo'q bo'lganda. Keyingi
  // re-open (cache hit) zudlik bilan to'liq holatda ochiladi.
  const isLoadingShell =
    isDetailFetching && (!merged?.variants || merged.variants.length === 0);

  // Dev-time diagnostika: backend javobida nimalar yetishmayotganini va
  // raw response'ni konsolga chiqaramiz. Bu test data muammolarini tezda
  // aniqlash uchun. Production'da log yo'q.
  useEffect(() => {
    if (process.env.NODE_ENV === "production") return;
    if (!open || isLoadingShell || !merged?.id) return;
    const issues = [];
    if (displayPriceRub == null) issues.push("price");
    if (skusFlat.length === 0) issues.push("variants[].skus[]");
    if (!merged?.in_stock) issues.push("inStock=false");
    if (!imageSrc) issues.push("image/media");
    if (issues.length) {
      console.groupCollapsed(
        `[QuickAddSheet] %c${merged.slug || merged.id}%c — missing: ${issues.join(", ")}`,
        "color:#c93a00;font-weight:bold",
        "color:inherit",
      );
      console.log("PDP detail (mapped):", merged);
      console.log("PDP raw response:", merged._raw);
      console.log("Skus flat:", skusFlat);
      console.groupEnd();
    }
  }, [open, isLoadingShell, merged, displayPriceRub, skusFlat, imageSrc]);

  // Faqat `skuId` yo'qligida (yoki jonli submit'da) bloklaymiz. `inStock`
  // tekshirish olib tashlandi — backend autoritative deb ishonamiz va
  // foydalanuvchiga "klikni urinib ko'rish + aniq backend xatosini olish"
  // huquqini beramiz. Bu Telegram Mini App'lar uchun standart pragmatik UX.
  const submitDisabled =
    !selectedSku?.id ||
    submitState === SUBMIT_STATE.SUBMITTING ||
    isAdding;

  async function performAdd() {
    if (!selectedSku?.id) {
      setErrorMsg("Выберите вариант");
      setSubmitState(SUBMIT_STATE.ERROR);
      tgHaptic("error");
      return null;
    }
    setSubmitState(SUBMIT_STATE.SUBMITTING);
    setErrorMsg("");
    try {
      const result = await addCartItem({
        skuId: selectedSku.id,
        quantity: 1,
        // RTKQ optimistic patch'i uchun qo'shimcha meta — backend'da ignore qilinadi,
        // mutation body'sida faqat `skuId` va `quantity` yuboriladi. Cart UI darhol
        // to'g'ri item ko'rsatishi uchun.
        productId: merged?.id ?? null,
        variantId: selectedSku?.variantAttributes?.[0]?.attributeValueId ?? null,
        productName,
        variantLabel: skuLabel(selectedSku),
        imageUrl: imageSrc,
        priceRub: Number(displayPriceRub) || 0,
      }).unwrap();
      setSubmitState(SUBMIT_STATE.SUCCESS);
      tgHaptic("success");
      return result;
    } catch (err) {
      // Backend canonical envelope (Spec §3): `{error:{code,message,...}}`.
      // `normalizeApiError` code'ga qarab xabarni tanlaydi, fallback uchun
      // BFF helper xatosi ham ushlanadi.
      const norm = normalizeApiError(err);
      const msg =
        norm.code === "TOKEN_EXPIRED" ||
        norm.code === "MISSING_TOKEN" ||
        norm.status === 401
          ? "Нужно войти, чтобы добавить в корзину"
          : norm.status === 409
            ? "Товар уже в корзине"
            : norm.status === 422 || norm.status === 400
              ? humanizeApiError(err, "Не удалось добавить — проверьте вариант")
              : humanizeApiError(err, "Не удалось добавить в корзину");
      setErrorMsg(msg);
      setSubmitState(SUBMIT_STATE.ERROR);
      tgHaptic("error");
      return null;
    }
  }

  async function handleAddToCart() {
    const ok = await performAdd();
    if (!ok) return;
    // "В корзину" — sheet success animatsiyasi bilan yopiladi, sahifa
    // o'zgarmaydi. Foydalanuvchi PLP'da qoladi va yana qo'shishi mumkin.
    successTimerRef.current = setTimeout(() => {
      onClose?.();
    }, SUCCESS_AUTO_CLOSE_MS);
  }

  async function handleBuyNow() {
    const ok = await performAdd();
    if (!ok) return;
    // "Купить сейчас" — savatga o'tkazadi (`/trash`), sheet darhol yopiladi.
    onClose?.();
    router.push(CART_ROUTE);
  }

  // Label ierarxiyasi:
  //  1. Submit holati (in-flight / success) — kuchli ustunlik
  //  2. SKU yo'q (haqiqiy blok) — "Нет вариантов"
  //  3. Multi-SKU, hech biri tanlanmagan — "Выберите размер"
  //  4. Default — "В корзину"
  // Stock'ni label'ga qo'ymaymiz — haqiqiy "Нет в наличии" bo'lsa backend
  // submit'da rad etadi va `errorMsg` orqali aniq ko'rsatamiz.
  const footerLabelMain =
    submitState === SUBMIT_STATE.SUBMITTING
      ? "Добавляем…"
      : submitState === SUBMIT_STATE.SUCCESS
        ? "Добавлено ✓"
        : hasNoVariants
          ? "Нет вариантов"
          : requiresSelection
            ? "Выберите размер"
            : "В корзину";

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
                submitState === SUBMIT_STATE.SUCCESS && styles.btnSuccess,
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
              {imageSrc ? (
                <img src={imageSrc} alt={productName} />
              ) : null}
            </div>
            <div className={styles.productInfo}>
              <span className={styles.productName}>{productName}</span>
              <div className={styles.priceLine}>
                <span className={styles.productPrice}>
                  {formatRub(displayPriceRub)}
                </span>
                {!inStock && !hasNoVariants ? (
                  <span className={styles.stockBadge} aria-label="Out of stock">
                    Нет в наличии
                  </span>
                ) : null}
                {displayCompareRub != null &&
                Number(displayCompareRub) > Number(displayPriceRub) ? (
                  <span className={styles.productCompare}>
                    {formatRub(displayCompareRub)}
                  </span>
                ) : null}
              </div>
            </div>
          </div>

          {groups.length > 0 && isMultiSku ? (
            <div className={styles.sizesSection}>
              {groups.map((g, gi) => (
                <div key={g.id || `g${gi}`} className={styles.variantGroup}>
                  {/* Multi-dimension (size + color) bo'lganda group title
                      ko'rinadi, yagona dimension'da yashiriladi (mockup'dagi
                      tekis grid). */}
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
                                : styles.sizeDefault,
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
            // Yagona variantli mahsulot — selektor o'rniga informativ pill.
            // Tugma "В корзину" defaultSku bilan darhol ishlaydi.
            <div className={styles.singleSizeRow} aria-live="polite">
              <span className={styles.singleSizeBadge}>
                Размер: {skuLabel(selectedSku)}
              </span>
            </div>
          ) : null}
        </>
      )}
    </BottomSheet>
  );
}
