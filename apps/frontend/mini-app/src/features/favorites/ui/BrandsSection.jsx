'use client';
import React from 'react';
import FavoriteBrandCard from './FavoriteBrandCard';
import Link from 'next/link';

import { useDragToScroll } from '@/shared/lib/hooks';
import styles from './BrandsSection.module.css';
import { cn as cx } from '@/shared/lib/ui-utils';

export default function BrandsSection({ brands, onToggleFavorite }) {
  // Desktop swipe — touch'da hook avtomatik o'chiriladi.
  const carouselRef = useDragToScroll();

  return (
    <div className={styles.c1}>
      <div className={styles.c2}>
        <h2 className={styles.c3}>Бренды</h2>

        <Link href="/favorites/brands">
          <span className={cx(styles.c4, styles.tw1)}>
            все
            <img className={cx(styles.c5, styles.tw2)} src="/icons/global/arrow.svg" alt="arrow" />
          </span>
        </Link>
      </div>
      <div ref={carouselRef} className={cx(styles.c6, styles.tw3, 'scrollbar-hide')}>
        {brands.map((brand) => (
          <FavoriteBrandCard
            key={brand.id}
            name={brand.name}
            image={brand.image}
            imageFallbacks={brand.imageFallbacks}
            isFavorite={brand.isFavorite}
            onToggleFavorite={() => onToggleFavorite?.(brand.id)}
          />
        ))}
      </div>
    </div>
  );
}
