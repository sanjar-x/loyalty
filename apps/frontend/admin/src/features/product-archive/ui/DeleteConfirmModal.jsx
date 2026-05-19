'use client';

import { Modal } from '@/shared/ui/Modal';
import { productStyles as styles } from '@/entities/product';

export function DeleteConfirmModal({ product, onClose, onConfirm }) {
  return (
    <Modal
      open={Boolean(product)}
      onClose={onClose}
      title="Удалить товар?"
      titleId="delete-modal-title"
    >
      {product && (
        <>
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
        </>
      )}
    </Modal>
  );
}
