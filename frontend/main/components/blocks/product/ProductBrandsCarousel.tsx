"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import cx from "clsx";
import styles from "./ProductBrandsCarousel.module.css";

interface Brand {
  id?: string | number;
  slug?: string;
  name: string;
  image: string;
  imageFallbacks?: string[];
  href?: string;
  subtitle?: string;
}

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
  const [idx, setIdx] = useState<number>(0);
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

interface ProductBrandsCarouselProps {
  brands?: Brand[];
}

export default function ProductBrandsCarousel({ brands = [] }: ProductBrandsCarouselProps) {
  if (!Array.isArray(brands) || brands.length === 0) return null;

  return (
    <section className={styles.root} aria-label="\u0411\u0440\u0435\u043d\u0434\u044b">
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
                <span className={styles.sub}>{brand.subtitle ?? "\u0411\u0440\u0435\u043d\u0434"}</span>
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
