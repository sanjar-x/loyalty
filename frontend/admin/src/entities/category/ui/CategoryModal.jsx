'use client';

import { useState, useEffect } from 'react';
import { Modal } from '@/shared/ui/Modal';
import { apiClient } from '@/shared/api/client-fetch';
import { buildI18nPayload } from '@/shared/lib/utils';

const CATEGORY_ERROR_CODES = {
  CATEGORY_SLUG_CONFLICT:
    'Категория с таким slug уже существует на этом уровне',
  CATEGORY_MAX_DEPTH_REACHED: 'Достигнута максимальная глубина вложенности',
  CATEGORY_HAS_CHILDREN: 'Нельзя удалить категорию с дочерними элементами',
  CATEGORY_NOT_FOUND: 'Категория не найдена',
  VALIDATION_ERROR: 'Проверьте введённые данные',
  INSUFFICIENT_PERMISSIONS: 'Недостаточно прав',
};

function describeError(err, fallback) {
  return CATEGORY_ERROR_CODES[err?.code] ?? err?.message ?? fallback;
}

function generateSlug(name) {
  const slug = name
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-]/g, '');
  return slug;
}

export function CategoryModal({
  mode,
  parentId,
  category,
  onClose,
  onSuccess,
}) {
  const isEdit = mode === 'edit';
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [sortOrder, setSortOrder] = useState(0);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [slugTouched, setSlugTouched] = useState(false);

  useEffect(() => {
    if (isEdit && category) {
      setName(category.name);
      setSlug(category.slug);
      setSortOrder(category.sortOrder ?? 0);
      setSlugTouched(true);
    }
  }, [isEdit, category]);

  function handleNameChange(value) {
    setName(value);
    if (!slugTouched) {
      const auto = generateSlug(value);
      if (auto) setSlug(auto);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);

    const payload = isEdit
      ? { nameI18N: buildI18nPayload(name, ''), slug, sortOrder }
      : { nameI18N: buildI18nPayload(name, ''), slug, parentId, sortOrder };

    try {
      if (isEdit) {
        await apiClient.patch(`/api/categories/${category.id}`, payload);
      } else {
        await apiClient.post('/api/categories', payload);
      }
      onSuccess();
    } catch (err) {
      setError(describeError(err, 'Произошла ошибка'));
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete() {
    setError('');
    setLoading(true);

    try {
      await apiClient.del(`/api/categories/${category.id}`);
      onSuccess();
    } catch (err) {
      setError(describeError(err, 'Не удалось удалить'));
    } finally {
      setLoading(false);
      setConfirmDelete(false);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={isEdit ? 'Редактирование' : 'Новая категория'}
    >
      <form onSubmit={handleSubmit} className="mt-5 flex flex-col gap-4">
        {error && (
          <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">
            {error}
          </div>
        )}

        <label className="block">
          <span className="text-app-text mb-1 block text-sm font-medium">
            Название
          </span>
          <input
            type="text"
            required
            minLength={2}
            maxLength={255}
            value={name}
            onChange={(e) => handleNameChange(e.target.value)}
            className="border-app-border focus:border-app-text w-full rounded-lg border px-3 py-2.5 text-sm transition-colors outline-none"
            placeholder="Например: Одежда"
          />
        </label>

        <label className="block">
          <span className="text-app-text mb-1 block text-sm font-medium">
            Slug (URL)
          </span>
          <input
            type="text"
            required
            minLength={3}
            maxLength={255}
            pattern="^[a-z0-9-]+$"
            value={slug}
            onChange={(e) => {
              setSlug(e.target.value);
              setSlugTouched(true);
            }}
            className="border-app-border focus:border-app-text w-full rounded-lg border px-3 py-2.5 text-sm transition-colors outline-none"
            placeholder="naprimer-odezhda"
          />
        </label>

        <label className="block">
          <span className="text-app-text mb-1 block text-sm font-medium">
            Порядок сортировки
          </span>
          <input
            type="number"
            value={sortOrder}
            onChange={(e) => setSortOrder(Number(e.target.value))}
            className="border-app-border focus:border-app-text w-full rounded-lg border px-3 py-2.5 text-sm transition-colors outline-none"
          />
        </label>

        <button
          type="submit"
          disabled={loading}
          className="bg-app-text w-full rounded-lg px-4 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {loading ? 'Сохранение...' : 'Сохранить'}
        </button>

        {isEdit && (
          <div className="border-app-border border-t pt-4">
            {confirmDelete ? (
              <div className="flex flex-col gap-2">
                <p className="text-app-muted text-sm">Вы уверены?</p>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={handleDelete}
                    disabled={loading}
                    className="flex-1 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
                  >
                    Да, удалить
                  </button>
                  <button
                    type="button"
                    onClick={() => setConfirmDelete(false)}
                    className="border-app-border text-app-text hover:bg-app-card flex-1 rounded-lg border px-4 py-2 text-sm font-medium"
                  >
                    Отмена
                  </button>
                </div>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setConfirmDelete(true)}
                className="text-sm font-medium text-red-600 hover:text-red-700"
              >
                Удалить категорию
              </button>
            )}
          </div>
        )}
      </form>
    </Modal>
  );
}
