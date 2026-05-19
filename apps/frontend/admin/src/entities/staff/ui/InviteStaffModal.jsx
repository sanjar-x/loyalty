'use client';

import { useEffect, useState } from 'react';

import { useRoles } from '@/entities/role';

import { copyToClipboard } from '@/shared/lib/utils';
import { Modal } from '@/shared/ui/Modal';

import { useInviteStaff } from '../api/mutations';
import styles from './styles/staff.module.css';

// Error-code map mirrors the actual codes thrown by the backend in
// `modules/identity/application/commands/invite_staff.py`. Keys must match the
// backend exactly — otherwise we'd fall back to the English `err.message`.
const INVITE_ERROR_CODES = {
  IDENTITY_ALREADY_EXISTS: 'Сотрудник с таким email уже существует',
  ACTIVE_INVITATION_EXISTS: 'Приглашение для этого email уже отправлено',
  ROLE_NOT_FOUND: 'Одна из выбранных ролей не найдена',
  INSUFFICIENT_PERMISSIONS: 'Недостаточно прав',
  PRIVILEGE_ESCALATION: 'Нельзя выдать роли выше своих',
  ACCOUNT_TYPE_MISMATCH: 'Эта роль предназначена для другого типа аккаунта',
  VALIDATION_ERROR: 'Проверьте введённые данные',
};

function describeError(err, fallback = 'Не удалось создать приглашение') {
  return INVITE_ERROR_CODES[err?.code] ?? err?.message ?? fallback;
}

function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

// `initialInvitation` short-circuits the form: when provided, the modal
// opens directly into the success-state (link + copy). Used by the
// resend flow in InvitationsTab — same UX as a fresh create, no extra
// component needed.
export function InviteStaffModal({
  open,
  onClose,
  onCreated,
  initialInvitation = null,
  title = 'Пригласить сотрудника',
}) {
  const { data: roles = [] } = useRoles();
  const inviteMutation = useInviteStaff();

  const [email, setEmail] = useState('');
  const [selectedRoleIds, setSelectedRoleIds] = useState([]);
  const [error, setError] = useState('');
  const [createdInvitation, setCreatedInvitation] = useState(null);
  const [linkCopied, setLinkCopied] = useState(false);

  useEffect(() => {
    if (open) {
      setEmail('');
      setSelectedRoleIds([]);
      setError('');
      // initialInvitation takes precedence — caller is reusing the
      // success UI for a freshly-resent invitation.
      setCreatedInvitation(initialInvitation);
      setLinkCopied(false);
    }
  }, [open, initialInvitation]);

  function toggleRole(roleId) {
    setSelectedRoleIds((prev) =>
      prev.includes(roleId)
        ? prev.filter((id) => id !== roleId)
        : [...prev, roleId],
    );
  }

  function handleSubmit(e) {
    e.preventDefault();
    if (!isValidEmail(email)) {
      setError('Введите корректный email');
      return;
    }
    if (selectedRoleIds.length === 0) {
      setError('Выберите хотя бы одну роль');
      return;
    }
    setError('');
    inviteMutation.mutate(
      { email: email.trim(), roleIds: selectedRoleIds },
      {
        onSuccess: (data) => {
          setCreatedInvitation(data);
          onCreated?.(data);
        },
        onError: (err) => setError(describeError(err)),
      },
    );
  }

  async function handleCopy() {
    if (!createdInvitation?.inviteUrl) return;
    await copyToClipboard(createdInvitation.inviteUrl);
    setLinkCopied(true);
    setTimeout(() => setLinkCopied(false), 1500);
  }

  return (
    <Modal open={open} onClose={onClose} title={title}>
      {createdInvitation ? (
        <div className={styles.detailSection}>
          <p className={styles.successText}>
            Приглашение отправлено. Ссылка действительна ограниченное время — её
            можно скопировать и переслать вручную.
          </p>
          <div className={styles.inviteLinkRow}>
            <code
              className={styles.inviteLink}
              title={createdInvitation.inviteUrl}
            >
              {createdInvitation.inviteUrl}
            </code>
            <button
              type="button"
              className={styles.copyButton}
              onClick={handleCopy}
            >
              {linkCopied ? 'Скопировано' : 'Копировать'}
            </button>
          </div>
          <div className={styles.modalActions}>
            <button
              type="button"
              className={styles.primaryButton}
              onClick={onClose}
            >
              Готово
            </button>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className={styles.detailSection}>
          <label className={styles.fieldLabel}>
            Email сотрудника
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@company.com"
              className={styles.fieldInput}
              required
              autoFocus
              disabled={inviteMutation.isPending}
            />
          </label>

          <div className={styles.fieldLabel}>
            Роли
            <div className={styles.rolesPickerList}>
              {roles.length === 0 ? (
                <span className={styles.detailLabel}>
                  Сначала создайте роли
                </span>
              ) : (
                roles.map((role) => (
                  <label key={role.id} className={styles.rolesPickerItem}>
                    <input
                      type="checkbox"
                      checked={selectedRoleIds.includes(role.id)}
                      onChange={() => toggleRole(role.id)}
                      disabled={inviteMutation.isPending}
                    />
                    <span>{role.name}</span>
                    {role.description && (
                      <span className={styles.detailLabel}>
                        — {role.description}
                      </span>
                    )}
                  </label>
                ))
              )}
            </div>
          </div>

          {error && <div className={styles.modalError}>{error}</div>}

          <div className={styles.modalActions}>
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={onClose}
              disabled={inviteMutation.isPending}
            >
              Отмена
            </button>
            <button
              type="submit"
              className={styles.primaryButton}
              disabled={
                inviteMutation.isPending ||
                !email ||
                selectedRoleIds.length === 0
              }
            >
              {inviteMutation.isPending ? 'Отправка…' : 'Отправить приглашение'}
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
}
