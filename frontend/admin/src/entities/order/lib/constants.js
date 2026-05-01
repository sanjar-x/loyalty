export const STATUS_LABELS = {
  placed: 'Оформленные',
  in_transit: 'В пути',
  pickup_point: 'В пункте выдачи',
  canceled: 'Отмененные',
  received: 'Полученные',
};

export const STATUS_PILL_LABELS = {
  placed: 'Оформлен',
  in_transit: 'В пути',
  pickup_point: 'Готов к выдаче',
  canceled: 'Отменен',
  received: 'Получен',
};

export const REASON_FILTERS = [
  'not_for_sale',
  'release_refusal',
  'storage_expired',
];

export const REASON_FILTER_LABELS = {
  not_for_sale: 'Нет в продаже',
  release_refusal: 'Отказ в выпуске посылки',
  storage_expired: 'Срок хранения истёк',
};
