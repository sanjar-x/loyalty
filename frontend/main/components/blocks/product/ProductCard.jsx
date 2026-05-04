"use client";
import { cn } from "@/lib/format/cn";
import Image from "next/image";
import { useRouter } from "next/navigation";

import { memo, useCallback, useMemo, useState } from "react";

import styles from "./ProductCard.module.css";
import cx from "clsx";
import QuickAddSheet from "./QuickAddSheet";
import ProductImageCarousel from "./ProductImageCarousel";

export default memo(function ProductCard({
  isPurchased,
  isViewed,
  product,
  onToggleFavorite,
  favoriteItemIds,
  variant = "normal",
  hideFavoriteButton = false,
  showStars = false,
  starsInteractive = false,
  onRatingChange,
  onStarSelect,
}) {
  const isFavorite = favoriteItemIds
    ? favoriteItemIds.has(product?.id)
    : Boolean(product?.isFavorite);
  const [quickAddOpen, setQuickAddOpen] = useState(false);
  const [carouselIdx, setCarouselIdx] = useState(0);
  const isCompact = variant === "compact";
  const router = useRouter();

  const productSlug =
    typeof product?.slug === "string" && product.slug.trim()
      ? product.slug.trim()
      : product?.id != null
        ? String(product.id)
        : "";

  const productHref = productSlug
    ? `/product/${encodeURIComponent(productSlug)}`
    : "";

  // Client-side navigation — Next.js Router PDP sahifasini in-memory
  // qo'shadi. Back button instant ishlaydi, RTK cache va Zustand state
  // saqlanadi. PDP data tap'dan keyin PDP page mount'da fetch qilinadi
  // (~600-800ms loading state); list-page'larda hech qanday qo'shimcha
  // product detail fetch yo'q (N+1 antipattern oldini olish).
  const openProduct = useCallback(() => {
    if (!productHref) return;
    router.push(productHref);
  }, [router, productHref]);

  const fallbackText =
    typeof product?.name === "string" && product.name.trim()
      ? product.name.trim().slice(0, 1).toUpperCase()
      : "";

  const imageFallbacks = useMemo(() => {
    const raw = product?.imageFallbacks;
    return Array.isArray(raw)
      ? raw.filter((x) => typeof x === "string" && x.trim())
      : [];
  }, [product?.imageFallbacks]);

  const gallery = useMemo(() => {
    const raw = product && product.gallery;
    const list = Array.isArray(raw)
      ? raw.filter((x) => typeof x === "string" && x.trim())
      : [];
    return Array.from(new Set(list));
  }, [product]);

  const baseSrc = typeof product?.image === "string" ? product.image : "";
  const productKey = `${String(product?.id ?? "")}|${baseSrc}|${imageFallbacks.join("|")}`;

  const initialImgSrc = typeof product?.image === "string" ? product.image : "";

  const [imgState, setImgState] = useState(() => ({
    productKey,
    imgSrc: initialImgSrc,
    fallbackIdx: 0,
  }));

  const effectiveImgState =
    imgState?.productKey === productKey
      ? imgState
      : { productKey, imgSrc: initialImgSrc, fallbackIdx: 0 };

  const imgSrc = effectiveImgState.imgSrc;
  const fallbackIdx = effectiveImgState.fallbackIdx;

  const installmentText = (() => {
    if (!product) return "";
    if (typeof product.installment === "string" && product.installment.trim()) {
      return product.installment.trim();
    }

    const raw = String(product.price || "");
    const digits = raw.replace(/[^0-9]/g, "");
    if (!digits) return "";
    const total = Number(digits);
    if (!Number.isFinite(total) || total <= 0) return "";
    const per = Math.ceil(total / 4);
    const formatted = per.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
    return `4 × ${formatted} ₽ в сплит`;
  })();

  const rubIndex = installmentText.indexOf("₽");

  const pricePart = installmentText.slice(0, rubIndex + 1);
  const splitPart = installmentText.slice(rubIndex + 1).trim();

  const deliveryLabel =
    (typeof product?.deliveryDate === "string" &&
      product.deliveryDate.trim()) ||
    (typeof product?.deliveryText === "string" &&
      product.deliveryText.trim()) ||
    "Доставка";

  const currentRating = (() => {
    const n = Number(product?.rating ?? 0);
    if (!Number.isFinite(n)) return 0;
    return Math.max(0, Math.min(5, Math.trunc(n)));
  })();

  return (
    <div
      className={`${cn(styles.root, isCompact ? styles.compact : styles.normal)} ${isViewed ? `${styles.isViewed}` : ""} ${isPurchased ? `${styles.isPurchased}` : ""} `}
      onClick={openProduct}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          openProduct();
        }
      }}
    >
      <div
        className={cn(
          styles.imageWrap,
          isCompact ? styles.imageWrapCompact : styles.imageWrapNormal,
        )}
      >
        <div className={styles.center}>
          {gallery.length > 1 ? (
            <ProductImageCarousel
              key={gallery.join("|")}
              images={gallery}
              alt={product?.name ?? ""}
              sizes="(max-width: 768px) 50vw, 200px"
              onActiveChange={setCarouselIdx}
            />
          ) : typeof imgSrc === "string" && imgSrc.trim() ? (
            <Image
              src={imgSrc}
              alt={product?.name ?? ""}
              className={styles.image}
              fill
              sizes="(max-width: 768px) 50vw, 200px"
              loading="lazy"
              onError={() => {
                setImgState((prev) => {
                  const current =
                    prev?.productKey === productKey
                      ? prev
                      : { productKey, imgSrc: initialImgSrc, fallbackIdx: 0 };

                  const next = imageFallbacks[current.fallbackIdx];
                  if (
                    typeof next === "string" &&
                    next &&
                    next !== current.imgSrc
                  ) {
                    return {
                      productKey,
                      imgSrc: next,
                      fallbackIdx: current.fallbackIdx + 1,
                    };
                  }

                  return {
                    productKey,
                    imgSrc: "",
                    fallbackIdx: current.fallbackIdx,
                  };
                });
              }}
            />
          ) : (
            <div className={cx(styles.c1, styles.tw1)}>
              <Image
                src="/img/placeholder-product.svg"
                alt={product?.name ?? "Product"}
                className={styles.image}
                fill
                sizes="(max-width: 768px) 50vw, 200px"
                loading="lazy"
              />
            </div>
          )}
        </div>

        {showStars && !isCompact ? (
          <div className={styles.starsRow} aria-label="Оценка" role="group">
            {Array.from({ length: 5 }).map((_, i) => {
              const value = i + 1;
              const isActive = value <= currentRating;

              if (!starsInteractive) {
                return (
                  <img
                    key={i}
                    src="/icons/product/Star.svg"
                    alt=""
                    className={isActive ? styles.starActive : styles.star}
                    loading="lazy"
                    aria-hidden="true"
                  />
                );
              }

              return (
                <button
                  key={i}
                  type="button"
                  className={styles.starBtn}
                  aria-label={`Оценить на ${value}`}
                  aria-pressed={isActive}
                  onClick={(e) => {
                    e.stopPropagation();
                    onRatingChange?.(product?.id, value);
                    onStarSelect?.(product?.id, value);
                  }}
                >
                  <img
                    src="/icons/product/Star.svg"
                    alt=""
                    className={isActive ? styles.starActive : styles.star}
                    loading="lazy"
                    aria-hidden="true"
                  />
                </button>
              );
            })}
          </div>
        ) : null}

        {!hideFavoriteButton ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onToggleFavorite(product.id);
            }}
            type="button"
            className={styles.favoriteBtn}
            aria-pressed={isFavorite}
          >
            <img
              src={
                isFavorite
                  ? "/icons/global/active-heart.svg"
                  : "/icons/global/not-active-heart.svg"
              }
              alt={isFavorite ? "liked" : "not liked"}
              className={styles.favoriteIcon}
            />
          </button>
        ) : (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onToggleFavorite(product.id);
            }}
            type="button"
            className={styles.favoriteBtn}
            aria-label="Добавить в избранное"
          >
            <img
              src="/icons/global/not-active-heart.svg"
              alt="Добавить в избранное"
              className={styles.favoriteIcon}
            />
          </button>
        )}
      </div>
      {variant === "normal" && gallery.length <= 1 && (
        <div className={styles.dotsSpacer} aria-hidden="true" />
      )}
      {variant === "normal" && gallery.length > 1 && (() => {
        const total = gallery.length;
        const maxDots = 5;
        const visible = Math.min(total, maxDots);
        const activeVisibleIdx = total <= maxDots
          ? carouselIdx
          : Math.min(
              maxDots - 1,
              Math.max(0, carouselIdx - Math.max(0, total - maxDots)),
            );
        const w = (visible - 1) * 8 + 6;
        return (
          <div className={styles.dots} aria-hidden="true">
            <svg
              width={w}
              height="6"
              viewBox={`0 0 ${w} 6`}
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              {Array.from({ length: visible }).map((_, i) => {
                const isActive = i === activeVisibleIdx;
                return (
                  <circle
                    key={i}
                    cx={3 + i * 8}
                    cy={3}
                    r={isActive ? 2.58 : 1.55}
                    fill={isActive ? "#7E7E7E" : "#CECDCD"}
                  />
                );
              })}
            </svg>
          </div>
        );
      })()}

      <div className={cn(styles.meta, isCompact && styles.metaCompact)}>
        <div className={styles.price}>{product.price}</div>
        {installmentText ? (
          <div className={styles.installment}>
            <span>{pricePart}</span>
            &nbsp;
            <span>{splitPart}</span>
          </div>
        ) : null}
        <div className={styles.name}>{product.name}</div>
      </div>

      {/* Кнопка доставки — открывает быстрое добавление */}
      <button
        type="button"
        className={styles.deliveryBtn}
        style={{ display: `${isPurchased ? "none" : "flex"}` }}
        onClick={(e) => {
          e.stopPropagation();
          setQuickAddOpen(true);
        }}
      >
        <span className={styles.deliveryText}>{deliveryLabel}</span>
      </button>

      {/* Sheet'ni faqat birinchi ochilgandan keyin mount qilamiz — har bir
          card ichida portal va RTKQ subscription'ni avans qilmasligi uchun. */}
      {quickAddOpen ? (
        <QuickAddSheet
          product={product}
          productSlug={productSlug}
          open={quickAddOpen}
          onClose={() => setQuickAddOpen(false)}
        />
      ) : null}
    </div>
  );
}, (prev, next) => {
  if (prev.product !== next.product) return false;
  if (prev.variant !== next.variant) return false;
  if (prev.hideFavoriteButton !== next.hideFavoriteButton) return false;
  if (prev.showStars !== next.showStars) return false;
  if (prev.starsInteractive !== next.starsInteractive) return false;
  if (prev.isPurchased !== next.isPurchased) return false;
  if (prev.isViewed !== next.isViewed) return false;
  if (prev.onToggleFavorite !== next.onToggleFavorite) return false;
  if (prev.onRatingChange !== next.onRatingChange) return false;
  if (prev.onStarSelect !== next.onStarSelect) return false;
  // Gallery o'zgarishini ham tekshirish (reference tengligi)
  if (prev.product?.gallery !== next.product?.gallery) return false;
  // Only re-render if THIS card's favorite status changed
  const prevFav = prev.favoriteItemIds ? prev.favoriteItemIds.has(prev.product?.id) : Boolean(prev.product?.isFavorite);
  const nextFav = next.favoriteItemIds ? next.favoriteItemIds.has(next.product?.id) : Boolean(next.product?.isFavorite);
  if (prevFav !== nextFav) return false;
  return true;
})
