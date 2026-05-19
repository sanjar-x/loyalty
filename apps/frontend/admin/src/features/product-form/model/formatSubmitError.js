/**
 * Audit 2.4 — single source of truth for submit-error copy.
 *
 * Pre-fix the same `code === '…'` ladder lived in two places inside
 * ProductDetailsForm.jsx — the `useEffect` toast on line 327 and the
 * inline error card around line 1037 — so adding a new submit-error
 * code (or wording change) silently risked drift. Extract once, call
 * from both call sites.
 *
 * Two callers, two slightly different copies (the inline card adds a
 * trailing reassurance for `MEDIA_PARTIAL_FAILURE`), so this returns
 * `{ short, long, isCancellation }` and lets the caller pick.
 */
export function formatSubmitError(err) {
  if (err == null) {
    return { short: '', long: '', isCancellation: false };
  }
  if (typeof err === 'string') {
    return { short: err, long: err, isCancellation: false };
  }

  const code = err.code;
  const fallback = err.message ? `Ошибка: ${err.message}` : 'Ошибка';

  switch (code) {
    case 'MEDIA_PARTIAL_FAILURE':
      return {
        short:
          'Некоторые изображения не загрузились. Вы можете отредактировать продукт позже.',
        long: `${err.message ?? 'Часть изображений не загрузилась.'} Вы можете отредактировать продукт позже.`,
        isCancellation: false,
      };
    case 'ZERO_SKUS':
      return {
        short: 'Не удалось сгенерировать SKU. Проверьте размеры.',
        long: 'Не удалось сгенерировать варианты (SKU). Проверьте выбранные атрибуты.',
        isCancellation: false,
      };
    case 'TIMEOUT': {
      const msg =
        'Сервер не отвечает. Проверьте соединение и попробуйте позже.';
      return { short: msg, long: msg, isCancellation: false };
    }
    case 'RATE_LIMITED': {
      const msg = 'Слишком много запросов. Подождите и попробуйте снова.';
      return { short: msg, long: msg, isCancellation: false };
    }
    case 'ABORTED_AFTER_CREATE': {
      const msg =
        'Операция отменена. Продукт сохранён как черновик — его можно открыть и продолжить.';
      return { short: msg, long: msg, isCancellation: true };
    }
    default:
      return { short: fallback, long: fallback, isCancellation: false };
  }
}
