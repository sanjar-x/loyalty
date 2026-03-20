"use client";
import React from "react";
import styles from "./ProductAddToCart.module.css";
import cx from "clsx";

interface ProductAddToCartProps {
  onAddToCart?: () => void;
  onBuyNow?: () => void;
  quantity?: number;
  onQuantityChange?: (quantity: number) => void;
}

export default function ProductAddToCart({
  onAddToCart,
  onBuyNow,
  quantity = 1,
  onQuantityChange,
}: ProductAddToCartProps) {
  // Keep API stable; default quantity is 1 for now.
  React.useEffect(() => {
    onQuantityChange?.(quantity);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const dec = () => {
    if (!onQuantityChange) return;
    onQuantityChange(Math.max(1, Number(quantity || 1) - 1));
  };

  const inc = () => {
    if (!onQuantityChange) return;
    onQuantityChange(Number(quantity || 1) + 1);
  };

  return (
    <div className={cx(styles.c1, styles.tw1)}>
      <div className={styles.row}>
        <button
          onClick={onBuyNow ?? onAddToCart}
          className={styles.primary}
          type="button"
        >
          {onBuyNow ? "\u041a\u0443\u043f\u0438\u0442\u044c \u0441\u0435\u0439\u0447\u0430\u0441" : "\u0412 \u043a\u043e\u0440\u0437\u0438\u043d\u0443"}
        </button>

        {onQuantityChange ? (
          <div className={styles.stepper} role="group" aria-label="\u041a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e">
            <button
              type="button"
              className={styles.stepBtn}
              onClick={dec}
              disabled={Number(quantity || 1) <= 1}
              aria-label="\u0423\u043c\u0435\u043d\u044c\u0448\u0438\u0442\u044c \u043a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e"
            >
              {"\u2212"}
            </button>
            <span className={styles.qty} aria-live="polite">
              {Number(quantity || 1)}
            </span>
            <button
              type="button"
              className={styles.stepBtn}
              onClick={inc}
              aria-label="\u0423\u0432\u0435\u043b\u0438\u0447\u0438\u0442\u044c \u043a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e"
            >
              +
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
