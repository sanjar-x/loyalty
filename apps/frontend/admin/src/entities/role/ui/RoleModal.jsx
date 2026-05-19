'use client';

import { useEffect, useRef, useState } from 'react';
import { Button } from '@/shared/ui/Button';
import { Modal } from '@/shared/ui/Modal';
import { useCreateRole, useDeleteRole, useUpdateRole } from '../api/mutations';

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
    // RolesTab signals "open this modal in delete-confirmation state" via
    // `triggerDelete: true`. Without honouring it, the trash icon would
    // open a full edit form and bury the destructive action below the
    // Save button — a UX regression.
    if (role.triggerDelete) setConfirmDelete(true);
  }, [isEdit, role]);

  const createMutation = useCreateRole();
  const updateMutation = useUpdateRole(role?.id);
  const deleteMutation = useDeleteRole(role?.id);

  function handleSubmit(e) {
    e.preventDefault();
    setError('');
    const payload = {};
    if (!isEdit || !isSystem) payload.name = name;
    // Explicit null clears the backend field on PATCH; `undefined` would
    // be dropped by the JSON serializer and leave the previous description
    // untouched — silently swallowing a "clear text + save" intent.
    const trimmed = description.trim();
    payload.description = trimmed === '' ? null : trimmed;
    const mutation = isEdit ? updateMutation : createMutation;
    mutation.mutate(payload, {
      onSuccess: () => onSuccess(),
      onError: (err) => setError(describeError(err, 'Произошла ошибка')),
    });
  }

  function handleDelete() {
    setError('');
    deleteMutation.mutate(undefined, {
      onSuccess: () => onSuccess(),
      onError: (err) => {
        // Reset confirmation only on error so the user sees the "Удалить"
        // button again. On success, the modal unmounts before this matters.
        setError(describeError(err, 'Не удалось удалить'));
        setConfirmDelete(false);
      },
    });
  }

  const loading =
    createMutation.isPending ||
    updateMutation.isPending ||
    deleteMutation.isPending;
  const saving = createMutation.isPending || updateMutation.isPending;

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
            placeholder="marketing_manager"
            aria-describedby="role-name-hint"
          />
          <span
            id="role-name-hint"
            className="text-app-muted mt-1 block text-xs"
          >
            Только латиница в нижнем регистре и подчёркивания, например{' '}
            <code>marketing_manager</code>.
          </span>
        </label>

        <label className="block">
          <span className="text-app-text mb-1 block text-sm font-medium">
            Описание
          </span>
          <textarea
            rows={3}
            maxLength={500}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="border-app-border focus:border-app-text w-full resize-y rounded-lg border px-3 py-2.5 text-sm transition-colors outline-none"
            placeholder="Необязательное описание роли"
          />
        </label>

        <Button type="submit" disabled={loading} fullWidth>
          {saving ? 'Сохранение…' : 'Сохранить'}
        </Button>

        {isEdit && !isSystem && (
          <div className="border-app-border border-t pt-4">
            {confirmDelete ? (
              <div className="flex flex-col gap-2">
                <p className="text-app-muted text-sm">Вы уверены?</p>
                <div className="flex gap-2">
                  <Button
                    variant="danger"
                    onClick={handleDelete}
                    disabled={loading}
                    className="flex-1"
                  >
                    Да, удалить
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => setConfirmDelete(false)}
                    className="flex-1"
                  >
                    Отмена
                  </Button>
                </div>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setConfirmDelete(true)}
                className="rounded text-sm font-medium text-red-600 hover:text-red-700 focus-visible:ring-2 focus-visible:ring-[#4a90d9] focus-visible:ring-offset-2 focus-visible:outline-none"
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
