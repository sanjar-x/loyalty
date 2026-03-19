"use client";
import React from "react";
import Link from "next/link";
import Image from "next/image";
import styles from "./ProductInfo.module.css";
import cx from "clsx";

export default function ProductInfo({
  productName,
  brand,
  brandLink,
  images = [],
  currentImageIndex = 0,
  onImageChange,
  theme = "light",
  showThumbnails = true,
}) {
  const isDark = theme === "dark";

  return (
    <div className={cx(styles.c1, isDark && styles.dark)}>
      {/* Бренд */}
      {brandLink ? (
        <Link
          href={brandLink}
          className={cx(styles.c2, isDark && styles.brandDark)}
        >
          {brand}
        </Link>
      ) : (
        <h1 className={cx(styles.c2, isDark && styles.brandDark)}>{brand}</h1>
      )}

      {/* Название товара */}
      {productName ? (
        <p className={cx(styles.c4, isDark && styles.nameDark)}>
          {productName}
        </p>
      ) : null}

      {showThumbnails && images.length > 1 && (
        <div className={cx(styles.c5, "scrollbar-hide")}>
          <div className={cx(styles.c6, styles.tw1)}>
            {images.map((image, index) => (
              <button
                key={index}
                type="button"
                onClick={() => onImageChange?.(index)}
                className={cx(
                  styles.thumbButton,
                  index === currentImageIndex
                    ? styles.thumbActive
                    : styles.thumbInactive,
                )}
                style={{ width: "83px", height: "83px" }}
              >
                <Image
                  src={image}
                  alt={`Миниатюра ${index + 1}`}
                  fill
                  className={styles.c7}
                  sizes="80px"
                />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
