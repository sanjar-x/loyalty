"use client";
import React, { useState } from "react";
import Image from "next/image";
import styles from "./ProductSizes.module.css";
import cx from "clsx";
import BottomSheet from "@/components/ui/BottomSheet";

interface SizeChartEntry {
  size: string;
  chest?: number | string;
  length?: number | string;
  sleeve?: number | string;
}

interface ProductSizesProps {
  sizes: string[];
  availableSizes?: string[];
  onSizeSelect?: (size: string) => void;
  sizeChart?: SizeChartEntry[];
  theme?: "light" | "dark";
  hideTitle?: boolean;
}

export default function ProductSizes({
  sizes,
  availableSizes = [],
  onSizeSelect,
  sizeChart,
  theme = "light",
  hideTitle = false,
}: ProductSizesProps) {
  const [selectedSize, setSelectedSize] = useState<string | null>(null);
  const [isSizeChartOpen, setIsSizeChartOpen] = useState<boolean>(false);
  const isDark = theme === "dark";

  const resolvedSizeChart: SizeChartEntry[] = Array.isArray(sizeChart)
    ? sizeChart
    : (Array.isArray(sizes) ? sizes : []).map((size) => {
        const key = String(size).toUpperCase();
        const preset: Record<string, { chest: number; length: number; sleeve: number }> = {
          XS: { chest: 110, length: 66, sleeve: 74 },
          S: { chest: 114, length: 68, sleeve: 75 },
          M: { chest: 118, length: 69, sleeve: 77 },
          L: { chest: 120, length: 72, sleeve: 78 },
          XL: { chest: 124, length: 74, sleeve: 79 },
          XXL: { chest: 128, length: 76, sleeve: 81 },
        };

        return {
          size,
          ...(preset[key] || { chest: "\u2014", length: "\u2014", sleeve: "\u2014" }),
        };
      });

  const handleSizeClick = (size: string) => {
    const isAvailable =
      availableSizes.length === 0 || availableSizes.includes(size);
    if (isAvailable) {
      setSelectedSize(size);
      onSizeSelect?.(size);
    }
  };

  const isSizeAvailable = (size: string): boolean => {
    return availableSizes.length === 0 || availableSizes.includes(size);
  };

  return (
    <div className={cx(styles.c1, isDark && styles.dark)}>
      <div className={cx(styles.c2, styles.tw1)}>
        <div className={cx(styles.c3, styles.tw2)}>
          {!hideTitle ? <h3 className={styles.c4}>\u0420\u0430\u0437\u043c\u0435\u0440 - EU</h3> : null}
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
          <span>\u0422\u0430\u0431\u043b\u0438\u0446\u0430 \u0440\u0430\u0437\u043c\u0435\u0440\u043e\u0432</span>

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
          title="\u0420\u0430\u0437\u043c\u0435\u0440\u043d\u0430\u044f \u0441\u0435\u0442\u043a\u0430"
          ariaLabel="\u0420\u0430\u0437\u043c\u0435\u0440\u043d\u0430\u044f \u0441\u0435\u0442\u043a\u0430"
        >
          <div className={styles.sheetBody}>
            <img
              src="/img/sizes.png"
              alt="sizes"
              style={{ width: "100%", height: "auto" }}
            />

            <p className={styles.sizeHint}>
              (\u0418\u0437-\u0437\u0430 \u0440\u0430\u0437\u043b\u0438\u0447\u0438\u0439 \u0432 \u043c\u0435\u0442\u043e\u0434\u0430\u0445 \u0438\u0437\u043c\u0435\u0440\u0435\u043d\u0438\u044f \u0435\u0434\u0438\u043d\u0438\u0446\u0430 \u0438\u0437\u043c\u0435\u0440\u0435\u043d\u0438\u044f \u043f\u043b\u043e\u0441\u043a\u043e\u0441\u0442\u0438 \u0421\u041c
              \u043c\u043e\u0436\u0435\u0442 \u0438\u043c\u0435\u0442\u044c \u043f\u043e\u0433\u0440\u0435\u0448\u043d\u043e\u0441\u0442\u044c \u0432 2\u20133 \u0441\u043c)
            </p>
          </div>
        </BottomSheet>
      </div>
    </div>
  );
}
