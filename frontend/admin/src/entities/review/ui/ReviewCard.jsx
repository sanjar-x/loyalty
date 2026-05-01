import Image from 'next/image';
import { cn, copyToClipboard } from '@/shared/lib/utils';
import { Star } from '@/shared/ui/StarsRow';
import ChevronIcon from '@/assets/icons/chevron.svg';
import styles from './ReviewCard.module.css';

const DEFAULT_AVATAR_SRC = '/avatars/default.png';
const DEFAULT_BRAND_LOGO_SRC = '/avatars/testBrandLogo.png';

function StarsRow({ rating }) {
  const safe = Math.max(0, Math.min(5, Number(rating) || 0));
  return (
    <span className={styles.stars} aria-label={`Оценка ${safe} из 5`}>
      {Array.from({ length: 5 }, (_, idx) => (
        <Star
          key={idx}
          filled={idx < safe}
          className={cn(
            styles.star,
            idx < safe ? styles.starFilled : styles.starEmpty,
          )}
        />
      ))}
    </span>
  );
}

function TrashIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 17 19"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={styles.actionIcon}
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

export default function ReviewCard({
  product,
  review,
  order,
  expanded = false,
  onOpenOrder,
  onDelete,
  onToggleExpand,
}) {
  const brandLogoSrc =
    product?.brandLogoSrc || product?.brandLogoUrl || DEFAULT_BRAND_LOGO_SRC;
  const productImage = product?.image || '';
  const avatarSrc =
    review?.user?.avatar || review?.user?.avatarUrl || DEFAULT_AVATAR_SRC;

  const originLabel = order?.originLabel || order?.origin || '';

  return (
    <article className={styles.card}>
      <div className={styles.grid}>
        {/* Column 1 — Product */}
        <div className={styles.productCol}>
          <div className={styles.brandRow}>
            <div className={styles.brandLogo} aria-hidden="true">
              <Image
                src={brandLogoSrc}
                alt=""
                width={56}
                height={56}
                className={styles.brandLogoImg}
                onError={(e) => {
                  if (e.currentTarget.src.endsWith(DEFAULT_BRAND_LOGO_SRC))
                    return;
                  e.currentTarget.src = DEFAULT_BRAND_LOGO_SRC;
                }}
              />
            </div>
            <div className={styles.brandText}>
              <p className={styles.brandName}>{product?.brandName || ''}</p>
              <p className={styles.brandLabel}>Бренд</p>
            </div>
          </div>

          <div className={styles.productRow}>
            {productImage ? (
              <Image
                src={productImage}
                alt={product?.title || ''}
                width={64}
                height={64}
                className={styles.productImage}
              />
            ) : (
              <div className={styles.productImage} aria-hidden="true" />
            )}
            <div className={styles.productText}>
              <p className={styles.productTitle}>{product?.title || ''}</p>
              <p className={styles.productSize}>
                Размер: {product?.size || ''}
              </p>
            </div>
          </div>
        </div>

        {/* Column 2 — Review */}
        <div className={styles.reviewCol}>
          <div className={styles.userRow}>
            {avatarSrc ? (
              <Image
                src={avatarSrc}
                alt={review?.user?.name || ''}
                width={38}
                height={38}
                className={styles.avatar}
                onError={(e) => {
                  if (e.currentTarget.src.endsWith(DEFAULT_AVATAR_SRC)) return;
                  e.currentTarget.src = DEFAULT_AVATAR_SRC;
                }}
              />
            ) : (
              <div className={styles.avatar} aria-hidden="true" />
            )}

            <div className={styles.userMeta}>
              <StarsRow rating={review?.rating} />
              <div className={styles.userLine}>
                <p className={styles.userName}>{review?.user?.name || ''}</p>
                <span className={styles.metaDot}>•</span>
                <span className={styles.userDate}>
                  {review?.dateLabel || ''}
                </span>
              </div>
            </div>
          </div>

          <div className={styles.reviewText}>
            <p className={styles.reviewLine}>
              <span className={styles.strong}>Достоинства:</span>{' '}
              <span className={styles.valueMuted}>{review?.pros || '—'}</span>
            </p>
            <p className={styles.reviewLine}>
              <span className={styles.strong}>Недостатки:</span>{' '}
              <span className={styles.valueNormal}>{review?.cons || '—'}</span>
            </p>
            <p className={styles.reviewLine}>
              <span className={styles.strong}>Комментарий:</span>{' '}
              <span className={styles.valueMuted}>
                {review?.comment || '—'}
              </span>
            </p>
          </div>
        </div>

        {/* Column 3 — Order info */}
        <div className={styles.orderCol}>
          <div>
            <div className={styles.orderNumberRow}>
              <span>№ {order?.number || ''}</span>
              <button
                type="button"
                className={styles.copyButton}
                aria-label="Скопировать номер заказа"
                onClick={() => copyToClipboard(order?.number)}
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 16 16"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M11.9424 6.15337C11.9424 5.5934 11.7199 5.05636 11.324 4.6604C10.928 4.26444 10.391 4.04199 9.83101 4.04199H2.97042C2.69316 4.04199 2.4186 4.0966 2.16244 4.20271C1.90627 4.30882 1.67352 4.46434 1.47746 4.6604C1.2814 4.85646 1.12587 5.08922 1.01977 5.34538C0.913662 5.60154 0.85905 5.8761 0.85905 6.15337V13.014C0.85905 13.2912 0.913662 13.5658 1.01977 13.8219C1.12587 14.0781 1.2814 14.3109 1.47746 14.5069C1.67352 14.703 1.90627 14.8585 2.16244 14.9646C2.4186 15.0707 2.69316 15.1253 2.97042 15.1253H9.83101C10.1083 15.1253 10.3828 15.0707 10.639 14.9646C10.8952 14.8585 11.1279 14.703 11.324 14.5069C11.52 14.3109 11.6756 14.0781 11.7817 13.8219C11.8878 13.5658 11.9424 13.2912 11.9424 13.014V6.15337Z"
                    stroke="#7E7E7E"
                    strokeWidth="1.71818"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <path
                    d="M14.3066 11.7501C14.5497 11.612 14.7518 11.4121 14.8925 11.1705C15.0333 10.929 15.1075 10.6545 15.1078 10.375V2.45833C15.1078 1.5875 14.3953 0.875 13.5245 0.875H5.60779C5.01404 0.875 4.69104 1.17979 4.42029 1.66667"
                    stroke="#7E7E7E"
                    strokeWidth="1.75"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>
            </div>
            <div className={styles.orderDate}>от {order?.dateLabel || ''}</div>
          </div>
          {originLabel ? (
            <div className={styles.badge}>{originLabel}</div>
          ) : null}
        </div>

        {/* Column 4 — Actions */}
        <div className={styles.actionsCol}>
          <div className={styles.orderButtons}>
            <button
              type="button"
              className={styles.orderButton}
              onClick={() => onOpenOrder?.(order)}
            >
              К заказу
            </button>

            <button
              type="button"
              className={styles.iconButton}
              onClick={() => onDelete?.(review)}
              aria-label="Удалить отзыв"
            >
              <TrashIcon />
            </button>
          </div>
          <span className={styles.expandSpacer} aria-hidden="true" />

          <button
            type="button"
            className={styles.expandButton}
            onClick={() => onToggleExpand?.(!expanded)}
            aria-label={expanded ? 'Свернуть' : 'Развернуть'}
          >
            <ChevronIcon
              className={cn(
                styles.actionIcon,
                styles.chevron,
                expanded && styles.chevronOpen,
              )}
            />
          </button>
        </div>
      </div>
    </article>
  );
}
