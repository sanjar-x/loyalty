'use client';

import { pluralizeRu } from '@/shared/lib/utils';
import { productStyles as styles } from '@/entities/product';

/**
 * Audit 3.1 — `pending` flag wires the parent's `bulkActionPending`
 * state into the toolbar so concurrent clicks during a bulk action
 * are blocked at the UI layer (and the user gets a "Применяется…"
 * label) instead of stacking duplicate requests.
 *
 * Audit 3.4 — `role="region"` + `aria-label` tag the floating bar so
 * screen-reader users land on a named region when the bar appears.
 */
export function BulkBar({
  selectedCount,
  onArchive,
  onDelete,
  onClear,
  pending = false,
}) {
  const selectedLabel = `${selectedCount.toLocaleString('ru-RU')} ${pluralizeRu(selectedCount, 'товар', 'товара', 'товаров')}`;
  const archiveLabel = pending ? 'Применяется…' : 'В архив';
  const deleteLabel = pending ? 'Применяется…' : 'Удалить';

  return (
    <>
      <div
        className={styles.bulkBar}
        role="region"
        aria-label="Массовые действия с выбранными товарами"
        aria-busy={pending}
      >
        <div className={styles.bulkBarInner}>
          <div className={styles.bulkBarLeft}>
            <span className={styles.bulkBarCheck} aria-hidden="true">
              ✓
            </span>
            <span className={styles.bulkBarCount}>{selectedLabel}</span>
          </div>

          <div className={styles.bulkBarRight}>
            <button
              type="button"
              onClick={onArchive}
              disabled={pending}
              className={styles.bulkBarPrimary}
            >
              {archiveLabel}
            </button>
            <button
              type="button"
              onClick={onDelete}
              disabled={pending}
              className={styles.bulkBarDanger}
            >
              {deleteLabel}
            </button>
            <button
              type="button"
              onClick={onClear}
              disabled={pending}
              className={styles.bulkBarClose}
              aria-label="Снять выделение"
            >
              ×
            </button>
          </div>
        </div>
      </div>
      <div className={styles.bulkBarSpacer} />
    </>
  );
}
