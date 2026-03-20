"use client";
import React, { useMemo, useState } from "react";
import styles from "./BrandCard.module.css";
import cx from "clsx";

interface ImgWithFallbackProps {
  src: string;
  fallbacks?: string[];
  alt: string;
  className?: string;
}

function ImgWithFallback({ src, fallbacks, alt, className }: ImgWithFallbackProps) {
  const sources = useMemo(
    () => [src, ...(Array.isArray(fallbacks) ? fallbacks : [])].filter(Boolean),
    [src, fallbacks],
  );
  const [idx, setIdx] = useState(0);
  const current = sources[idx] || "";

  if (!current) return null;

  return (
    <img
      src={current}
      alt={alt}
      className={className}
      onError={() => {
        if (idx < sources.length - 1) setIdx(idx + 1);
      }}
    />
  );
}

interface BrandCardProps {
  name: string;
  image?: string;
  imageFallbacks?: string[];
  isFavorite?: boolean;
  onToggleFavorite?: () => void;
}

export default function BrandCard({
  name,
  image,
  imageFallbacks,
  isFavorite = false,
  onToggleFavorite,
}: BrandCardProps) {
  return (
    <div className={cx(styles.c1, styles.tw1)}>
      {/* Изображение бренда */}
      {image && (
        <div className={cx(styles.c2, styles.tw2)}>
          <ImgWithFallback
            src={image}
            fallbacks={imageFallbacks}
            alt={name}
            className={styles.c3}
          />
        </div>
      )}

      {/* Текст бренда */}
      <div className={cx(styles.c4, styles.tw3)}>
        <span className={styles.c5}>{name}</span>
        <span className={styles.c6}>Бренд</span>
      </div>

      {/* Кнопка избранного */}
      <button
        onClick={onToggleFavorite}
        className={cx(styles.c7, styles.tw4)}
        aria-pressed={isFavorite}
      >
        <img
          src={
            isFavorite
              ? "/icons/global/active-heart.svg"
              : "/icons/global/not-active-heart.svg"
          }
          alt={isFavorite ? "Удалить из избранного" : "Добавить в избранное"}
          className={styles.c8}
        />
      </button>
    </div>
  );
}
