export const PRODUCT_STATUS_LABELS = {
  draft: 'Черновик',
  enriching: 'Обогащение',
  ready_for_review: 'На модерации',
  published: 'Опубликован',
  archived: 'Архив',
};

/**
 * Visual tones for the FSM status badge (audit 1.7).
 *
 * Hex values are the WCAG-AA-passing pairs used by the rest of the
 * admin's pill components (status pills in Order detail, pricing
 * status badges). Keep in sync with `PRODUCT_STATUS_LABELS`.
 */
export const PRODUCT_STATUS_TONES = {
  draft: { bg: '#f4f3f1', fg: '#22252b' }, // app-card / app-text — neutral
  enriching: { bg: '#dbeafe', fg: '#1e40af' }, // sky — work in progress
  ready_for_review: { bg: '#fef3c7', fg: '#92400e' }, // amber — awaiting action
  published: { bg: '#dcfce7', fg: '#15803d' }, // emerald — live
  archived: { bg: '#e5e7eb', fg: '#374151' }, // slate — retired
};

export const PRODUCT_STATUS_TRANSITIONS = {
  draft: [{ target: 'enriching', label: 'Начать обогащение' }],
  enriching: [
    { target: 'draft', label: 'Вернуть в черновик' },
    { target: 'ready_for_review', label: 'На модерацию' },
  ],
  ready_for_review: [
    { target: 'enriching', label: 'Вернуть на обогащение' },
    { target: 'published', label: 'Опубликовать' },
  ],
  published: [{ target: 'archived', label: 'В архив' }],
  archived: [{ target: 'draft', label: 'Вернуть в черновик' }],
};
