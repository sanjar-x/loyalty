'use client';

import { Badge } from '@/shared/ui/Badge';
import dayjs from '@/shared/lib/dayjs';
import { formatDateTimeLong } from '@/shared/lib/utils';

import { INVITATION_STATUS_LABELS } from '../api/invitations';
import styles from './styles/staff.module.css';

const FALLBACK = '—';

// `Badge` only ships with default/china/dark/muted variants, so we render the
// invitation status as a status-coloured pill via local CSS classes instead.
const STATUS_PILL_CLASS = {
  PENDING: styles.statusPillPending,
  ACCEPTED: styles.statusPillAccepted,
  REVOKED: styles.statusPillRevoked,
  EXPIRED: styles.statusPillExpired,
};

const EXPIRY_SOON_MS = 24 * 60 * 60 * 1000;

const formatDate = (value) => formatDateTimeLong(value, { fallback: FALLBACK });

// Returns one of { kind: 'fresh' | 'soon' | 'past', label }. Caller
// decides whether to surface a chip. We only render chips for PENDING
// rows — terminal statuses (ACCEPTED/REVOKED/EXPIRED) already speak for
// themselves and a second chip would be noise.
function computeExpiry(expiresAt) {
  if (!expiresAt) return { kind: 'fresh' };
  const target = dayjs(expiresAt);
  if (!target.isValid()) return { kind: 'fresh' };
  const now = dayjs();
  if (target.isBefore(now)) {
    return { kind: 'past', label: `Истекло ${target.fromNow()}` };
  }
  const diff = target.valueOf() - now.valueOf();
  if (diff <= EXPIRY_SOON_MS) {
    return { kind: 'soon', label: `Истекает ${target.fromNow()}` };
  }
  return { kind: 'fresh' };
}

export function InvitationRow({
  invitation,
  onRevoke,
  onResend,
  onOpenProfile,
  isRevoking,
  isResending,
}) {
  const statusLabel =
    INVITATION_STATUS_LABELS[invitation.status] ?? invitation.status;
  const statusClass =
    STATUS_PILL_CLASS[invitation.status] ?? styles.statusPillRevoked;

  const canRevoke = invitation.status === 'PENDING';
  // Backend treats resend as "create a new invitation row for the same
  // email", which is meaningful for any non-accepted state — including
  // PENDING (admin lost the link before sending) and the terminal-but-
  // recoverable states (REVOKED / EXPIRED).
  const canResend = invitation.status !== 'ACCEPTED';
  // Backend invitation DTO does not carry identityId, so we deep-link to
  // the staff tab by email instead — the page handler renders the right
  // CTA. Anything in ACCEPTED state may have a staff_members row.
  const canOpenProfile = invitation.status === 'ACCEPTED';

  const roles = Array.isArray(invitation.roles) ? invitation.roles : [];
  const expiry =
    invitation.status === 'PENDING'
      ? computeExpiry(invitation.expiresAt)
      : null;

  return (
    <div className={styles.invitationRow}>
      <div className={styles.cell}>
        <span className={styles.primary}>{invitation.email}</span>
        {invitation.invitedByEmail && (
          <span className={styles.secondary}>
            от {invitation.invitedByEmail}
          </span>
        )}
      </div>

      <div className={styles.rolesCell}>
        {roles.length > 0 ? (
          roles.map((name) => (
            <Badge key={name} variant="muted">
              {name}
            </Badge>
          ))
        ) : (
          <span className={styles.secondary}>{FALLBACK}</span>
        )}
      </div>

      <div className={styles.cell}>
        <span className={`${styles.statusPill} ${statusClass}`}>
          {statusLabel}
        </span>
      </div>

      <div className={styles.dateCell}>
        <span className={styles.primary}>
          Создано: {formatDate(invitation.createdAt)}
        </span>
        <span className={styles.secondary}>
          {invitation.status === 'PENDING' ? 'Истекает' : 'Истекало'}:{' '}
          {formatDate(invitation.expiresAt)}
        </span>
        {expiry?.kind === 'soon' && (
          <span className={`${styles.expiryChip} ${styles.expiryChipSoon}`}>
            {expiry.label}
          </span>
        )}
        {expiry?.kind === 'past' && (
          <span className={`${styles.expiryChip} ${styles.expiryChipPast}`}>
            {expiry.label}
          </span>
        )}
      </div>

      <div className={styles.actionsCell}>
        {/* Destructive action goes last so the operator can't blow through
            it on a hurried Tab — Resend / Open Profile come first. */}
        {canResend && (
          <button
            type="button"
            className={styles.resendButton}
            onClick={() => onResend?.(invitation)}
            disabled={isResending}
            title="Создаст новую ссылку. Старое приглашение будет отозвано автоматически."
          >
            {isResending ? 'Отправка…' : 'Переотправить'}
          </button>
        )}
        {canOpenProfile && (
          <button
            type="button"
            className={styles.openProfileButton}
            onClick={() => onOpenProfile?.(invitation)}
          >
            Открыть профиль
          </button>
        )}
        {canRevoke && (
          <button
            type="button"
            className={styles.revokeButton}
            onClick={() => onRevoke?.(invitation)}
            disabled={isRevoking}
          >
            {isRevoking ? 'Отзыв…' : 'Отозвать'}
          </button>
        )}
      </div>
    </div>
  );
}
