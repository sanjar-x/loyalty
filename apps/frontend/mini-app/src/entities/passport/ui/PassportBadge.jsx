'use client';

import styles from './PassportBadge.module.css';

/**
 * Validation-status badge for a Passport row. Backend `validationStatus`
 * is a free-form string today, but follows a small enum in practice:
 *   • 'pending'   — backfilled / freshly created, awaiting DaData / DobroPost
 *   • 'verified'  — passed external validation
 *   • 'invalid'   — explicit failure, see `validationFailedReason`
 *
 * Anything else falls back to a neutral "pending" treatment so a future
 * backend status (e.g. 'expired') doesn't crash the UI.
 */
const STATUS_LABEL = {
  pending: 'Проверяем',
  verified: 'Подтверждён',
  invalid: 'Ошибка проверки',
};

const STATUS_CLASS = {
  pending: styles.pending,
  verified: styles.verified,
  invalid: styles.invalid,
};

export default function PassportBadge({ status, reason }) {
  const key = STATUS_LABEL[status] ? status : 'pending';
  const cls = STATUS_CLASS[key] ?? STATUS_CLASS.pending;
  const label = STATUS_LABEL[key];
  const title = key === 'invalid' && reason ? reason : undefined;
  return (
    <span className={`${styles.badge} ${cls}`} title={title} role="status">
      {label}
    </span>
  );
}
