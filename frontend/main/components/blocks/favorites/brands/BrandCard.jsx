"use client";
import React, { useMemo, useState } from "react";
import styles from "./BrandCard.module.css";
import cx from "clsx";

function ImgWithFallback({ src, fallbacks, alt, className }) {
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
export default function BrandCard({
  id,
  name,
  image,
  imageFallbacks,
  onClick,
}) {
  return (
    <li className={cx(styles.c1, styles.tw1)} onClick={() => onClick?.(id)}>
      {/* Левая часть: изображение и текст */}
      <div className={cx(styles.c2, styles.tw2)}>
        {/* Изображение бренда */}
        {image && (
          <div className={cx(styles.c3, styles.tw3)}>
            <ImgWithFallback
              src={image}
              fallbacks={imageFallbacks}
              alt={name}
              className={styles.c4}
            />
          </div>
        )}

        {/* Текст бренда */}
        <div className={cx(styles.c5, styles.tw4)}>
          <span className={styles.c6}>{name}</span>
          <span className={styles.c7}>Бренд</span>
        </div>
      </div>

      {/* Стрелка справа */}
      <img
        src="/icons/global/Wrap.svg"
        alt="arrow"
        className={cx(styles.c8, styles.tw5)}
      />
    </li>
  );
}
