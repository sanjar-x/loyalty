"use client";
import React from "react";
import BrandCard from "./BrandCard";
import styles from './FavoriteBrandsSection.module.css';
import cx from 'clsx';

export default function FavoriteBrandsSection({
  brands,
  onBrandClick,
}) {
  return (
    <div className={styles.c1}>
      <h2 className={styles.c2}>
        Избранные
      </h2>
      <ul className={cx(styles.c3, styles.tw1)}>
        {brands.map((brand) => (
          <BrandCard
            key={brand.id}
            id={brand.id}
            name={brand.name}
            image={brand.image}
            onClick={onBrandClick}
          />
        ))}
      </ul>
    </div>
  );
}
