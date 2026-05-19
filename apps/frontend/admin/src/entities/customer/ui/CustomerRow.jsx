import dayjs from '@/shared/lib/dayjs';

import styles from './styles/customers.module.css';

const FALLBACK = '—';
const ID_VISIBLE_PREFIX = 9;

const AVATAR_PALETTE = [
  ['#ffd6a8', '#f7a25b'],
  ['#e0e0e0', '#bdbdbd'],
  ['#cfe7c8', '#7bb775'],
  ['#fad0e2', '#d989a9'],
  ['#cfe5fb', '#6f9fd6'],
  ['#fce7c0', '#caa66b'],
];

function avatarPaletteFor(seed) {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash * 31 + seed.charCodeAt(i)) | 0;
  }
  const idx = Math.abs(hash) % AVATAR_PALETTE.length;
  return AVATAR_PALETTE[idx];
}

function avatarInitials({ firstName, lastName, username, email }) {
  const fromName = [firstName, lastName].filter(Boolean).join(' ').trim();
  if (fromName) {
    const parts = fromName.split(/\s+/);
    return (parts[0][0] + (parts[1]?.[0] ?? '')).toUpperCase();
  }
  if (username) return username.slice(0, 2).toUpperCase();
  if (email) return email.slice(0, 2).toUpperCase();
  return '??';
}

function formatId(identityId) {
  if (!identityId) return FALLBACK;
  // Shorten UUIDs for the column. Keeps the layout aligned with the Figma
  // numeric-style "ID 707635394" without losing copyability on hover.
  return identityId.replace(/-/g, '').slice(0, ID_VISIBLE_PREFIX).toUpperCase();
}

function formatDate(value) {
  if (!value) return FALLBACK;
  const m = dayjs(value);
  return m.isValid() ? m.format('D MMMM HH:mm') : FALLBACK;
}

function ProfileIcon(props) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      {...props}
    >
      <circle cx="12" cy="8" r="3.5" stroke="currentColor" strokeWidth="1.6" />
      <path
        d="M5 19c1.4-3 4-4.5 7-4.5s5.6 1.5 7 4.5"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

function WaveIcon(props) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      {...props}
    >
      <path
        d="M3 12c2-3 4-3 6 0s4 3 6 0 4-3 6 0"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function FollowersIcon(props) {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      {...props}
    >
      <circle cx="10" cy="8" r="3.5" stroke="currentColor" strokeWidth="1.5" />
      <path
        d="M3 19c1.2-3 3.5-4.5 7-4.5s5.8 1.5 7 4.5"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <path
        d="M18 7v6M21 10h-6"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

function BagIcon(props) {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      {...props}
    >
      <path
        d="M5 8h14l-1 12a2 2 0 01-2 2H8a2 2 0 01-2-2L5 8z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path
        d="M9 8V6a3 3 0 016 0v2"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function CustomerRow({ user, onEdit, onChat }) {
  const fullName = [user.firstName, user.lastName].filter(Boolean).join(' ');
  const usernameLabel = user.username
    ? `@${user.username}`
    : (user.email ?? FALLBACK);

  const seed = user.identityId || user.username || user.email || 'user';
  const [bgFrom, bgTo] = avatarPaletteFor(seed);
  const initials = avatarInitials(user);

  // Source UTM ('start=bio') and follower/order counts are not exposed on the
  // current `/admin/customers` projection. Render placeholders today; once the
  // backend adds `acquisitionSource` / `referralCount` / `orderCount`, swap
  // them in here without touching the layout.
  const source = user.acquisitionSource ?? null;
  const referralsCount = user.referralCount ?? 0;
  const referralsDelta = user.referralCountDelta ?? 0;
  const ordersCount = user.orderCount ?? 0;
  const ordersDelta = user.orderCountDelta ?? 0;

  return (
    <div className={styles.row}>
      <div className={styles.userCell}>
        <button
          type="button"
          className={styles.avatar}
          style={{ background: `linear-gradient(135deg, ${bgFrom}, ${bgTo})` }}
          onClick={() => onEdit(user)}
          aria-label={`Открыть карточку ${usernameLabel}`}
        >
          <span aria-hidden="true">{initials}</span>
        </button>
        <button
          type="button"
          className={styles.usernameButton}
          onClick={() => onEdit(user)}
          title={fullName || user.email || ''}
        >
          {usernameLabel}
        </button>
      </div>

      <span className={styles.idCell} title={user.identityId}>
        ID&nbsp;{formatId(user.identityId)}
      </span>

      <span className={styles.dateCell}>{formatDate(user.createdAt)}</span>

      <span className={styles.sourceCell}>
        {source ? (
          <span className={styles.sourceLink}>start={source}</span>
        ) : (
          <span className={styles.sourceMuted}>{FALLBACK}</span>
        )}
      </span>

      <span className={styles.statCell}>
        <FollowersIcon className={styles.statIcon} />
        <span className={styles.statValue}>{referralsCount}</span>
        {referralsDelta > 0 && (
          <span className={styles.statDelta}>+{referralsDelta}</span>
        )}
      </span>

      <span className={styles.statCell}>
        <BagIcon className={styles.statIcon} />
        <span className={styles.statValue}>{ordersCount}</span>
        {ordersDelta > 0 && (
          <span className={styles.statDelta}>+{ordersDelta}</span>
        )}
      </span>

      <div className={styles.actionsCell}>
        <button
          type="button"
          className={styles.actionIconButton}
          onClick={() => onEdit(user)}
          aria-label={`Открыть профиль ${usernameLabel}`}
          title="Профиль"
        >
          <ProfileIcon className={styles.actionIcon} />
        </button>
        <button
          type="button"
          className={styles.actionIconButton}
          onClick={() => onEdit(user)}
          aria-label={`Активность ${usernameLabel}`}
          title="Активность"
        >
          <WaveIcon className={styles.actionIcon} />
        </button>
        <button
          type="button"
          className={styles.actionChatButton}
          onClick={() => onChat?.(user)}
          aria-label={`Написать ${usernameLabel}`}
        >
          Чат
        </button>
      </div>

      {!user.isActive && (
        <span
          className={styles.inactiveBadge}
          aria-label="Аккаунт деактивирован"
        >
          Неактивен
        </span>
      )}
    </div>
  );
}
