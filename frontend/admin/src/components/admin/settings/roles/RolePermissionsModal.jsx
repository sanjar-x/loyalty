'use client';

import { useState, useEffect, useCallback } from 'react';
import { Modal } from '@/components/ui/Modal';

const ERROR_MESSAGES = {
  PRIVILEGE_ESCALATION: 'Нельзя назначить права, которых у вас нет',
  ROLE_NOT_FOUND: 'Роль не найдена',
  INSUFFICIENT_PERMISSIONS: 'Недостаточно прав',
};

export function RolePermissionsModal({ role, onClose, onSuccess }) {
  const [groups, setGroups] = useState([]);
  const [checkedIds, setCheckedIds] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const [permRes, roleRes] = await Promise.all([
        fetch('/api/admin/permissions', {
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
        }),
        fetch(`/api/admin/roles/${role.id}`, {
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
        }),
      ]);

      if (!permRes.ok || !roleRes.ok) {
        setError('Не удалось загрузить данные');
        return;
      }

      const permData = await permRes.json();
      const roleData = await roleRes.json();

      setGroups(permData);
      setCheckedIds(new Set(roleData.permissions.map((p) => p.id)));
    } catch {
      setError('Нет связи с сервером');
    } finally {
      setLoading(false);
    }
  }, [role.id]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

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

  async function handleSave() {
    setError('');
    setSaving(true);

    try {
      const res = await fetch(`/api/admin/roles/${role.id}/permissions`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: JSON.stringify({ permissionIds: [...checkedIds] }),
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
      setSaving(false);
    }
  }

  function capitalize(str) {
    if (!str) return str;
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  return (
    <Modal open onClose={onClose} title={`Права: ${role.name}`}>
      <div className="mt-5 flex flex-col gap-4">
        {error && (
          <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#dfdfe2] border-t-[#22252b]" />
          </div>
        ) : (
          <div className="max-h-[400px] space-y-4 overflow-y-auto">
            {groups.map((group) => (
              <div key={group.resource}>
                <p className="mb-2 text-sm font-medium text-[#22252b]">
                  {capitalize(group.resource)}
                </p>
                <div className="flex flex-wrap gap-3">
                  {group.permissions.map((perm) => (
                    <label
                      key={perm.id}
                      className="flex items-center gap-1.5 text-sm text-[#878b93]"
                    >
                      <input
                        type="checkbox"
                        checked={checkedIds.has(perm.id)}
                        onChange={() => handleToggle(perm.id)}
                        className="h-4 w-4 rounded border-[#dfdfe2] accent-[#22252b]"
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
          disabled={saving || loading}
          className="w-full rounded-lg bg-[#22252b] px-4 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {saving ? 'Сохранение...' : 'Сохранить'}
        </button>
      </div>
    </Modal>
  );
}
