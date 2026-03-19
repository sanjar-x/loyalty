'use client';

import { useState, useEffect } from 'react';
import { Modal } from '@/components/ui/Modal';

const ERROR_MESSAGES = {
  ROLE_ALREADY_EXISTS: 'Роль с таким именем уже существует',
  SYSTEM_ROLE_MODIFICATION: 'Системные роли нельзя изменить',
  ROLE_NOT_FOUND: 'Роль не найдена',
  VALIDATION_ERROR: 'Проверьте введённые данные',
  INSUFFICIENT_PERMISSIONS: 'Недостаточно прав',
};

export function RoleModal({ mode, role, onClose, onSuccess }) {
  const isEdit = mode === 'edit';
  const isSystem = isEdit && role?.isSystem;
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    if (isEdit && role) {
      setName(role.name);
      setDescription(role.description ?? '');
    }
  }, [isEdit, role]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const url = isEdit ? `/api/admin/roles/${role.id}` : '/api/admin/roles';
      const method = isEdit ? 'PATCH' : 'POST';

      const body = {};
      if (!isEdit || !isSystem) {
        body.name = name;
      }
      body.description = description || undefined;

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
      const res = await fetch(`/api/admin/roles/${role.id}`, {
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
      title={isEdit ? 'Редактирование' : 'Новая роль'}
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
            pattern="^[a-z_]+$"
            maxLength={255}
            value={name}
            disabled={isSystem}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-lg border border-[#dfdfe2] px-3 py-2.5 text-sm transition-colors outline-none focus:border-[#22252b] disabled:cursor-not-allowed disabled:bg-[#f4f3f1] disabled:text-[#878b93]"
            placeholder="naprimer_moderator"
          />
        </label>

        <label className="block">
          <span className="mb-1 block text-sm font-medium text-[#22252b]">
            Описание
          </span>
          <input
            type="text"
            maxLength={500}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full rounded-lg border border-[#dfdfe2] px-3 py-2.5 text-sm transition-colors outline-none focus:border-[#22252b]"
            placeholder="Необязательное описание роли"
          />
        </label>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-[#22252b] px-4 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {loading ? 'Сохранение...' : 'Сохранить'}
        </button>

        {isEdit && !isSystem && (
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
                Удалить роль
              </button>
            )}
          </div>
        )}
      </form>
    </Modal>
  );
}
