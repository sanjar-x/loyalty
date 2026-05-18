'use client';

import React, { useMemo, useState } from 'react';
import { cn as cx } from '@/shared/lib/ui-utils';

import { useDragToScroll } from '@/shared/lib/hooks';
import styles from './ProductBrandsCarousel.module.css';

function ImgWithFallback({ src, fallbacks, alt, className }) {
  const sources = useMemo(
    () => [src, ...(Array.isArray(fallbacks) ? fallbacks : [])].filter(Boolean),
    [src, fallbacks]
  );
  const [idx, setIdx] = useState(0);
  const current = sources[idx] || '';

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
  // Desktop swipe — touch'da hook avtomatik o'chiriladi.
  const rowRef = useDragToScroll();
  if (!Array.isArray(brands) || brands.length === 0) return null;

  return (
    <section className={styles.root} aria-label="Бренды">
      <div ref={rowRef} className={cx(styles.row, 'scrollbar-hide')}>
        {brands.map((brand) => (
          <div
            key={brand.id ?? brand.slug ?? brand.name}
            role="link"
            tabIndex={0}
            className={styles.card}
            style={{ cursor: 'pointer' }}
            onClick={() => {
              if (brand.href) window.location.assign(brand.href);
            }}
            onKeyDown={(e) => {
              if ((e.key === 'Enter' || e.key === ' ') && brand.href) {
                window.location.assign(brand.href);
              }
            }}
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
                <span className={styles.sub}>{brand.subtitle ?? 'Бренд'}</span>
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
          </div>
        ))}
      </div>
    </section>
  );
}
