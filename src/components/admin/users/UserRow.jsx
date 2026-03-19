import { Badge } from '@/components/ui/Badge';
import styles from '@/app/admin/users/page.module.css';

export function UserRow({ user, onEdit }) {
  return (
    <div className={styles.row}>
      <button
        type="button"
        className={styles.emailCell}
        onClick={() => onEdit(user)}
      >
        {user.email}
      </button>

      <div className={styles.cell}>
        {[user.firstName, user.lastName].filter(Boolean).join(' ') || '—'}
      </div>

      <div className={styles.rolesCell}>
        {user.roles && user.roles.length > 0 ? (
          user.roles.map((role) => (
            <Badge key={role.id} variant="muted">
              {role.name}
            </Badge>
          ))
        ) : (
          <span className={styles.cell} style={{ color: '#878b93' }}>
            —
          </span>
        )}
      </div>

      <div className={styles.statusCell}>
        <span
          className={`${styles.statusDot} ${
            user.isActive ? styles.statusActive : styles.statusInactive
          }`}
        />
        {user.isActive ? 'Активен' : 'Неактивен'}
      </div>

      <div>
        <button
          type="button"
          className={styles.editButton}
          onClick={() => onEdit(user)}
          aria-label={`Редактировать ${user.email}`}
        >
          Ред.
        </button>
      </div>
    </div>
  );
}
