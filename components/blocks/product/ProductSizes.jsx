"use client";
import React, { useState } from "react";
import Image from "next/image";
import styles from "./ProductSizes.module.css";
import cx from "clsx";
import BottomSheet from "@/components/ui/BottomSheet";

export default function ProductSizes({
  sizes,
  availableSizes = [],
  onSizeSelect,
  sizeChart,
  theme = "light",
  hideTitle = false,
}) {
  const [selectedSize, setSelectedSize] = useState(null);
  const [isSizeChartOpen, setIsSizeChartOpen] = useState(false);
  const isDark = theme === "dark";

  const resolvedSizeChart = Array.isArray(sizeChart)
    ? sizeChart
    : (Array.isArray(sizes) ? sizes : []).map((size) => {
        const key = String(size).toUpperCase();
        const preset = {
          XS: { chest: 110, length: 66, sleeve: 74 },
          S: { chest: 114, length: 68, sleeve: 75 },
          M: { chest: 118, length: 69, sleeve: 77 },
          L: { chest: 120, length: 72, sleeve: 78 },
          XL: { chest: 124, length: 74, sleeve: 79 },
          XXL: { chest: 128, length: 76, sleeve: 81 },
        };

        return {
          size,
          ...(preset[key] || { chest: "—", length: "—", sleeve: "—" }),
        };
      });

  const handleSizeClick = (size) => {
    const isAvailable =
      availableSizes.length === 0 || availableSizes.includes(size);
    if (isAvailable) {
      setSelectedSize(size);
      onSizeSelect?.(size);
    }
  };

  const isSizeAvailable = (size) => {
    return availableSizes.length === 0 || availableSizes.includes(size);
  };

  return (
    <div className={cx(styles.c1, isDark && styles.dark)}>
      <div className={cx(styles.c2, styles.tw1)}>
        <div className={cx(styles.c3, styles.tw2)}>
          {!hideTitle ? <h3 className={styles.c4}>Размер - EU</h3> : null}
        </div>

        <div
          className={cx(styles.c5, styles.tw3, isDark && styles.sizesRowDark)}
        >
          {sizes.map((size) => {
            const isAvailable = isSizeAvailable(size);
            const isSelected = selectedSize === size;

            return (
              <button
                key={size}
                onClick={() => handleSizeClick(size)}
                disabled={!isAvailable}
                className={cx(
                  styles.sizeButton,
                  isDark && styles.sizeButtonDark,
                  !isAvailable
                    ? styles.sizeDisabled
                    : isSelected
                      ? styles.sizeSelected
                      : styles.sizeDefault,
                )}
                style={{ fontFamily: "Inter" }}
              >
                {size}
              </button>
            );
          })}
        </div>

        {/* Кнопка таблицы размеров */}
        <button
          type="button"
          className={styles.c6}
          onClick={() => setIsSizeChartOpen(true)}
          aria-haspopup="dialog"
          aria-expanded={isSizeChartOpen}
        >
          <span>Таблица размеров</span>

          <Image
            src="/icons/global/Wrap.svg"
            alt=""
            width={3.38}
            height={5.91}
            className={cx(styles.c7, styles.tw5)}
          />
        </button>

        <BottomSheet
          open={isSizeChartOpen}
          onClose={() => setIsSizeChartOpen(false)}
          title="Размерная сетка"
          ariaLabel="Размерная сетка"
        >
          <div className={styles.sheetBody}>
            <img
              src="/img/sizes.png"
              alt="sizes"
              style={{ width: "100%", height: "auto" }}
            />

            <p className={styles.sizeHint}>
              (Из-за различий в методах измерения единица измерения плоскости СМ
              может иметь погрешность в 2–3 см)
            </p>
          </div>
        </BottomSheet>
      </div>
    </div>
  );
}
