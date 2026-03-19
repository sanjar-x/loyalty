'use client';

import { useState, useEffect, useCallback } from 'react';
import { Badge } from '@/components/ui/Badge';
import { RoleModal } from '@/components/admin/settings/roles/RoleModal';
import { RolePermissionsModal } from '@/components/admin/settings/roles/RolePermissionsModal';

export default function RolesPage() {
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);
  const [permModal, setPermModal] = useState(null);

  const fetchRoles = useCallback(async () => {
    try {
      const res = await fetch('/api/admin/roles', {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      });
      if (res.ok) {
        const data = await res.json();
        setRoles(data);
      }
    } catch {
      // silent — roles stays empty
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRoles();
  }, [fetchRoles]);

  function handleCreate() {
    setModal({ mode: 'create' });
  }

  function handleEdit(role) {
    setModal({ mode: 'edit', role });
  }

  function handlePermissions(role) {
    setPermModal({ role });
  }

  function handleModalSuccess() {
    setModal(null);
    setLoading(true);
    fetchRoles();
  }

  function handlePermModalSuccess() {
    setPermModal(null);
    setLoading(true);
    fetchRoles();
  }

  return (
    <div>
      <div className="mb-5 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-[#22252b]">Роли</h2>
        <button
          onClick={handleCreate}
          className="rounded-lg bg-[#22252b] px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
        >
          + Создать роль
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#dfdfe2] border-t-[#22252b]" />
        </div>
      ) : roles.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-12 text-center">
          <p className="text-sm text-[#878b93]">Роли не найдены</p>
          <button
            onClick={handleCreate}
            className="text-sm font-medium text-[#22252b] underline hover:no-underline"
          >
            Создать первую
          </button>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-[#dfdfe2]">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[#dfdfe2] bg-[#f4f3f1]">
                <th className="px-4 py-3 font-medium text-[#878b93]">
                  Название
                </th>
                <th className="px-4 py-3 font-medium text-[#878b93]">Тип</th>
                <th className="px-4 py-3 font-medium text-[#878b93]">Прав</th>
                <th className="px-4 py-3 text-right font-medium text-[#878b93]">
                  Действия
                </th>
              </tr>
            </thead>
            <tbody>
              {roles.map((role) => (
                <tr
                  key={role.id}
                  className="border-b border-[#dfdfe2] last:border-b-0"
                >
                  <td className="px-4 py-3 font-medium text-[#22252b]">
                    {role.name}
                  </td>
                  <td className="px-4 py-3">
                    {role.isSystem ? (
                      <Badge variant="dark">Системная</Badge>
                    ) : (
                      <Badge variant="muted">Кастомная</Badge>
                    )}
                  </td>
                  <td className="px-4 py-3 text-[#878b93]">
                    {role.permissionCount ?? 0}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handlePermissions(role)}
                        className="rounded-lg border border-[#dfdfe2] px-3 py-1.5 text-xs font-medium text-[#22252b] transition-colors hover:bg-[#f4f3f1]"
                      >
                        Настроить права
                      </button>
                      {!role.isSystem && (
                        <>
                          <button
                            onClick={() => handleEdit(role)}
                            className="rounded-lg border border-[#dfdfe2] px-2 py-1.5 text-xs text-[#878b93] transition-colors hover:bg-[#f4f3f1]"
                            aria-label={`Редактировать ${role.name}`}
                          >
                            &#9998;
                          </button>
                          <button
                            onClick={() =>
                              handleEdit({ ...role, triggerDelete: true })
                            }
                            className="rounded-lg border border-[#dfdfe2] px-2 py-1.5 text-xs text-red-500 transition-colors hover:bg-red-50"
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
          onSuccess={handleModalSuccess}
        />
      )}

      {permModal && (
        <RolePermissionsModal
          role={permModal.role}
          onClose={() => setPermModal(null)}
          onSuccess={handlePermModalSuccess}
        />
      )}
    </div>
  );
}
