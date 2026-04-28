'use client';

import { useEffect } from 'react';
import styles from './products.module.css';

export function DeleteConfirmModal({ product, onClose, onConfirm }) {
  useEffect(() => {
    if (!product) {
      return undefined;
    }

    const previousOverflow = document.body.style.overflow;
    const previousPaddingRight = document.body.style.paddingRight;
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
    document.body.style.overflow = 'hidden';
    if (scrollbarWidth > 0) {
      document.body.style.paddingRight = `${scrollbarWidth}px`;
    }

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose();
      }
    }

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      document.body.style.paddingRight = previousPaddingRight;
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [product, onClose]);

  if (!product) {
    return null;
  }

  return (
    <div className={styles.modalOverlay} role="presentation" onClick={onClose}>
      <div
        className={styles.modalCard}
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <p id="delete-modal-title" className={styles.modalTitle}>
          Удалить товар?
        </p>
        <p className={styles.modalText}>
          Товар будет удалён. Это действие нельзя отменить.
        </p>
        <div className={styles.modalProductBox}>
          <p className={styles.modalProductLabel}>Товар</p>
          <p className={styles.modalProductTitle}>{product.title}</p>
        </div>
        <div className={styles.modalActions}>
          <button
            type="button"
            onClick={onClose}
            className={styles.modalSecondaryButton}
          >
            Отмена
          </button>
          <button
            type="button"
            onClick={() => onConfirm(product.id)}
            className={styles.modalDangerButton}
          >
            Удалить
          </button>
        </div>
      </div>
    </div>
  );
}
