"use client";
import { cn } from "@/lib/format/cn";
import { useRouter } from "next/navigation";

import { useMemo, useState } from "react";

import styles from "./ProductCard.module.css";
import cx from "clsx";

export default function ProductCard({
  isPurchased,
  isViewed,
  product,
  onToggleFavorite,
  variant = "normal",
  hideFavoriteButton = false,
  showStars = false,
  starsInteractive = false,
  onRatingChange,
  onStarSelect,
}) {
  const isCompact = variant === "compact";
  const router = useRouter();

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
  const openProduct = () => {
    if (!product?.id) return;
    router.push(`/product/${product.id}`);
  };

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
          {typeof imgSrc === "string" && imgSrc.trim() ? (
            <img
              src={imgSrc}
              alt={product?.name ?? ""}
              className={styles.image}
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
            <div className={cx(styles.c1, styles.tw1)}>{fallbackText}</div>
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
            aria-pressed={product.isFavorite}
          >
            <img
              src={
                product.isFavorite
                  ? "/icons/global/active-heart.svg"
                  : "/icons/global/not-active-heart.svg"
              }
              alt={product.isFavorite ? "liked" : "not liked"}
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
      {variant === "normal" && (
        <img
          className={styles.dots}
          src="/icons/product/dots-mini-slider.svg"
          alt="dots"
        />
      )}

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

      {/* Кнопка доставки */}
      <button
        type="button"
        className={styles.deliveryBtn}
        style={{ display: `${isPurchased ? "none" : "block"}` }}
      >
        <span className={styles.deliveryText}>{deliveryLabel}</span>
      </button>
    </div>
  );
}
