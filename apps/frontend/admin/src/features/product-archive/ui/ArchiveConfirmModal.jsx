'use client';

import { Modal } from '@/shared/ui/Modal';
import { productStyles as styles } from '@/entities/product';

export function ArchiveConfirmModal({ product, onClose, onConfirm }) {
  return (
    <Modal
      open={Boolean(product)}
      onClose={onClose}
      title="Переместить товар в архив?"
      titleId="archive-modal-title"
    >
      {product && (
        <>
          <p className={styles.modalText}>
            Товар исчезнет из активного списка и будет доступен во вкладке
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
        </>
      )}
    </Modal>
  );
}
