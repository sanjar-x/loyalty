import { Badge } from '@/shared/ui/Badge';
import { formatDateTimeLong } from '@/shared/lib/utils';

import { StaffAnomalyBadges } from './StaffAnomalyBadges';
import styles from './styles/staff.module.css';

const FALLBACK = '—';
const PROFILE_MISSING_LABEL = 'Профиль не заполнен';

// Deterministic accent palette — avatars are picked by hashing the email/id so
// the same staff member keeps the same colour across renders and pages.
const AVATAR_PALETTE = [
  { bg: '#dde7ff', fg: '#1f3c8a' },
  { bg: '#fde7e0', fg: '#92381c' },
  { bg: '#e1f3d6', fg: '#2f6b1a' },
  { bg: '#fcefd0', fg: '#7a5316' },
  { bg: '#f0e0fc', fg: '#5b1f8a' },
  { bg: '#d6f0ef', fg: '#1b6663' },
];

function hashString(input) {
  let h = 0;
  for (let i = 0; i < input.length; i += 1) {
    h = (h * 31 + input.charCodeAt(i)) | 0;
  }
  return Math.abs(h);
}

function pickAvatarColor(seed) {
  if (!seed) return AVATAR_PALETTE[0];
  return AVATAR_PALETTE[hashString(seed) % AVATAR_PALETTE.length];
}

function initialsFrom(firstName, lastName, email) {
  const first = (firstName || '').trim();
  const last = (lastName || '').trim();
  if (first || last) {
    const a = first.charAt(0);
    const b = last.charAt(0);
    return (a + b).toUpperCase() || a.toUpperCase() || b.toUpperCase();
  }
  // Email fallback — first letter of the local part. Anything weirder
  // (only digits, only symbols) collapses to a placeholder glyph.
  const local = (email || '').split('@')[0] || '';
  return local.charAt(0).toUpperCase() || '?';
}

export function StaffRow({ member, onOpen }) {
  // `StaffListItemResponse.roles` is `string[]` of role names — same shape as
  // `AdminIdentityResponse`. Detail endpoint returns `RoleInfoResponse[]`.
  const roleNames = Array.isArray(member.roles) ? member.roles : [];
  const fullName = [member.firstName, member.lastName]
    .filter(Boolean)
    .join(' ');
  const emailLabel = member.email || FALLBACK;
  const profileMissing = member.hasStaffMemberProfile === false;
  // No profile == no `staff_members` row, which is also what
  // first_name/last_name nullability proxies. Show a dedicated placeholder
  // instead of a generic em dash so the operator knows it's not just "blank
  // because nobody filled it in".
  const nameLabel =
    fullName || (profileMissing ? PROFILE_MISSING_LABEL : FALLBACK);
  const initials = initialsFrom(
    member.firstName,
    member.lastName,
    member.email,
  );
  const avatarColor = pickAvatarColor(member.email || member.identityId);

  return (
    <button
      type="button"
      className={styles.row}
      onClick={() => onOpen(member)}
      aria-label={`Открыть ${fullName || emailLabel}`}
    >
      <div className={styles.cell}>
        <div className={styles.personCell}>
          <span
            className={styles.avatar}
            style={{ background: avatarColor.bg, color: avatarColor.fg }}
            aria-hidden="true"
          >
            {initials}
          </span>
          <div className={styles.personInfo}>
            <span className={styles.nameLine}>
              <span
                className={`${styles.primary} ${
                  profileMissing && !fullName ? styles.primaryPlaceholder : ''
                }`}
              >
                {nameLabel}
              </span>
              <StaffAnomalyBadges member={member} />
            </span>
            <span className={styles.secondary}>{emailLabel}</span>
          </div>
        </div>
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

      <div className={styles.dateCell}>
        {formatDateTimeLong(member.createdAt)}
      </div>
    </button>
  );
}
