import AlertTriangleIcon from '@/assets/icons/alert-triangle.svg';
import InfoCircleIcon from '@/assets/icons/info-circle.svg';

import styles from './styles/staff.module.css';

// Two backend-surfaced data anomalies on a staff row:
//   accountTypeMismatch — warning (legacy data, needs migration).
//   !hasStaffMemberProfile — neutral info (incomplete provisioning).
// Both can be present on the same row; render in this order so the warning
// reads first.
export function hasStaffAnomaly(member) {
  if (!member) return false;
  return (
    Boolean(member.accountTypeMismatch) ||
    member.hasStaffMemberProfile === false
  );
}

function MismatchBadge() {
  return (
    <span
      className={`${styles.anomalyBadge} ${styles.anomalyBadgeWarning}`}
      title="Identity сохранён как CUSTOMER, но назначена staff-роль. Обычный invitation flow создаёт identity с account_type=STAFF; здесь данные несогласованы — сообщите команде для миграции."
    >
      <AlertTriangleIcon
        className={styles.anomalyBadgeIcon}
        aria-hidden="true"
      />
      Клиент с админ-ролью
    </span>
  );
}

function MissingProfileBadge() {
  return (
    <span
      className={`${styles.anomalyBadge} ${styles.anomalyBadgeNeutral}`}
      title="Identity провижен как сотрудник, но запись в staff_members не создалась (вероятно, outbox-событие не дошло). Профиль можно создать через invite-resend или ручной интерфейс (когда появится)."
    >
      <InfoCircleIcon className={styles.anomalyBadgeIcon} aria-hidden="true" />
      Профиль не создан
    </span>
  );
}

export function StaffAnomalyBadges({ member, className }) {
  if (!member) return null;
  const mismatch = Boolean(member.accountTypeMismatch);
  const missing = member.hasStaffMemberProfile === false;
  if (!mismatch && !missing) return null;

  return (
    <span className={className ?? styles.anomalyBadgeStack}>
      {mismatch && <MismatchBadge />}
      {missing && <MissingProfileBadge />}
    </span>
  );
}

// Detail-page banner. Shown above the profile fields so the admin
// understands why some columns are blank before they try to edit.
export function StaffAnomalyBanner({ member }) {
  if (!hasStaffAnomaly(member)) return null;
  const mismatch = Boolean(member.accountTypeMismatch);
  const missing = member.hasStaffMemberProfile === false;
  return (
    <div
      role="alert"
      className={`${styles.anomalyBanner} ${
        mismatch ? styles.anomalyBannerWarning : styles.anomalyBannerNeutral
      }`}
    >
      <AlertTriangleIcon
        className={styles.anomalyBannerIcon}
        aria-hidden="true"
      />
      <div className={styles.anomalyBannerBody}>
        <p className={styles.anomalyBannerTitle}>
          {mismatch
            ? 'Несогласованный тип аккаунта'
            : 'Профиль сотрудника не создан'}
        </p>
        <p className={styles.anomalyBannerText}>
          {mismatch && (
            <>
              Identity сохранён как <code>CUSTOMER</code>, но назначена
              staff-роль. Обычный invitation flow создаёт identity с
              <code> account_type=STAFF</code>; здесь данные несогласованы.
              Сообщите команде для миграции — не редактируйте профиль вручную.
            </>
          )}
          {missing && !mismatch && (
            <>
              Identity провижен как сотрудник, но запись в{' '}
              <code>staff_members</code> не создалась (вероятно, outbox-событие
              не дошло). Профиль можно создать через invite-resend или ручной
              интерфейс (когда появится).
            </>
          )}
          {missing && mismatch && (
            <>
              {' '}
              Дополнительно: запись в <code>staff_members</code> отсутствует —
              поля имени/фамилии/должности пока пустые.
            </>
          )}
        </p>
      </div>
    </div>
  );
}
