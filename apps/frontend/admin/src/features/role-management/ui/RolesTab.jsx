'use client';

import { useState } from 'react';

import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { pluralizeRu } from '@/shared/lib/utils';

import { RoleModal, RolePermissionsModal, useRoles } from '@/entities/role';

/**
 * Roles tab — surfaced from the consolidated /admin/settings/staff page.
 * Mirrors the previous standalone /admin/settings/roles screen but lives
 * as a panel inside the unified staff/roles/permissions tabbar.
 */
export function RolesTab() {
  const { data: roles = [], isPending: loading, error } = useRoles();
  const [modal, setModal] = useState(null);
  const [permModal, setPermModal] = useState(null);

  function handleCreate() {
    setModal({ mode: 'create' });
  }

  function handleEdit(role) {
    setModal({ mode: 'edit', role });
  }

  function handlePermissions(role) {
    setPermModal({ role });
  }

  return (
    <>
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="text-app-text text-sm font-semibold">
          {loading
            ? ''
            : `${roles.length.toLocaleString('ru-RU')} ${pluralizeRu(roles.length, 'роль', 'роли', 'ролей')}`}
        </div>
        <Button onClick={handleCreate}>+ Создать роль</Button>
      </div>

      {error && (
        <div className="mb-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          Не удалось загрузить роли
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="border-app-border border-t-app-text h-6 w-6 animate-spin rounded-full border-2" />
        </div>
      ) : roles.length === 0 ? (
        <div className="border-app-border flex flex-col items-center gap-3 rounded-2xl border border-dashed py-16 text-center">
          <p className="text-app-text text-base font-semibold">
            Роли не найдены
          </p>
          <p className="text-app-muted text-sm">
            Создайте первую роль и назначьте ей права
          </p>
          <Button onClick={handleCreate} size="lg" className="mt-2">
            + Создать роль
          </Button>
        </div>
      ) : (
        <div className="border-app-border overflow-hidden rounded-xl border">
          <div className="border-app-border text-app-muted bg-app-bg-soft grid grid-cols-[minmax(220px,2fr)_minmax(120px,0.8fr)_minmax(80px,0.5fr)_minmax(220px,1fr)] gap-4 border-b px-4 py-3 text-xs font-semibold tracking-wider uppercase">
            <span>Название</span>
            <span>Тип</span>
            <span>Прав</span>
            <span className="text-right">Действия</span>
          </div>
          <ul className="divide-app-border divide-y">
            {roles.map((role) => (
              <li
                key={role.id}
                className="hover:bg-app-bg-soft grid grid-cols-[minmax(220px,2fr)_minmax(120px,0.8fr)_minmax(80px,0.5fr)_minmax(220px,1fr)] items-center gap-4 px-4 py-3"
              >
                <div className="text-app-text min-w-0 truncate text-sm font-semibold">
                  {role.name}
                </div>
                <div>
                  {role.isSystem ? (
                    <Badge variant="dark">Системная</Badge>
                  ) : (
                    <Badge variant="muted">Кастомная</Badge>
                  )}
                </div>
                <div className="text-app-muted text-sm tabular-nums">
                  {role.permissionCount ?? 0}
                </div>
                <div className="flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => handlePermissions(role)}
                    className="border-app-border text-app-text hover:bg-app-card rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors"
                  >
                    Настроить права
                  </button>
                  {!role.isSystem && (
                    <>
                      <button
                        type="button"
                        onClick={() => handleEdit(role)}
                        className="border-app-border text-app-muted hover:bg-app-card rounded-lg border px-2 py-1.5 text-xs transition-colors"
                        aria-label={`Редактировать ${role.name}`}
                      >
                        &#9998;
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          handleEdit({ ...role, triggerDelete: true })
                        }
                        className="border-app-border rounded-lg border px-2 py-1.5 text-xs text-red-500 transition-colors hover:bg-red-50"
                        aria-label={`Удалить ${role.name}`}
                      >
                        &#128465;
                      </button>
                    </>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {modal && (
        <RoleModal
          mode={modal.mode}
          role={modal.role}
          onClose={() => setModal(null)}
          onSuccess={() => setModal(null)}
        />
      )}

      {permModal && (
        <RolePermissionsModal
          key={permModal.role.id}
          role={permModal.role}
          onClose={() => setPermModal(null)}
          onSuccess={() => setPermModal(null)}
        />
      )}
    </>
  );
}
