'use client';

import { useEffect, useState } from 'react';

import dayjs from '@/shared/lib/dayjs';
import { Modal } from '@/shared/ui/Modal';

import { useDeactivateCustomer, useReactivateCustomer } from '../api/mutations';
import { useCustomer } from '../api/queries';
import styles from './styles/customers.module.css';

const CUSTOMER_ERROR_CODES = {
  IDENTITY_NOT_FOUND: 'Пользователь не найден',
  IDENTITY_ALREADY_DEACTIVATED: 'Аккаунт уже деактивирован',
  SELF_DEACTIVATION_FORBIDDEN: 'Нельзя деактивировать свой аккаунт',
  INSUFFICIENT_PERMISSIONS: 'Недостаточно прав',
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

const AUTH_METHOD_LABELS = {
  email_password: 'Email + пароль',
  telegram: 'Telegram',
  oidc: 'OIDC',
};

function describeError(err, fallback = 'Произошла ошибка') {
  return CUSTOMER_ERROR_CODES[err?.code] ?? err?.message ?? fallback;
}

function formatDateTime(value) {
  if (!value) return null;
  const m = dayjs(value);
  return m.isValid() ? m.format('D MMMM YYYY, HH:mm') : null;
}

function formatAuthMethod(method) {
  return AUTH_METHOD_LABELS[method] ?? method;
}

export function CustomerDetailModal({ identityId, open, onClose, onUpdate }) {
  const enabled = open && Boolean(identityId);

  const {
    data: detail,
    isPending: detailLoading,
    error: detailError,
  } = useCustomer(enabled ? identityId : null);

  const [error, setError] = useState('');
  const [confirmDeactivate, setConfirmDeactivate] = useState(false);
  const [reason, setReason] = useState('');

  // Reset transient UI state every time the modal opens against a new user.
  useEffect(() => {
    if (open && identityId) {
      setConfirmDeactivate(false);
      setReason('');
      setError('');
    }
  }, [open, identityId]);

  const deactivateMutation = useDeactivateCustomer(identityId);
  const reactivateMutation = useReactivateCustomer(identityId);

  const mutating = deactivateMutation.isPending || reactivateMutation.isPending;

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
        onUpdate?.();
      },
      onError: (err) =>
        setError(describeError(err, 'Не удалось деактивировать')),
    });
  }

  function handleReactivate() {
    setError('');
    reactivateMutation.mutate(undefined, {
      onSuccess: () => onUpdate?.(),
      onError: (err) =>
        setError(describeError(err, 'Не удалось реактивировать')),
    });
  }

  // `CustomerDetailResponse.roles` is RoleInfoResponse[] with `id`/`name`.
  const detailRoles = Array.isArray(detail?.roles) ? detail.roles : [];
  const authMethods = Array.isArray(detail?.authMethods)
    ? detail.authMethods
    : [];

  const fullName = detail
    ? [detail.firstName, detail.lastName].filter(Boolean).join(' ') || FALLBACK
    : '';
  const emailLabel = detail?.email || FALLBACK;
  const usernameLabel = detail?.username ? `@${detail.username}` : null;
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
              <span className={styles.detailValue}>{emailLabel}</span>
            </div>
            {usernameLabel && (
              <div className={styles.detailRow}>
                <span className={styles.detailLabel}>Username</span>
                <span className={styles.detailValue}>{usernameLabel}</span>
              </div>
            )}
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Имя</span>
              <span className={styles.detailValue}>{fullName}</span>
            </div>
            {detail.phone && (
              <div className={styles.detailRow}>
                <span className={styles.detailLabel}>Телефон</span>
                <span className={styles.detailValue}>{detail.phone}</span>
              </div>
            )}
            {authTypeLabel && (
              <div className={styles.detailRow}>
                <span className={styles.detailLabel}>Тип аккаунта</span>
                <span className={styles.detailValue}>{authTypeLabel}</span>
              </div>
            )}
            {authMethods.length > 0 && (
              <div className={styles.detailRow}>
                <span className={styles.detailLabel}>Способы входа</span>
                <span className={styles.detailValue}>
                  {authMethods.map(formatAuthMethod).join(', ')}
                </span>
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
                <span className={styles.detailLabel}>Дата регистрации</span>
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

          {detailRoles.length > 0 && (
            <div className={styles.rolesSection}>
              <p className={styles.rolesTitle}>Роли</p>
              <div className={styles.rolesList}>
                {detailRoles.map((role) => (
                  <span key={role.id} className={styles.roleBadge}>
                    {role.name}
                  </span>
                ))}
              </div>
            </div>
          )}

          {detail.isActive && confirmDeactivate && (
            <div className={styles.reasonSection}>
              <label htmlFor="deactivate-reason" className={styles.reasonLabel}>
                <span>Причина деактивации</span>
                <span className={styles.reasonCounter}>
                  {trimmedReasonLength}/{REASON_MAX}
                </span>
              </label>
              <textarea
                id="deactivate-reason"
                value={reason}
                onChange={(e) => setReason(e.target.value.slice(0, REASON_MAX))}
                placeholder="Например: нарушение правил, дубликат аккаунта…"
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
