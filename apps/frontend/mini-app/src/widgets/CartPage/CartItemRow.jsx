'use client';

import { cn } from '@/shared/lib/ui-utils';
import { formatRub } from '@/shared/lib/money';

import styles from './page.module.css';

/**
 * Sprint 6: extracted from app/cart/page.jsx (~133 lines of inline JSX).
 * A single cart item: photo/placeholder + name + size/article + price +
 * delivery chip + favorite/remove + qty stepper.
 *
 * Pure presentation: the parent owns state (selectedIds/favoriteItemIds)
 * and actions (toggleSelect, removeOne, setQuantity, toggleProductFavorite).
 */
export default function CartItemRow({
  item,
  isSelected,
  isFavorite,
  onToggleSelect,
  onToggleFavorite,
  onRemove,
  onSetQuantity,
}) {
  return (
    <div className={styles.c15}>
      <div className={cn(styles.c16, styles.tw6)}>
        <div className={cn(styles.c17, styles.tw7)}>
          {item.image ? (
            <img src={item.image} alt={item.name} className={styles.c18} loading="lazy" />
          ) : (
            <div className={styles.imagePlaceholder} aria-label="Изображение недоступно">
              <span className={styles.imagePlaceholderLetter}>
                {item.name ? item.name.trim().charAt(0).toUpperCase() : '?'}
              </span>
            </div>
          )}
        </div>

        <div className={cn(styles.c19, styles.tw8)}>
          <div className={cn(styles.c20, styles.tw9)}>
            <div className={cn(styles.c21, styles.tw10)}>
              <div className={styles.c22}>
                {item.isOrphaned ? 'Товар недоступен' : item.name}
              </div>
              {item.isOrphaned ? (
                <div className={styles.orphanWarning}>Снят с продажи — удалите из корзины</div>
              ) : null}
              {!item.isOrphaned && item.shippingText?.trim() ? (
                <div className={styles.c23}>{item.shippingText}</div>
              ) : null}
              <div className={styles.c24}>
                {item.size ? (
                  <p>
                    Размер: <span className={styles.c24Value}>{item.size}</span>
                  </p>
                ) : null}
                {item.article ? (
                  <p>
                    Артикул: <span className={styles.c24Value}>{item.article}</span>
                  </p>
                ) : null}
              </div>
            </div>

            <input
              type="checkbox"
              checked={isSelected}
              onChange={onToggleSelect}
              className={cn(styles.c25, 'lm-checkbox')}
            />
          </div>

          <div className={styles.c26}>{formatRub(item.priceRub)}</div>

          {!item.isOrphaned && item.deliveryText ? (
            <div className={cn(styles.c27, styles.tw11)}>
              <span className={cn(styles.c28, styles.tw12)} aria-hidden="true" />
              <span>{item.deliveryText}</span>
            </div>
          ) : null}

          <div className={styles.c29}>
            <div className={cn(styles.c30, styles.tw13)}>
              <button
                type="button"
                onClick={onToggleFavorite}
                aria-label={isFavorite ? 'Убрать из избранного' : 'Добавить в избранное'}
                className={styles.iconButton}
              >
                <img
                  src={
                    isFavorite
                      ? '/icons/global/active-heart.svg'
                      : '/icons/global/not-active-heart.svg'
                  }
                  alt=""
                  className={cn(styles.c31, styles.tw14)}
                />
              </button>

              <button
                type="button"
                onClick={onRemove}
                aria-label="Удалить"
                className={styles.iconButton}
              >
                <img
                  src="/icons/global/xicon.svg"
                  alt="Удалить"
                  className={cn(styles.c32, styles.tw15)}
                />
              </button>
            </div>

            <div className={cn(styles.c33, styles.tw16)}>
              <button
                type="button"
                onClick={() => onSetQuantity(item.quantity - 1)}
                className={styles.c34}
              >
                −
              </button>
              <span className={cn(styles.c35, styles.tw17)}>{item.quantity}</span>
              <button
                type="button"
                onClick={() => onSetQuantity(item.quantity + 1)}
                className={styles.c36}
              >
                +
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
