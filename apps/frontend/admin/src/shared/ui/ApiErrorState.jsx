import Link from 'next/link';

/**
 * Generic API error renderer for full-page failure states.
 *
 * Audit 1.3 / 4.3 — pre-fix the product detail and edit pages collapsed
 * 403/404/5xx into a single "Не удалось загрузить" line with a retry
 * button that didn't make sense for permission denials and missing
 * resources. Now we discriminate by `error.status`:
 *
 *  • 403 → "Нет доступа", no retry, offer the home link.
 *  • 404 → "Не найдено", no retry, offer the home link.
 *  • 5xx (502/503/504/etc) → "Сервер недоступен", show retry.
 *  • other / unknown → generic message + retry, plus the raw code so the
 *    user can quote it to support.
 *
 * Whenever the error envelope includes a `requestId` we surface it as
 * monospace muted text so support can pick it up from screenshots.
 */
function classifyError(error) {
  const status = error?.status ?? 0;
  if (status === 403) {
    return {
      title: 'Нет доступа',
      body: 'У вас недостаточно прав на просмотр этой страницы.',
      retryable: false,
    };
  }
  if (status === 404) {
    return {
      title: 'Не найдено',
      body: 'Запись удалена или никогда не существовала.',
      retryable: false,
    };
  }
  if (status >= 500 && status <= 599) {
    return {
      title: 'Сервер недоступен',
      body:
        error?.message ??
        'Не получилось дозвониться до бэкенда. Повторите чуть позже.',
      retryable: true,
    };
  }
  return {
    title: 'Ошибка',
    body: error?.message ?? 'Что-то пошло не так.',
    retryable: true,
  };
}

export function ApiErrorState({
  error,
  onRetry,
  homeHref = '/admin',
  homeLabel = 'На главную',
}) {
  const { title, body, retryable } = classifyError(error);
  const requestId = error?.details?.requestId;

  return (
    <div
      role="alert"
      className="flex flex-col items-center gap-3 px-4 py-12 text-center"
    >
      <p className="text-app-text-dark text-base font-semibold">{title}</p>
      <p className="text-app-muted max-w-md text-sm">{body}</p>

      {requestId && (
        <p className="text-app-muted font-mono text-xs">
          requestId: {requestId}
        </p>
      )}

      <div className="mt-2 flex items-center gap-3">
        {retryable && onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="text-app-text text-sm font-medium underline hover:no-underline"
          >
            Попробовать снова
          </button>
        )}
        {!retryable && (
          <Link
            href={homeHref}
            className="text-app-text text-sm font-medium underline hover:no-underline"
          >
            {homeLabel}
          </Link>
        )}
      </div>
    </div>
  );
}
