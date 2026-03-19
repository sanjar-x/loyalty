'use client';

import { useCallback, useEffect, useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import dayjs from '@/lib/dayjs';
import styles from '@/app/admin/users/page.module.css';

const ERROR_MESSAGES = {
  IDENTITY_NOT_FOUND: 'Пользователь не найден',
  IDENTITY_ALREADY_DEACTIVATED: 'Аккаунт уже деактивирован',
  SELF_DEACTIVATION_FORBIDDEN: 'Нельзя деактивировать свой аккаунт',
  LAST_ADMIN_PROTECTION: 'Нельзя деактивировать последнего администратора',
  INSUFFICIENT_PERMISSIONS: 'Недостаточно прав',
};

function translateError(err) {
  if (err && typeof err === 'object' && err.code) {
    return ERROR_MESSAGES[err.code] || err.message || 'Произошла ошибка';
  }
  if (typeof err === 'string') {
    return ERROR_MESSAGES[err] || err;
  }
  return 'Произошла ошибка';
}

export function UserDetailModal({ identityId, open, onClose, onUpdate }) {
  const [detail, setDetail] = useState(null);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [mutating, setMutating] = useState(false);
  const [selectedRoleId, setSelectedRoleId] = useState('');
  const [confirmDeactivate, setConfirmDeactivate] = useState(false);

  const fetchDetail = useCallback(async () => {
    if (!identityId) return;
    setLoading(true);
    setError('');
    try {
      const [detailRes, rolesRes] = await Promise.all([
        fetch(`/api/admin/identities/${identityId}`),
        fetch('/api/admin/roles'),
      ]);

      if (!detailRes.ok) {
        const data = await detailRes.json().catch(() => ({}));
        throw data;
      }

      const detailData = await detailRes.json();
      const rolesData = rolesRes.ok ? await rolesRes.json() : [];

      setDetail(detailData);
      setRoles(Array.isArray(rolesData) ? rolesData : rolesData.items || []);
    } catch (err) {
      setError(translateError(err));
    } finally {
      setLoading(false);
    }
  }, [identityId]);

  useEffect(() => {
    if (open && identityId) {
      fetchDetail();
      setConfirmDeactivate(false);
      setSelectedRoleId('');
    }
  }, [open, identityId, fetchDetail]);

  async function handleAssignRole() {
    if (!selectedRoleId || mutating) return;
    setMutating(true);
    setError('');
    try {
      const res = await fetch(`/api/admin/identities/${identityId}/roles`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ roleId: selectedRoleId }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw data;
      }
      setSelectedRoleId('');
      await fetchDetail();
      onUpdate();
    } catch (err) {
      setError(translateError(err));
    } finally {
      setMutating(false);
    }
  }

  async function handleRevokeRole(roleId) {
    if (mutating) return;
    setMutating(true);
    setError('');
    try {
      const res = await fetch(
        `/api/admin/identities/${identityId}/roles/${roleId}`,
        { method: 'DELETE' },
      );
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw data;
      }
      await fetchDetail();
      onUpdate();
    } catch (err) {
      setError(translateError(err));
    } finally {
      setMutating(false);
    }
  }

  async function handleDeactivate() {
    if (!confirmDeactivate) {
      setConfirmDeactivate(true);
      return;
    }
    if (mutating) return;
    setMutating(true);
    setError('');
    try {
      const res = await fetch(
        `/api/admin/identities/${identityId}/deactivate`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reason: 'admin_action' }),
        },
      );
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw data;
      }
      setConfirmDeactivate(false);
      await fetchDetail();
      onUpdate();
    } catch (err) {
      setError(translateError(err));
    } finally {
      setMutating(false);
    }
  }

  async function handleReactivate() {
    if (mutating) return;
    setMutating(true);
    setError('');
    try {
      const res = await fetch(
        `/api/admin/identities/${identityId}/reactivate`,
        { method: 'POST' },
      );
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw data;
      }
      await fetchDetail();
      onUpdate();
    } catch (err) {
      setError(translateError(err));
    } finally {
      setMutating(false);
    }
  }

  const assignedRoleIds = new Set(
    (detail?.roles || []).map((r) => r.id || r.roleId),
  );
  const availableRoles = roles.filter((r) => !assignedRoleIds.has(r.id));

  return (
    <Modal open={open} onClose={onClose} title="Пользователь">
      {loading && !detail && (
        <div className={styles.detailSection}>
          <div className={styles.skeletonRow} style={{ height: 32 }} />
          <div className={styles.skeletonRow} style={{ height: 32 }} />
          <div className={styles.skeletonRow} style={{ height: 32 }} />
        </div>
      )}

      {detail && (
        <>
          <div className={styles.detailSection}>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Email</span>
              <span className={styles.detailValue}>{detail.email}</span>
            </div>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Имя</span>
              <span className={styles.detailValue}>
                {[detail.firstName, detail.lastName]
                  .filter(Boolean)
                  .join(' ') || '—'}
              </span>
            </div>
            {detail.phone && (
              <div className={styles.detailRow}>
                <span className={styles.detailLabel}>Телефон</span>
                <span className={styles.detailValue}>{detail.phone}</span>
              </div>
            )}
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Статус</span>
              <span className={styles.detailValue}>
                <span
                  className={`${styles.statusDot} ${
                    detail.isActive
                      ? styles.statusActive
                      : styles.statusInactive
                  }`}
                />
                {detail.isActive ? 'Активен' : 'Неактивен'}
              </span>
            </div>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Дата регистрации</span>
              <span className={styles.detailValue}>
                {dayjs(detail.createdAt).format('D MMMM YYYY, HH:mm')}
              </span>
            </div>
          </div>

          <div className={styles.rolesSection}>
            <p className={styles.rolesTitle}>Роли</p>
            <div className={styles.rolesList}>
              {(detail.roles || []).map((role) => (
                <span key={role.id || role.roleId} className={styles.roleBadge}>
                  {role.name}
                  <button
                    type="button"
                    className={styles.roleRemoveButton}
                    onClick={() => handleRevokeRole(role.id || role.roleId)}
                    disabled={mutating}
                    aria-label={`Удалить роль ${role.name}`}
                  >
                    ✕
                  </button>
                </span>
              ))}
              {(detail.roles || []).length === 0 && (
                <span style={{ color: '#878b93', fontSize: 14 }}>
                  Нет ролей
                </span>
              )}
            </div>

            {availableRoles.length > 0 && (
              <div className={styles.addRoleRow}>
                <select
                  value={selectedRoleId}
                  onChange={(e) => setSelectedRoleId(e.target.value)}
                  className={styles.addRoleSelect}
                  aria-label="Выбрать роль для назначения"
                >
                  <option value="">Выберите роль</option>
                  {availableRoles.map((role) => (
                    <option key={role.id} value={role.id}>
                      {role.name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className={styles.addRoleButton}
                  onClick={handleAssignRole}
                  disabled={!selectedRoleId || mutating}
                >
                  + Назначить роль
                </button>
              </div>
            )}
          </div>

          <div className={styles.modalActions}>
            {detail.isActive ? (
              <button
                type="button"
                className={styles.deactivateButton}
                onClick={handleDeactivate}
                disabled={mutating}
              >
                {confirmDeactivate
                  ? 'Подтвердить деактивацию'
                  : 'Деактивировать'}
              </button>
            ) : (
              <button
                type="button"
                className={styles.reactivateButton}
                onClick={handleReactivate}
                disabled={mutating}
              >
                Реактивировать
              </button>
            )}
          </div>
        </>
      )}

      {error && <div className={styles.modalError}>{error}</div>}
    </Modal>
  );
}
