'use client';

import { i18n } from '@/lib/utils';

export function CompletenessPanel({ completeness }) {
  if (!completeness) {
    return (
      <div className="rounded-xl border border-[#dfdfe2] bg-white p-4">
        <p className="text-sm text-[#878b93]">Загрузка...</p>
      </div>
    );
  }

  const { isComplete, totalRequired, filledRequired, totalRecommended, filledRecommended, missingRequired, missingRecommended } = completeness;

  return (
    <div className="rounded-xl border border-[#dfdfe2] bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-[#22252b]">Полнота заполнения</h3>
        <span className="text-sm text-[#878b93]">
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
              <li key={attr.attributeId} className="flex items-center gap-1.5 text-sm text-[#22252b]">
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
              <li key={attr.attributeId} className="flex items-center gap-1.5 text-sm text-[#878b93]">
                <span className="text-amber-500">*</span>
                {i18n(attr.nameI18N)}
              </li>
            ))}
          </ul>
        </div>
      )}

      {!isComplete && totalRecommended > 0 && (
        <p className="mt-2 text-xs text-[#878b93]">
          Рекомендуемые: {filledRecommended}/{totalRecommended}
        </p>
      )}
    </div>
  );
}
