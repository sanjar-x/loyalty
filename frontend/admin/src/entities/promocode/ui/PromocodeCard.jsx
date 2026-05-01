import BagIcon from '@/assets/icons/bag.svg';
import dayjs from '@/shared/lib/dayjs';
import styles from './styles/promocodes.module.css';

function formatDiscount(discount) {
  if (!discount) return '';
  if (discount.type === 'percent') {
    return `-${discount.value}%`;
  }
  return `-${Number(discount.value || 0).toLocaleString('ru-RU')}₽`;
}

function StatsIcon() {
  return (
    <svg
      className={styles.actionIcon}
      viewBox="0 0 26 26"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M16.25 24.6457H9.74996C3.86746 24.6457 1.35413 22.1323 1.35413 16.2498V9.74984C1.35413 3.86734 3.86746 1.354 9.74996 1.354H16.25C22.1325 1.354 24.6458 3.86734 24.6458 9.74984V16.2498C24.6458 22.1323 22.1325 24.6457 16.25 24.6457ZM9.74996 2.979C4.75579 2.979 2.97913 4.75567 2.97913 9.74984V16.2498C2.97913 21.244 4.75579 23.0207 9.74996 23.0207H16.25C21.2441 23.0207 23.0208 21.244 23.0208 16.2498V9.74984C23.0208 4.75567 21.2441 2.979 16.25 2.979H9.74996Z"
        fill="#292D32"
      />
      <path
        d="M7.94079 16.51C7.76746 16.51 7.59413 16.4558 7.44246 16.3367C7.08496 16.0658 7.01996 15.5567 7.29079 15.1992L9.86912 11.8517C10.1833 11.4508 10.6275 11.1908 11.1366 11.1258C11.635 11.0608 12.1441 11.2017 12.545 11.5158L14.5275 13.0758C14.6033 13.1408 14.6791 13.1408 14.7333 13.13C14.7766 13.13 14.8525 13.1083 14.9175 13.0217L17.42 9.79334C17.6908 9.43584 18.2108 9.37084 18.5575 9.65251C18.915 9.92334 18.98 10.4325 18.6983 10.79L16.1958 14.0183C15.8816 14.4192 15.4375 14.6792 14.9283 14.7333C14.4191 14.7983 13.9208 14.6575 13.52 14.3433L11.5375 12.7833C11.4616 12.7183 11.375 12.7183 11.3316 12.7292C11.2883 12.7292 11.2125 12.7508 11.1475 12.8375L8.56913 16.185C8.42829 16.4017 8.18996 16.51 7.94079 16.51Z"
        fill="#292D32"
      />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg
      className={styles.actionIcon}
      width="18"
      height="18"
      viewBox="0 0 17 19"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M10.1798 7.4158V14.0269M6.42981 7.4158V14.0269M2.67981 3.63802V14.7825C2.67981 15.8403 2.67981 16.3689 2.88417 16.773C3.06393 17.1284 3.35057 17.4179 3.70337 17.599C4.10406 17.8047 4.62887 17.8047 5.67691 17.8047H10.9327C11.9808 17.8047 12.5048 17.8047 12.9055 17.599C13.2583 17.4179 13.5459 17.1284 13.7256 16.773C13.9298 16.3693 13.9298 15.8412 13.9298 14.7854V3.63802M2.67981 3.63802H4.55481M2.67981 3.63802H0.80481M4.55481 3.63802H12.0548M4.55481 3.63802C4.55481 2.75791 4.55481 2.31807 4.69754 1.97095C4.88784 1.50812 5.25261 1.14018 5.71204 0.948471C6.05661 0.804688 6.49367 0.804688 7.36731 0.804688H9.24231C10.1159 0.804688 10.5528 0.804688 10.8973 0.948471C11.3568 1.14018 11.7217 1.50812 11.912 1.97095C12.0547 2.31807 12.0548 2.75791 12.0548 3.63802M12.0548 3.63802H13.9298M13.9298 3.63802H15.8048"
        stroke="currentColor"
        strokeWidth="1.60973"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function PromocodeCard({ promo, onDelete }) {
  const expiresLabel = promo.expiresAt
    ? `до ${dayjs(promo.expiresAt).format('DD.MM.YYYY')}`
    : 'без срока';

  return (
    <article className={styles.card}>
      <div className={styles.cardRow}>
        <div className={styles.mainCell}>
          <div className={styles.discountPill}>
            {formatDiscount(promo.discount)}
          </div>
          <span className={styles.code}>Промокод {promo.code}</span>
        </div>

        <div className={styles.condition}>{promo.condition}</div>

        <div className={styles.meta}>{expiresLabel}</div>

        <div className={styles.usesCell}>
          <BagIcon className={styles.usesIcon} />
          <span className={styles.usesValue}>
            {promo.uses?.value?.toLocaleString('ru-RU') ?? 0}
            {promo.uses?.delta > 0 ? (
              <span className={styles.delta}>
                +{promo.uses.delta.toLocaleString('ru-RU')}
              </span>
            ) : null}
          </span>
        </div>

        <div className={styles.actions}>
          <button
            type="button"
            className={styles.iconButton}
            aria-label="Статистика"
          >
            <StatsIcon />
          </button>
          <button
            type="button"
            className={styles.iconButton}
            aria-label="Удалить"
            onClick={() => onDelete(promo.id)}
          >
            <TrashIcon />
          </button>
        </div>
      </div>
    </article>
  );
}
