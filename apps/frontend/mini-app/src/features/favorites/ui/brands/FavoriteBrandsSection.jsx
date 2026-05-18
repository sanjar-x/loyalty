'use client';
import React from 'react';
import CatalogBrandCard from './CatalogBrandCard';
import styles from './FavoriteBrandsSection.module.css';
import { cn as cx } from '@/shared/lib/ui-utils';

export default function FavoriteBrandsSection({ brands, onBrandClick }) {
  return (
    <div className={styles.c1}>
      <h2 className={styles.c2}>Избранные</h2>
      <ul className={cx(styles.c3, styles.tw1)}>
        {brands.map((brand) => (
          <CatalogBrandCard
            key={brand.id}
            id={brand.id}
            name={brand.name}
            image={brand.image}
            imageFallbacks={brand.imageFallbacks}
            onClick={onBrandClick}
          />
        ))}
      </ul>
    </div>
  );
}
