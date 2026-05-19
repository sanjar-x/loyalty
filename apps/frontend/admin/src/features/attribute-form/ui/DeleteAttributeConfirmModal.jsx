'use client';

import { useEffect, useState } from 'react';

import { useAttributeUsage, useDeleteAttribute } from '@/entities/attribute';

import { Modal } from '@/shared/ui/Modal';
import { i18n } from '@/shared/lib/utils';

/**
 * Confirmation modal that shows the attribute's usage analytics
 * (templates / categories / product count) before allowing the admin
 * to delete it. Backend rejects with `ATTRIBUTE_HAS_USAGES` 422 when
 * any of the counts are non-zero — we render the same picture
 * client-side so the user has a chance to redirect first.
 */
export function DeleteAttributeConfirmModal({ open, attribute, onClose }) {
  const [error, setError] = useState(null);
  const usageQuery = useAttributeUsage(attribute?.id, { enabled: open });
  const deleteMutation = useDeleteAttribute();

  useEffect(() => {
    if (open) {
      setError(null);
      deleteMutation.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, attribute?.id]);

  if (!attribute) return null;

  const usage = usageQuery.data;
  const totalUsage =
    (usage?.templateCount ?? 0) +
    (usage?.categoryCount ?? 0) +
    (usage?.productCount ?? 0);
  const blocked = totalUsage > 0;

  async function handleDelete() {
    if (deleteMutation.isPending || blocked) return;
    setError(null);
    try {
      await deleteMutation.mutateAsync(attribute.id);
      onClose?.();
    } catch (err) {
      setError(err?.message ?? 'Не удалось удалить атрибут');
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="md"
      title={`Удалить «${i18n(attribute.nameI18N, attribute.code)}»`}
    >
      <div className="mt-4 space-y-4">
        {usageQuery.isPending && (
          <p className="text-app-muted text-sm">Считаем использование…</p>
        )}

        {usage && (
          <div className="bg-app-card space-y-2 rounded-lg p-4 text-sm">
            <Row
              term="Шаблоны"
              count={usage.templateCount}
              items={usage.templates}
            />
            <Row
              term="Категории"
              count={usage.categoryCount}
              items={usage.categories}
            />
            <p>
              <span className="text-app-muted">Продукты:</span>{' '}
              <span className="text-app-text-dark font-medium">
                {usage.productCount}
              </span>
            </p>
          </div>
        )}

        {blocked && (
          // Audit 8.2 — pre-fix this block carried role="alert"
          // alongside the submit-error block below, so SR users heard
          // the same "deletion blocked" assertion announced twice for a
          // single user state. The advisory copy here is informational
          // (rendered before any submit attempt) — `role="status"` puts
          // it on a polite live region and lets the actual submit error
          // own the assertive `role="alert"` channel.
          <div
            role="status"
            className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800"
          >
            Атрибут используется. Backend вернёт 422 на удаление — сначала
            отвяжите его от шаблонов / категорий / продуктов.
          </div>
        )}

        {error && (
          <div
            role="alert"
            className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700"
          >
            {error}
          </div>
        )}

        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={deleteMutation.isPending}
            className="text-app-muted hover:text-app-text-dark px-3 py-2 text-sm font-medium"
          >
            Отмена
          </button>
          <button
            type="button"
            onClick={handleDelete}
            disabled={deleteMutation.isPending || blocked}
            className="bg-app-danger rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {deleteMutation.isPending ? 'Удаляем…' : 'Удалить'}
          </button>
        </div>
      </div>
    </Modal>
  );
}

function Row({ term, count, items = [] }) {
  return (
    <div>
      <p>
        <span className="text-app-muted">{term}:</span>{' '}
        <span className="text-app-text-dark font-medium">{count}</span>
      </p>
      {count > 0 && items?.length > 0 && (
        <ul className="text-app-muted mt-1 list-disc pl-5 text-xs">
          {items.slice(0, 5).map((item) => (
            <li key={item.id}>
              {i18n(item.nameI18N, item.code ?? item.fullSlug)}
            </li>
          ))}
          {items.length > 5 && <li>…и ещё {items.length - 5}</li>}
        </ul>
      )}
    </div>
  );
}
