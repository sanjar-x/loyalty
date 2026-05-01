'use client';

import { useEffect, useRef, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Modal } from '@/shared/ui/Modal';
import { createRole, deleteRole, roleKeys, updateRole } from '@/entities/role';

const ROLE_ERROR_CODES = {
  ROLE_ALREADY_EXISTS: 'Роль с таким именем уже существует',
  SYSTEM_ROLE_MODIFICATION: 'Системные роли нельзя изменить',
  ROLE_NOT_FOUND: 'Роль не найдена',
  VALIDATION_ERROR: 'Проверьте введённые данные',
  INSUFFICIENT_PERMISSIONS: 'Недостаточно прав',
};

function describeError(err, fallback) {
  return ROLE_ERROR_CODES[err?.code] ?? err?.message ?? fallback;
}

export function RoleModal({ mode, role, onClose, onSuccess }) {
  const isEdit = mode === 'edit';
  const isSystem = isEdit && role?.isSystem;
  const queryClient = useQueryClient();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(false);
  const hydratedRoleIdRef = useRef(null);

  // Hydrate form once per role.id — guards against a background refetch
  // (triggered by save invalidation) wiping the user's edits.
  useEffect(() => {
    if (!isEdit || !role) return;
    if (hydratedRoleIdRef.current === role.id) return;
    hydratedRoleIdRef.current = role.id;
    setName(role.name);
    setDescription(role.description ?? '');
  }, [isEdit, role]);

  function invalidateRoles() {
    queryClient.invalidateQueries({ queryKey: roleKeys.all });
  }

  const saveMutation = useMutation({
    mutationFn: (payload) =>
      isEdit ? updateRole(role.id, payload) : createRole(payload),
    onSuccess: () => {
      invalidateRoles();
      onSuccess();
    },
    onError: (err) => setError(describeError(err, 'Произошла ошибка')),
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteRole(role.id),
    onSuccess: () => {
      invalidateRoles();
      onSuccess();
    },
    onError: (err) => {
      // Reset confirmation only on error so the user sees the "Удалить" button
      // again. On success, the modal unmounts before this would matter.
      setError(describeError(err, 'Не удалось удалить'));
      setConfirmDelete(false);
    },
  });

  function handleSubmit(e) {
    e.preventDefault();
    setError('');
    const payload = {};
    if (!isEdit || !isSystem) payload.name = name;
    payload.description = description || undefined;
    saveMutation.mutate(payload);
  }

  function handleDelete() {
    setError('');
    deleteMutation.mutate();
  }

  const loading = saveMutation.isPending || deleteMutation.isPending;

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
          <span className="text-app-text mb-1 block text-sm font-medium">
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
            className="border-app-border focus:border-app-text disabled:bg-app-card disabled:text-app-muted w-full rounded-lg border px-3 py-2.5 text-sm transition-colors outline-none disabled:cursor-not-allowed"
            placeholder="naprimer_moderator"
          />
        </label>

        <label className="block">
          <span className="text-app-text mb-1 block text-sm font-medium">
            Описание
          </span>
          <input
            type="text"
            maxLength={500}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="border-app-border focus:border-app-text w-full rounded-lg border px-3 py-2.5 text-sm transition-colors outline-none"
            placeholder="Необязательное описание роли"
          />
        </label>

        <button
          type="submit"
          disabled={loading}
          className="bg-app-text w-full rounded-lg px-4 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {saveMutation.isPending ? 'Сохранение...' : 'Сохранить'}
        </button>

        {isEdit && !isSystem && (
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
                Удалить роль
              </button>
            )}
          </div>
        )}
      </form>
    </Modal>
  );
}
