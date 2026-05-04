import { Badge } from '@/shared/ui/Badge';
import dayjs from '@/shared/lib/dayjs';

import styles from './styles/staff.module.css';

const FALLBACK = '—';

function formatDate(value) {
  if (!value) return FALLBACK;
  const m = dayjs(value);
  return m.isValid() ? m.format('D MMMM YYYY') : FALLBACK;
}

export function StaffRow({ member, onOpen }) {
  // `StaffListItemResponse.roles` is `string[]` of role names — same shape as
  // `AdminIdentityResponse`. Detail endpoint returns `RoleInfoResponse[]`.
  const roleNames = Array.isArray(member.roles) ? member.roles : [];
  const fullName = [member.firstName, member.lastName]
    .filter(Boolean)
    .join(' ');
  const emailLabel = member.email || FALLBACK;

  return (
    <button
      type="button"
      className={styles.row}
      onClick={() => onOpen(member)}
      aria-label={`Открыть ${fullName || emailLabel}`}
    >
      <div className={styles.cell}>
        <span className={styles.primary}>{fullName || FALLBACK}</span>
        <span className={styles.secondary}>{emailLabel}</span>
      </div>

      <div className={styles.cell}>
        <span className={styles.primary}>{member.position || FALLBACK}</span>
        <span className={styles.secondary}>
          {member.department || FALLBACK}
        </span>
      </div>

      <div className={styles.rolesCell}>
        {roleNames.length > 0 ? (
          roleNames.map((name) => (
            <Badge key={name} variant="muted">
              {name}
            </Badge>
          ))
        ) : (
          <span className={styles.secondary}>{FALLBACK}</span>
        )}
      </div>

      <div className={styles.statusCell}>
        <span
          className={`${styles.statusDot} ${
            member.isActive ? styles.statusActive : styles.statusInactive
          }`}
        />
        {member.isActive ? 'Активен' : 'Неактивен'}
      </div>

      <div className={styles.dateCell}>{formatDate(member.createdAt)}</div>
    </button>
  );
}
