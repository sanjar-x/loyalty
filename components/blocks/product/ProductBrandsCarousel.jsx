"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import cx from "clsx";
import styles from "./ProductBrandsCarousel.module.css";

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

export default function ProductBrandsCarousel({ brands = [] }) {
  if (!Array.isArray(brands) || brands.length === 0) return null;

  return (
    <section className={styles.root} aria-label="Бренды">
      <div className={cx(styles.row, "scrollbar-hide")}>
        {brands.map((brand) => (
          <Link
            key={brand.id ?? brand.slug ?? brand.name}
            href={brand.href ?? "#"}
            className={styles.card}
          >
            <div className={styles.left}>
              <span className={styles.logoWrap} aria-hidden="true">
                <ImgWithFallback
                  src={brand.image}
                  fallbacks={brand.imageFallbacks}
                  alt=""
                  className={styles.logo}
                />
              </span>
              <div className={styles.text}>
                <span className={styles.name}>{brand.name}</span>
                <span className={styles.sub}>{brand.subtitle ?? "Бренд"}</span>
              </div>
            </div>

            <span className={styles.right} aria-hidden="true">
              <img
                src="/icons/global/arrowBlack.svg"
                alt=""
                width={7}
                height={11}
                className={styles.arrow}
              />
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}
