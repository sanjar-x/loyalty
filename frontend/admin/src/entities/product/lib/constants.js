export const PRODUCT_STATUS_LABELS = {
  draft: 'Черновик',
  enriching: 'Обогащение',
  ready_for_review: 'На модерации',
  published: 'Опубликован',
  archived: 'Архив',
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
