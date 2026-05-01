'use client';

import { useCallback, useEffect, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Modal } from '@/shared/ui/Modal';
import { useRoles } from '@/entities/role';
import dayjs from '@/shared/lib/dayjs';
import {
  assignIdentityRole,
  deactivateIdentity,
  identityKeys,
  reactivateIdentity,
  revokeIdentityRole,
  useIdentity,
} from '@/entities/user';
import styles from './styles/users.module.css';

const IDENTITY_ERROR_CODES = {
  IDENTITY_NOT_FOUND: 'Пользователь не найден',
  IDENTITY_ALREADY_DEACTIVATED: 'Аккаунт уже деактивирован',
  SELF_DEACTIVATION_FORBIDDEN: 'Нельзя деактивировать свой аккаунт',
  LAST_ADMIN_PROTECTION: 'Нельзя деактивировать последнего администратора',
  INSUFFICIENT_PERMISSIONS: 'Недостаточно прав',
};

function describeError(err, fallback = 'Произошла ошибка') {
  return IDENTITY_ERROR_CODES[err?.code] ?? err?.message ?? fallback;
}

export function UserDetailModal({ identityId, open, onClose, onUpdate }) {
  const queryClient = useQueryClient();
  const enabled = open && Boolean(identityId);

  const {
    data: detail,
    isPending: detailLoading,
    error: detailError,
  } = useIdentity(enabled ? identityId : null);

  const { data: roles = [] } = useRoles();

  const [error, setError] = useState('');
  const [selectedRoleId, setSelectedRoleId] = useState('');
  const [confirmDeactivate, setConfirmDeactivate] = useState(false);

  // Reset transient UI state every time the modal opens against a new user.
  useEffect(() => {
    if (open && identityId) {
      setSelectedRoleId('');
      setConfirmDeactivate(false);
      setError('');
    }
  }, [open, identityId]);

  // Fire-and-forget invalidation: the cache update happens in the background
  // and we don't await it, so the modal's local state changes (clearing
  // `selectedRoleId`, closing the confirm flow) finish synchronously and
  // can't run after unmount.
  const invalidate = useCallback(() => {
    queryClient.invalidateQueries({
      queryKey: identityKeys.detail(identityId),
    });
    queryClient.invalidateQueries({ queryKey: identityKeys.lists() });
    onUpdate?.();
  }, [queryClient, identityId, onUpdate]);

  const assignMutation = useMutation({
    mutationFn: (roleId) => assignIdentityRole(identityId, roleId),
    onSuccess: () => {
      setSelectedRoleId('');
      invalidate();
    },
    onError: (err) => setError(describeError(err, 'Не удалось назначить роль')),
  });

  const revokeMutation = useMutation({
    mutationFn: (roleId) => revokeIdentityRole(identityId, roleId),
    onSuccess: () => invalidate(),
    onError: (err) => setError(describeError(err, 'Не удалось удалить роль')),
  });

  const deactivateMutation = useMutation({
    mutationFn: () => deactivateIdentity(identityId),
    onSuccess: () => {
      setConfirmDeactivate(false);
      invalidate();
    },
    onError: (err) => setError(describeError(err, 'Не удалось деактивировать')),
  });

  const reactivateMutation = useMutation({
    mutationFn: () => reactivateIdentity(identityId),
    onSuccess: () => invalidate(),
    onError: (err) => setError(describeError(err, 'Не удалось реактивировать')),
  });

  const mutating =
    assignMutation.isPending ||
    revokeMutation.isPending ||
    deactivateMutation.isPending ||
    reactivateMutation.isPending;

  function handleAssignRole() {
    if (!selectedRoleId) return;
    setError('');
    assignMutation.mutate(selectedRoleId);
  }

  function handleRevokeRole(roleId) {
    setError('');
    revokeMutation.mutate(roleId);
  }

  function handleDeactivate() {
    if (!confirmDeactivate) {
      setConfirmDeactivate(true);
      return;
    }
    setError('');
    deactivateMutation.mutate();
  }

  function handleReactivate() {
    setError('');
    reactivateMutation.mutate();
  }

  const assignedRoleIds = new Set(
    (detail?.roles || []).map((r) => r.id || r.roleId),
  );
  const availableRoles = roles.filter((r) => !assignedRoleIds.has(r.id));
  const displayError =
    error ||
    (detailError ? describeError(detailError, 'Не удалось загрузить') : '');

  return (
    <Modal open={open} onClose={onClose} title="Пользователь">
      {detailLoading && !detail && (
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
                <span className="text-app-muted text-sm">Нет ролей</span>
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

      {displayError && <div className={styles.modalError}>{displayError}</div>}
    </Modal>
  );
}
