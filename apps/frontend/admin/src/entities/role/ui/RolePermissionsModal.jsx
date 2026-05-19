'use client';

import { useEffect, useMemo, useRef, useState } from 'react';

import { Button } from '@/shared/ui/Button';
import { Modal } from '@/shared/ui/Modal';

import { useSetRolePermissions } from '../api/mutations';
import { usePermissions, useRole } from '../api/queries';

const PERMISSION_ERROR_CODES = {
  PRIVILEGE_ESCALATION: 'Нельзя назначить права, которых у вас нет',
  ROLE_NOT_FOUND: 'Роль не найдена',
  INSUFFICIENT_PERMISSIONS: 'Недостаточно прав',
};

const RESOURCE_LABELS = {
  identity: 'Идентичности',
  staff: 'Сотрудники',
  customer: 'Клиенты',
  role: 'Роли',
  permission: 'Права',
  brand: 'Бренды',
  category: 'Категории',
  product: 'Товары',
  attribute: 'Атрибуты',
  order: 'Заказы',
  shipment: 'Доставка',
  pricing: 'Цены',
  media: 'Медиа',
};

const ACTION_LABELS = {
  read: 'Просмотр',
  create: 'Создание',
  update: 'Изменение',
  delete: 'Удаление',
  assign: 'Назначение',
  revoke: 'Отзыв',
  activate: 'Активация',
  deactivate: 'Деактивация',
  publish: 'Публикация',
  invite: 'Приглашение',
};

function describeError(err, fallback) {
  return PERMISSION_ERROR_CODES[err?.code] ?? err?.message ?? fallback;
}

function resourceLabel(resource) {
  return RESOURCE_LABELS[resource] || resource;
}

function actionLabel(action) {
  return ACTION_LABELS[action] || action;
}

// Compare two Set<string>: returns {added, removed}. Used to display diff
// summary and to disable Save when nothing changed.
function diffSets(current, baseline) {
  let added = 0;
  let removed = 0;
  for (const id of current) if (!baseline.has(id)) added += 1;
  for (const id of baseline) if (!current.has(id)) removed += 1;
  return { added, removed };
}

export function RolePermissionsModal({ role, onClose, onSuccess }) {
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

  const [checkedIds, setCheckedIds] = useState(() => new Set());
  const [baseline, setBaseline] = useState(() => new Set());
  const [error, setError] = useState('');
  const hydratedRoleIdRef = useRef(null);

  // Hydrate local toggle state once per role.id. Without the ref guard, a
  // background refetch (triggered by save invalidation) would overwrite the
  // user's in-flight checkbox edits with the previous server values.
  useEffect(() => {
    if (!roleDetail?.permissions) return;
    if (hydratedRoleIdRef.current === role.id) return;
    hydratedRoleIdRef.current = role.id;
    const ids = new Set(roleDetail.permissions.map((p) => p.id));
    setCheckedIds(ids);
    setBaseline(new Set(ids));
  }, [roleDetail, role.id]);

  const saveMutation = useSetRolePermissions(role.id);

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

  function handleToggleGroup(group, nextChecked) {
    setCheckedIds((prev) => {
      const next = new Set(prev);
      for (const perm of group.permissions) {
        if (nextChecked) next.add(perm.id);
        else next.delete(perm.id);
      }
      return next;
    });
  }

  function handleSave() {
    setError('');
    saveMutation.mutate([...checkedIds], {
      onSuccess: () => {
        onSuccess();
      },
      onError: (err) => setError(describeError(err, 'Произошла ошибка')),
    });
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

  const diff = useMemo(
    () => diffSets(checkedIds, baseline),
    [checkedIds, baseline],
  );
  const hasChanges = diff.added > 0 || diff.removed > 0;

  return (
    <Modal open onClose={onClose} title={`Права: ${role.name}`} size="lg">
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
          <div className="border-app-border max-h-[460px] overflow-y-auto rounded-xl border bg-white">
            {permissionGroups?.map((group) => {
              const groupIds = group.permissions.map((p) => p.id);
              const checkedInGroup = groupIds.filter((id) =>
                checkedIds.has(id),
              ).length;
              const allChecked = checkedInGroup === groupIds.length;
              const someChecked = checkedInGroup > 0 && !allChecked;
              return (
                <section
                  key={group.resource}
                  className="border-app-border border-b last:border-b-0"
                >
                  {/* Sticky group header — survives long scroll lists, gives
                      the operator a per-group select-all that scales to 100+
                      permissions without 30 manual clicks per role. */}
                  <header className="border-app-border bg-app-bg-soft sticky top-0 z-10 flex items-center gap-3 border-b px-4 py-2">
                    <label className="text-app-text flex flex-1 cursor-pointer items-center gap-2 text-sm font-semibold">
                      <input
                        type="checkbox"
                        className="border-app-border accent-app-text h-4 w-4"
                        checked={allChecked}
                        ref={(el) => {
                          if (el) el.indeterminate = someChecked;
                        }}
                        onChange={(e) =>
                          handleToggleGroup(group, e.target.checked)
                        }
                        aria-label={`Выбрать все права в группе ${resourceLabel(group.resource)}`}
                      />
                      <span className="tracking-wide uppercase">
                        {resourceLabel(group.resource)}
                      </span>
                      <code className="text-app-muted text-xs normal-case">
                        {group.resource}
                      </code>
                    </label>
                    <span className="text-app-muted text-xs tabular-nums">
                      {checkedInGroup}/{groupIds.length}
                    </span>
                  </header>
                  <div className="flex flex-wrap gap-2 px-4 py-3">
                    {group.permissions.map((perm) => {
                      const checked = checkedIds.has(perm.id);
                      return (
                        <label
                          key={perm.id}
                          className={`text-app-text flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-1.5 text-sm transition-colors ${
                            checked
                              ? 'border-app-text-dark/40 bg-app-text-dark/5'
                              : 'border-app-border hover:bg-app-bg-soft'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => handleToggle(perm.id)}
                            className="border-app-border accent-app-text h-4 w-4"
                          />
                          <span>{actionLabel(perm.action)}</span>
                          <code className="text-app-muted text-xs">
                            {perm.action}
                          </code>
                        </label>
                      );
                    })}
                  </div>
                </section>
              );
            })}
          </div>
        )}

        <div className="flex items-center justify-between gap-3">
          <span className="text-app-muted text-xs">
            {loading
              ? ''
              : hasChanges
                ? `Изменения: ${diff.added > 0 ? `+${diff.added}` : ''}${diff.added > 0 && diff.removed > 0 ? ' / ' : ''}${diff.removed > 0 ? `−${diff.removed}` : ''}`
                : 'Без изменений'}
          </span>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              onClick={onClose}
              disabled={saveMutation.isPending}
            >
              Отмена
            </Button>
            <Button
              onClick={handleSave}
              disabled={saveMutation.isPending || loading || !hasChanges}
            >
              {saveMutation.isPending ? 'Сохранение…' : 'Сохранить'}
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}
