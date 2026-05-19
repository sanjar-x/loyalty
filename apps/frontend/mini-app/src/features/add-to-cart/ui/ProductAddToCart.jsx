'use client';
import { useCallback, useRef, useState } from 'react';
import { cn as cx } from '@/shared/lib/ui-utils';
import styles from './ProductAddToCart.module.css';

const MIN_QTY = 1;
const MAX_QTY = 99;

const clampQty = (value) => {
  const n = Math.floor(Number(value));
  if (!Number.isFinite(n)) return MIN_QTY;
  return Math.max(MIN_QTY, Math.min(MAX_QTY, n));
};

export default function ProductAddToCart({
  onBuyNow,
  initialQuantity = 1,
  buyNowDisabled = false,
  buyNowDisabledHint = '',
}) {
  const [mode, setMode] = useState('simple');
  const [quantity, setQuantity] = useState(() => clampQty(initialQuantity));
  const [isBuying, setIsBuying] = useState(false);
  const incBtnRef = useRef(null);

  const dec = useCallback(() => {
    setQuantity((q) => clampQty(q - 1));
  }, []);

  const inc = useCallback(() => {
    setQuantity((q) => clampQty(q + 1));
  }, []);

  const handleAddToCart = useCallback(() => {
    setMode('pickQty');
    // Foydalanuvchi darhol miqdorni oshira olsin
    queueMicrotask(() => {
      incBtnRef.current?.focus();
    });
  }, []);

  const handleBuy = useCallback(async () => {
    if (isBuying) return;
    const qty = mode === 'simple' ? 1 : quantity;
    setIsBuying(true);
    try {
      await onBuyNow?.(qty);
    } finally {
      setIsBuying(false);
    }
  }, [isBuying, mode, onBuyNow, quantity]);

  const isMin = quantity <= MIN_QTY;
  const isMax = quantity >= MAX_QTY;

  return (
    <div className={cx(styles.c1, styles.tw1)}>
      <div className={styles.row}>
        <button
          type="button"
          className={styles.primary}
          onClick={handleBuy}
          disabled={isBuying || buyNowDisabled}
          aria-disabled={isBuying || buyNowDisabled}
          title={buyNowDisabled ? buyNowDisabledHint || undefined : undefined}
        >
          Купить сейчас
        </button>

        {mode === 'simple' ? (
          <button type="button" className={styles.secondary} onClick={handleAddToCart}>
            В корзину
          </button>
        ) : (
          <div className={styles.stepper} role="group" aria-label="Количество">
            <button
              type="button"
              className={styles.stepBtn}
              onClick={dec}
              disabled={isMin}
              aria-disabled={isMin}
              aria-label="Уменьшить количество"
            >
              −
            </button>
            <span className={styles.qty} aria-live="polite">
              {quantity}
            </span>
            <button
              ref={incBtnRef}
              type="button"
              className={styles.stepBtn}
              onClick={inc}
              disabled={isMax}
              aria-disabled={isMax}
              aria-label="Увеличить количество"
            >
              +
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
