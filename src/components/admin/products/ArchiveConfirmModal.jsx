'use client';

import { useEffect } from 'react';
import styles from './products.module.css';

export function ArchiveConfirmModal({ product, onClose, onConfirm }) {
  useEffect(() => {
    if (!product) {
      return undefined;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose();
      }
    }

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
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
        aria-labelledby="archive-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <p id="archive-modal-title" className={styles.modalTitle}>
          Переместить товар в архив?
        </p>
        <p className={styles.modalText}>
          Товар исчезнет из активного списка и будет доступен во вкладке{' '}
          «Архив».
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
            className={styles.modalPrimaryButton}
          >
            В архив
          </button>
        </div>
      </div>
    </div>
  );
}
