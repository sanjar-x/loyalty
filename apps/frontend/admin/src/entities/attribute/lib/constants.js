// Mirrors of the backend `Attribute` enums (post-CAT-006). Kept in
// lock-step with `openapi/backend.json` — when backend grows the enum,
// add the value here AND extend the corresponding labels map.

export const ATTRIBUTE_DATA_TYPES = ['string', 'integer', 'float', 'boolean'];

export const ATTRIBUTE_UI_TYPES = [
  'text_button',
  'color_swatch',
  'dropdown',
  'checkbox',
  'range_slider',
];

export const ATTRIBUTE_LEVELS = ['product', 'variant'];

export const REQUIREMENT_LEVELS = ['required', 'recommended', 'optional'];

export const DATA_TYPE_LABELS = {
  string: 'Строка',
  integer: 'Целое число',
  float: 'Число с точкой',
  boolean: 'Да/нет',
};

export const UI_TYPE_LABELS = {
  text_button: 'Кнопки с текстом',
  color_swatch: 'Цветовые свотчи',
  dropdown: 'Выпадающий список',
  checkbox: 'Чекбокс',
  range_slider: 'Слайдер диапазона',
};

export const LEVEL_LABELS = {
  product: 'Продукт',
  variant: 'Вариант',
};

export const REQUIREMENT_LEVEL_LABELS = {
  required: 'Обязательно',
  recommended: 'Рекомендуется',
  optional: 'Опционально',
};

// Friendly defaults for the create modal — matches backend defaults so
// a "minimal" payload reproduces the Python-side experience.
export const ATTRIBUTE_CREATE_DEFAULTS = Object.freeze({
  dataType: 'string',
  uiType: 'dropdown',
  level: 'product',
  isDictionary: true,
  isFilterable: false,
  isSearchable: false,
  searchWeight: 5,
  isComparable: false,
  isVisibleOnCard: false,
});
