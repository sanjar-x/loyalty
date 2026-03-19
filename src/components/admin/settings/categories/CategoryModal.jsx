'use client';

import { useState, useEffect } from 'react';
import { Modal } from '@/components/ui/Modal';

const ERROR_MESSAGES = {
  CATEGORY_SLUG_CONFLICT:
    'Категория с таким slug уже существует на этом уровне',
  CATEGORY_MAX_DEPTH_REACHED: 'Достигнута максимальная глубина вложенности',
  CATEGORY_HAS_CHILDREN: 'Нельзя удалить категорию с дочерними элементами',
  CATEGORY_NOT_FOUND: 'Категория не найдена',
  VALIDATION_ERROR: 'Проверьте введённые данные',
  INSUFFICIENT_PERMISSIONS: 'Недостаточно прав',
};

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

    try {
      const url = isEdit ? `/api/categories/${category.id}` : '/api/categories';
      const method = isEdit ? 'PATCH' : 'POST';

      const body = isEdit
        ? { name, slug, sortOrder }
        : { name, slug, parentId, sortOrder };

      const res = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: JSON.stringify(body),
      });

      if (res.ok) {
        onSuccess();
        return;
      }

      const data = await res.json().catch(() => null);
      const code = data?.error?.code;
      setError(
        ERROR_MESSAGES[code] ?? data?.error?.message ?? 'Произошла ошибка',
      );
    } catch {
      setError('Нет связи с сервером');
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete() {
    setError('');
    setLoading(true);

    try {
      const res = await fetch(`/api/categories/${category.id}`, {
        method: 'DELETE',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      });

      if (res.ok) {
        onSuccess();
        return;
      }

      const data = await res.json().catch(() => null);
      const code = data?.error?.code;
      setError(
        ERROR_MESSAGES[code] ?? data?.error?.message ?? 'Не удалось удалить',
      );
    } catch {
      setError('Нет связи с сервером');
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
          <span className="mb-1 block text-sm font-medium text-[#22252b]">
            Название
          </span>
          <input
            type="text"
            required
            minLength={2}
            maxLength={255}
            value={name}
            onChange={(e) => handleNameChange(e.target.value)}
            className="w-full rounded-lg border border-[#dfdfe2] px-3 py-2.5 text-sm transition-colors outline-none focus:border-[#22252b]"
            placeholder="Например: Одежда"
          />
        </label>

        <label className="block">
          <span className="mb-1 block text-sm font-medium text-[#22252b]">
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
            className="w-full rounded-lg border border-[#dfdfe2] px-3 py-2.5 text-sm transition-colors outline-none focus:border-[#22252b]"
            placeholder="naprimer-odezhda"
          />
        </label>

        <label className="block">
          <span className="mb-1 block text-sm font-medium text-[#22252b]">
            Порядок сортировки
          </span>
          <input
            type="number"
            value={sortOrder}
            onChange={(e) => setSortOrder(Number(e.target.value))}
            className="w-full rounded-lg border border-[#dfdfe2] px-3 py-2.5 text-sm transition-colors outline-none focus:border-[#22252b]"
          />
        </label>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-[#22252b] px-4 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {loading ? 'Сохранение...' : 'Сохранить'}
        </button>

        {isEdit && (
          <div className="border-t border-[#dfdfe2] pt-4">
            {confirmDelete ? (
              <div className="flex flex-col gap-2">
                <p className="text-sm text-[#878b93]">Вы уверены?</p>
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
                    className="flex-1 rounded-lg border border-[#dfdfe2] px-4 py-2 text-sm font-medium text-[#22252b] hover:bg-[#f4f3f1]"
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
