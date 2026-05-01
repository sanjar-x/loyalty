'use client';

import { useEffect, useRef, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Modal } from '@/shared/ui/Modal';
import {
  roleKeys,
  setRolePermissions,
  usePermissions,
  useRole,
} from '@/entities/role';

const PERMISSION_ERROR_CODES = {
  PRIVILEGE_ESCALATION: 'Нельзя назначить права, которых у вас нет',
  ROLE_NOT_FOUND: 'Роль не найдена',
  INSUFFICIENT_PERMISSIONS: 'Недостаточно прав',
};

function describeError(err, fallback) {
  return PERMISSION_ERROR_CODES[err?.code] ?? err?.message ?? fallback;
}

function capitalize(str) {
  if (!str) return str;
  return str.charAt(0).toUpperCase() + str.slice(1);
}

export function RolePermissionsModal({ role, onClose, onSuccess }) {
  const queryClient = useQueryClient();
  const {
    data: permissionGroups,
    isPending: permissionsLoading,
    error: permissionsError,
  } = usePermissions();
  const {
    data: roleDetail,
    isPending: roleLoading,
    error: roleError,
  } = useRole(role.id);

  const [checkedIds, setCheckedIds] = useState(new Set());
  const [error, setError] = useState('');
  const hydratedRoleIdRef = useRef(null);

  // Hydrate local toggle state once per role.id. Without the ref guard, a
  // background refetch (triggered by save invalidation) would overwrite the
  // user's in-flight checkbox edits with the previous server values.
  useEffect(() => {
    if (!roleDetail?.permissions) return;
    if (hydratedRoleIdRef.current === role.id) return;
    hydratedRoleIdRef.current = role.id;
    setCheckedIds(new Set(roleDetail.permissions.map((p) => p.id)));
  }, [roleDetail, role.id]);

  const saveMutation = useMutation({
    mutationFn: (permissionIds) => setRolePermissions(role.id, permissionIds),
    onSuccess: () => {
      // Fire-and-forget invalidation so the modal closes immediately; the
      // refetch happens in the background and the parent list updates when
      // it's ready.
      queryClient.invalidateQueries({ queryKey: roleKeys.all });
      onSuccess();
    },
    onError: (err) => setError(describeError(err, 'Произошла ошибка')),
  });

  function handleToggle(permissionId) {
    setCheckedIds((prev) => {
      const next = new Set(prev);
      if (next.has(permissionId)) {
        next.delete(permissionId);
      } else {
        next.add(permissionId);
      }
      return next;
    });
  }

  function handleSave() {
    setError('');
    saveMutation.mutate([...checkedIds]);
  }

  const loading = permissionsLoading || roleLoading;
  const fetchError =
    permissionsError || roleError
      ? describeError(
          permissionsError ?? roleError,
          'Не удалось загрузить данные',
        )
      : '';
  const displayError = error || fetchError;

  return (
    <Modal open onClose={onClose} title={`Права: ${role.name}`}>
      <div className="mt-5 flex flex-col gap-4">
        {displayError && (
          <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">
            {displayError}
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="border-app-border border-t-app-text h-6 w-6 animate-spin rounded-full border-2" />
          </div>
        ) : (
          <div className="max-h-[400px] space-y-4 overflow-y-auto">
            {permissionGroups?.map((group) => (
              <div key={group.resource}>
                <p className="text-app-text mb-2 text-sm font-medium">
                  {capitalize(group.resource)}
                </p>
                <div className="flex flex-wrap gap-3">
                  {group.permissions.map((perm) => (
                    <label
                      key={perm.id}
                      className="text-app-muted flex items-center gap-1.5 text-sm"
                    >
                      <input
                        type="checkbox"
                        checked={checkedIds.has(perm.id)}
                        onChange={() => handleToggle(perm.id)}
                        className="border-app-border accent-app-text h-4 w-4 rounded"
                      />
                      {perm.action}
                    </label>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        <button
          type="button"
          onClick={handleSave}
          disabled={saveMutation.isPending || loading}
          className="bg-app-text w-full rounded-lg px-4 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {saveMutation.isPending ? 'Сохранение...' : 'Сохранить'}
        </button>
      </div>
    </Modal>
  );
}
