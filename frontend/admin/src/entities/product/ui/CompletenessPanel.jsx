'use client';

import { i18n } from '@/shared/lib/utils';

export function CompletenessPanel({ completeness }) {
  if (!completeness) {
    return (
      <div className="border-app-border rounded-xl border bg-white p-4">
        <p className="text-app-muted text-sm">Загрузка...</p>
      </div>
    );
  }

  const {
    isComplete,
    totalRequired,
    filledRequired,
    totalRecommended,
    filledRecommended,
    missingRequired,
    missingRecommended,
  } = completeness;

  return (
    <div className="border-app-border rounded-xl border bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-app-text text-sm font-semibold">
          Полнота заполнения
        </h3>
        <span className="text-app-muted text-sm">
          {filledRequired}/{totalRequired}
        </span>
      </div>

      {isComplete && (
        <p className="mb-3 text-sm text-green-600">
          &#10003; Все обязательные атрибуты заполнены
        </p>
      )}

      {missingRequired?.length > 0 && (
        <div className="mb-3">
          <p className="mb-1 text-xs font-medium text-red-600">
            Обязательные (не заполнено: {missingRequired.length})
          </p>
          <ul className="space-y-0.5">
            {missingRequired.map((attr) => (
              <li
                key={attr.attributeId}
                className="text-app-text flex items-center gap-1.5 text-sm"
              >
                <span className="text-red-500">*</span>
                {i18n(attr.nameI18N)}
              </li>
            ))}
          </ul>
        </div>
      )}

      {missingRecommended?.length > 0 && (
        <div>
          <p className="mb-1 text-xs font-medium text-amber-600">
            Рекомендуемые (не заполнено: {missingRecommended.length})
          </p>
          <ul className="space-y-0.5">
            {missingRecommended.map((attr) => (
              <li
                key={attr.attributeId}
                className="text-app-muted flex items-center gap-1.5 text-sm"
              >
                <span className="text-amber-500">*</span>
                {i18n(attr.nameI18N)}
              </li>
            ))}
          </ul>
        </div>
      )}

      {!isComplete && totalRecommended > 0 && (
        <p className="text-app-muted mt-2 text-xs">
          Рекомендуемые: {filledRecommended}/{totalRecommended}
        </p>
      )}
    </div>
  );
}
