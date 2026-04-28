'use client';

import { cn } from '@/lib/utils';

const ERROR_MESSAGES = {
  UNAUTHORIZED: 'Необходима авторизация',
  PRICING_CONTEXT_NOT_FOUND: 'Контекст не найден',
  PRICING_CONTEXT_CODE_TAKEN: 'Контекст с таким кодом уже существует',
  PRICING_CONTEXT_FROZEN: 'Контекст заморожен — операция недоступна',
  PRICING_CONTEXT_VERSION_CONFLICT: 'Контекст был изменён другим пользователем. Обновите страницу',
  PRICING_CONTEXT_FIELD_IMMUTABLE: 'Это поле нельзя изменить после создания',
  PRICING_VARIABLE_NOT_FOUND: 'Переменная не найдена',
  PRICING_VARIABLE_CODE_TAKEN: 'Переменная с таким кодом уже существует',
  PRICING_VARIABLE_IN_USE: 'Переменная используется — сначала удалите все ссылки',
  PRICING_VARIABLE_SCOPE_IMMUTABLE: 'Scope нельзя изменить после создания',
  PRICING_VARIABLE_CODE_IMMUTABLE: 'Код нельзя изменить после создания',
  PRICING_VARIABLE_DATA_TYPE_IMMUTABLE: 'Тип данных нельзя изменить после создания',
  PRICING_FORMULA_VERSION_NOT_FOUND: 'Версия формулы не найдена',
  PRICING_FORMULA_VERSION_CONFLICT: 'Формула была изменена другим пользователем',
  PRICING_FORMULA_AST_INVALID: 'Невалидная структура формулы',
  BACKEND_UNAVAILABLE: 'Сервер недоступен. Попробуйте позже',
  SERVICE_UNAVAILABLE: 'Сервер недоступен. Попробуйте позже',
};

export function ErrorBanner({ error, onDismiss, className }) {
  if (!error) return null;

  const code = error?.data?.error?.code || error?.code || '';
  const serverMessage = error?.data?.error?.message || error?.message || '';
  const message = ERROR_MESSAGES[code] || serverMessage || 'Произошла ошибка';

  return (
    <div
      className={cn(
        'flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3',
        className,
      )}
      role="alert"
    >
      <svg className="mt-0.5 h-5 w-5 shrink-0 text-red-500" viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
      </svg>
      <p className="flex-1 text-sm text-red-700">{message}</p>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="shrink-0 text-red-400 transition-colors hover:text-red-600"
          aria-label="Закрыть"
        >
          <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </button>
      )}
    </div>
  );
}
