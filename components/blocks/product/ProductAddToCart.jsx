"use client";
import React from "react";
import styles from "./ProductAddToCart.module.css";
import cx from "clsx";

export default function ProductAddToCart({
  onAddToCart,
  onBuyNow,
  quantity = 1,
  onQuantityChange,
}) {
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
          {onBuyNow ? "Купить сейчас" : "В корзину"}
        </button>

        {onQuantityChange ? (
          <div className={styles.stepper} role="group" aria-label="Количество">
            <button
              type="button"
              className={styles.stepBtn}
              onClick={dec}
              disabled={Number(quantity || 1) <= 1}
              aria-label="Уменьшить количество"
            >
              −
            </button>
            <span className={styles.qty} aria-live="polite">
              {Number(quantity || 1)}
            </span>
            <button
              type="button"
              className={styles.stepBtn}
              onClick={inc}
              aria-label="Увеличить количество"
            >
              +
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
