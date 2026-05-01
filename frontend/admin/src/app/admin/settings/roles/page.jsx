'use client';

import { useState } from 'react';
import { Badge } from '@/shared/ui/Badge';
import { RoleModal, RolePermissionsModal, useRoles } from '@/entities/role';

export default function RolesPage() {
  const { data: roles = [], isPending: loading } = useRoles();
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
    <div>
      <div className="mb-5 flex items-center justify-between">
        <h2 className="text-app-text text-xl font-semibold">Роли</h2>
        <button
          onClick={handleCreate}
          className="bg-app-text rounded-lg px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
        >
          + Создать роль
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="border-app-border border-t-app-text h-6 w-6 animate-spin rounded-full border-2" />
        </div>
      ) : roles.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-12 text-center">
          <p className="text-app-muted text-sm">Роли не найдены</p>
          <button
            onClick={handleCreate}
            className="text-app-text text-sm font-medium underline hover:no-underline"
          >
            Создать первую
          </button>
        </div>
      ) : (
        <div className="border-app-border overflow-hidden rounded-xl border">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-app-border bg-app-card border-b">
                <th className="text-app-muted px-4 py-3 font-medium">
                  Название
                </th>
                <th className="text-app-muted px-4 py-3 font-medium">Тип</th>
                <th className="text-app-muted px-4 py-3 font-medium">Прав</th>
                <th className="text-app-muted px-4 py-3 text-right font-medium">
                  Действия
                </th>
              </tr>
            </thead>
            <tbody>
              {roles.map((role) => (
                <tr
                  key={role.id}
                  className="border-app-border border-b last:border-b-0"
                >
                  <td className="text-app-text px-4 py-3 font-medium">
                    {role.name}
                  </td>
                  <td className="px-4 py-3">
                    {role.isSystem ? (
                      <Badge variant="dark">Системная</Badge>
                    ) : (
                      <Badge variant="muted">Кастомная</Badge>
                    )}
                  </td>
                  <td className="text-app-muted px-4 py-3">
                    {role.permissionCount ?? 0}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handlePermissions(role)}
                        className="border-app-border text-app-text hover:bg-app-card rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors"
                      >
                        Настроить права
                      </button>
                      {!role.isSystem && (
                        <>
                          <button
                            onClick={() => handleEdit(role)}
                            className="border-app-border text-app-muted hover:bg-app-card rounded-lg border px-2 py-1.5 text-xs transition-colors"
                            aria-label={`Редактировать ${role.name}`}
                          >
                            &#9998;
                          </button>
                          <button
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
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
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
    </div>
  );
}
