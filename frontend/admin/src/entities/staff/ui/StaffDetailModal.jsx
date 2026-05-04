'use client';

import { useCallback, useEffect, useState } from 'react';

import { useQueryClient } from '@tanstack/react-query';

import { useAssignIdentityRole, useRevokeIdentityRole } from '@/entities/user';

import { useRoles } from '@/entities/role';

import dayjs from '@/shared/lib/dayjs';
import { Modal } from '@/shared/ui/Modal';

import { useDeactivateStaff, useReactivateStaff } from '../api/mutations';
import { useStaffMember } from '../api/queries';
import { staffKeys } from '../api/keys';
import styles from './styles/staff.module.css';

// Mirrors `modules/identity/domain/exceptions.py` — adding any code requires a
// matching backend rename, so keep the keys as-is and only expand the table.
const STAFF_ERROR_CODES = {
  IDENTITY_NOT_FOUND: 'Сотрудник не найден',
  IDENTITY_ALREADY_DEACTIVATED: 'Аккаунт уже деактивирован',
  IDENTITY_ALREADY_ACTIVE: 'Аккаунт уже активен',
  SELF_DEACTIVATION_FORBIDDEN: 'Нельзя деактивировать свой аккаунт',
  LAST_ADMIN_PROTECTION: 'Нельзя деактивировать последнего администратора',
  INSUFFICIENT_PERMISSIONS: 'Недостаточно прав',
  ROLE_NOT_FOUND: 'Роль не найдена',
  ROLE_ALREADY_ASSIGNED: 'Роль уже назначена',
  ACCOUNT_TYPE_MISMATCH: 'Эта роль предназначена для другого типа аккаунта',
  PRIVILEGE_ESCALATION: 'Нельзя изменять роли выше своих',
  SYSTEM_ROLE_MODIFICATION: 'Системные роли изменять нельзя',
  VALIDATION_ERROR: 'Проверьте введённые данные',
};

const REASON_MAX = 200;
const REASON_MIN = 1;
const FALLBACK = '—';

const AUTH_TYPE_LABELS = {
  LOCAL: 'Email + пароль',
  OIDC: 'OIDC',
  TELEGRAM: 'Telegram',
};

function describeError(err, fallback = 'Произошла ошибка') {
  return STAFF_ERROR_CODES[err?.code] ?? err?.message ?? fallback;
}

function formatDateTime(value) {
  if (!value) return null;
  const m = dayjs(value);
  return m.isValid() ? m.format('D MMMM YYYY, HH:mm') : null;
}

export function StaffDetailModal({ identityId, open, onClose, onUpdate }) {
  const qc = useQueryClient();
  const enabled = open && Boolean(identityId);

  const {
    data: detail,
    isPending: detailLoading,
    error: detailError,
  } = useStaffMember(enabled ? identityId : null);
  const { data: roles = [] } = useRoles();

  const [error, setError] = useState('');
  const [selectedRoleId, setSelectedRoleId] = useState('');
  const [confirmDeactivate, setConfirmDeactivate] = useState(false);
  const [reason, setReason] = useState('');

  useEffect(() => {
    if (open && identityId) {
      setSelectedRoleId('');
      setConfirmDeactivate(false);
      setReason('');
      setError('');
    }
  }, [open, identityId]);

  // Role assignment for staff goes through the generic /admin/identities
  // endpoints — same as customers — because /admin/staff itself doesn't
  // expose role mutations.
  const assignMutation = useAssignIdentityRole(identityId);
  const revokeMutation = useRevokeIdentityRole(identityId);
  const deactivateMutation = useDeactivateStaff(identityId);
  const reactivateMutation = useReactivateStaff(identityId);

  const invalidateBoth = useCallback(() => {
    qc.invalidateQueries({ queryKey: staffKeys.detail(identityId) });
    qc.invalidateQueries({ queryKey: staffKeys.lists() });
    onUpdate?.();
  }, [qc, identityId, onUpdate]);

  const mutating =
    assignMutation.isPending ||
    revokeMutation.isPending ||
    deactivateMutation.isPending ||
    reactivateMutation.isPending;

  function handleAssignRole() {
    if (!selectedRoleId) return;
    setError('');
    assignMutation.mutate(selectedRoleId, {
      onSuccess: () => {
        setSelectedRoleId('');
        invalidateBoth();
      },
      onError: (err) =>
        setError(describeError(err, 'Не удалось назначить роль')),
    });
  }

  function handleRevokeRole(roleId) {
    setError('');
    revokeMutation.mutate(roleId, {
      onSuccess: () => invalidateBoth(),
      onError: (err) => setError(describeError(err, 'Не удалось удалить роль')),
    });
  }

  function handleDeactivate() {
    if (!confirmDeactivate) {
      setConfirmDeactivate(true);
      return;
    }
    const trimmed = reason.trim();
    if (trimmed.length < REASON_MIN || trimmed.length > REASON_MAX) {
      setError(`Укажите причину (${REASON_MIN}–${REASON_MAX} символов)`);
      return;
    }
    setError('');
    deactivateMutation.mutate(trimmed, {
      onSuccess: () => {
        setConfirmDeactivate(false);
        setReason('');
        invalidateBoth();
      },
      onError: (err) =>
        setError(describeError(err, 'Не удалось деактивировать')),
    });
  }

  function handleReactivate() {
    setError('');
    reactivateMutation.mutate(undefined, {
      onSuccess: () => invalidateBoth(),
      onError: (err) =>
        setError(describeError(err, 'Не удалось реактивировать')),
    });
  }

  // `StaffDetailResponse.roles` is `RoleInfoResponse[]` (id, name, isSystem).
  const detailRoles = Array.isArray(detail?.roles) ? detail.roles : [];
  const assignedRoleIds = new Set(detailRoles.map((r) => r.id));
  const availableRoles = roles.filter((r) => !assignedRoleIds.has(r.id));

  const fullName = detail
    ? [detail.firstName, detail.lastName].filter(Boolean).join(' ') || FALLBACK
    : '';
  const emailLabel = detail?.email || FALLBACK;
  const authTypeLabel = detail?.authType
    ? (AUTH_TYPE_LABELS[detail.authType] ?? detail.authType)
    : null;
  const createdAt = detail?.createdAt ? formatDateTime(detail.createdAt) : null;
  const deactivatedAt = detail?.deactivatedAt
    ? formatDateTime(detail.deactivatedAt)
    : null;

  const trimmedReasonLength = reason.trim().length;
  const reasonValid =
    trimmedReasonLength >= REASON_MIN && trimmedReasonLength <= REASON_MAX;
  const displayError =
    error ||
    (detailError ? describeError(detailError, 'Не удалось загрузить') : '');

  return (
    <Modal open={open} onClose={onClose} title="Сотрудник">
      {detailLoading && !detail && (
        <div className={styles.detailSection}>
          <div className={styles.skeletonRow} />
          <div className={styles.skeletonRow} />
          <div className={styles.skeletonRow} />
        </div>
      )}

      {detail && (
        <>
          <div className={styles.detailSection}>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Email</span>
              <span className={styles.detailValue}>{emailLabel}</span>
            </div>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Имя</span>
              <span className={styles.detailValue}>{fullName}</span>
            </div>
            {detail.position && (
              <div className={styles.detailRow}>
                <span className={styles.detailLabel}>Должность</span>
                <span className={styles.detailValue}>{detail.position}</span>
              </div>
            )}
            {detail.department && (
              <div className={styles.detailRow}>
                <span className={styles.detailLabel}>Отдел</span>
                <span className={styles.detailValue}>{detail.department}</span>
              </div>
            )}
            {authTypeLabel && (
              <div className={styles.detailRow}>
                <span className={styles.detailLabel}>Тип входа</span>
                <span className={styles.detailValue}>{authTypeLabel}</span>
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
            {createdAt && (
              <div className={styles.detailRow}>
                <span className={styles.detailLabel}>Создан</span>
                <span className={styles.detailValue}>{createdAt}</span>
              </div>
            )}
            {!detail.isActive && deactivatedAt && (
              <div className={styles.detailRow}>
                <span className={styles.detailLabel}>Деактивирован</span>
                <span className={styles.detailValue}>{deactivatedAt}</span>
              </div>
            )}
          </div>

          <div className={styles.rolesSection}>
            <p className={styles.rolesTitle}>Роли</p>
            <div className={styles.rolesList}>
              {detailRoles.map((role) => (
                <span key={role.id} className={styles.roleBadge}>
                  {role.name}
                  {!role.isSystem && (
                    <button
                      type="button"
                      className={styles.roleRemoveButton}
                      onClick={() => handleRevokeRole(role.id)}
                      disabled={mutating}
                      aria-label={`Удалить роль ${role.name}`}
                    >
                      ✕
                    </button>
                  )}
                </span>
              ))}
              {detailRoles.length === 0 && (
                <span className={styles.detailLabel}>Нет ролей</span>
              )}
            </div>

            {availableRoles.length > 0 && (
              <div className={styles.addRoleRow}>
                <select
                  value={selectedRoleId}
                  onChange={(e) => setSelectedRoleId(e.target.value)}
                  className={styles.addRoleSelect}
                  aria-label="Выбрать роль для назначения"
                  disabled={mutating}
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

          {detail.isActive && confirmDeactivate && (
            <div className={styles.reasonSection}>
              <label
                htmlFor="staff-deactivate-reason"
                className={styles.reasonLabel}
              >
                <span>Причина деактивации</span>
                <span className={styles.reasonCounter}>
                  {trimmedReasonLength}/{REASON_MAX}
                </span>
              </label>
              <textarea
                id="staff-deactivate-reason"
                value={reason}
                onChange={(e) => setReason(e.target.value.slice(0, REASON_MAX))}
                placeholder="Например: переведён в другой отдел, увольнение"
                className={styles.reasonInput}
                rows={3}
                maxLength={REASON_MAX}
                disabled={mutating}
                autoFocus
              />
            </div>
          )}

          <div className={styles.modalActions}>
            {detail.isActive ? (
              <button
                type="button"
                className={styles.deactivateButton}
                onClick={handleDeactivate}
                disabled={mutating || (confirmDeactivate && !reasonValid)}
              >
                {confirmDeactivate
                  ? deactivateMutation.isPending
                    ? 'Деактивация…'
                    : 'Подтвердить деактивацию'
                  : 'Деактивировать'}
              </button>
            ) : (
              <button
                type="button"
                className={styles.reactivateButton}
                onClick={handleReactivate}
                disabled={mutating}
              >
                {reactivateMutation.isPending
                  ? 'Реактивация…'
                  : 'Реактивировать'}
              </button>
            )}
          </div>
        </>
      )}

      {displayError && <div className={styles.modalError}>{displayError}</div>}
    </Modal>
  );
}
