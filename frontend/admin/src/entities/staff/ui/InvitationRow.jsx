'use client';

import { Badge } from '@/shared/ui/Badge';
import dayjs from '@/shared/lib/dayjs';

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

function formatDate(value) {
  if (!value) return FALLBACK;
  const m = dayjs(value);
  return m.isValid() ? m.format('D MMMM YYYY, HH:mm') : FALLBACK;
}

export function InvitationRow({ invitation, onRevoke, isRevoking }) {
  const statusLabel =
    INVITATION_STATUS_LABELS[invitation.status] ?? invitation.status;
  const statusClass =
    STATUS_PILL_CLASS[invitation.status] ?? styles.statusPillRevoked;
  const canRevoke = invitation.status === 'PENDING';
  const roles = Array.isArray(invitation.roles) ? invitation.roles : [];

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
      </div>

      <div className={styles.actionsCell}>
        {canRevoke && (
          <button
            type="button"
            className={styles.revokeButton}
            onClick={() => onRevoke(invitation)}
            disabled={isRevoking}
          >
            {isRevoking ? 'Отзыв…' : 'Отозвать'}
          </button>
        )}
      </div>
    </div>
  );
}
