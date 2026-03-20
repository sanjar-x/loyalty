"use client";
import React from "react";
import BrandCard from "./BrandCard";
import Link from "next/link";
import styles from "./BrandsSection.module.css";
import cx from "clsx";

interface Brand {
  id: string | number;
  name: string;
  image?: string;
  imageFallbacks?: string[];
  isFavorite?: boolean;
}

interface BrandsSectionProps {
  brands: Brand[];
  onToggleFavorite?: (id: string | number) => void;
}

export default function BrandsSection({ brands, onToggleFavorite }: BrandsSectionProps) {
  return (
    <div className={styles.c1}>
      <div className={styles.c2}>
        <h2 className={styles.c3}>Бренды</h2>

        <Link href="/favorites/brands">
          <span className={cx(styles.c4, styles.tw1)}>
            все
            <img
              className={cx(styles.c5, styles.tw2)}
              src="/icons/global/arrow.svg"
              alt="arrow"
            />
          </span>
        </Link>
      </div>
      <div className={cx(styles.c6, styles.tw3, "scrollbar-hide")}>
        {brands.map((brand) => (
          <BrandCard
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
