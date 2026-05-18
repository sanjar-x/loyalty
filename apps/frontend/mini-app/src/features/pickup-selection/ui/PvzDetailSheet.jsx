'use client';

import { Clock, CreditCard, MapPin, Phone } from 'lucide-react';

import Button from '@/shared/ui/Button';
import { cn } from '@/shared/lib/ui-utils';

import styles from './PvzDetailSheet.module.css';

/**
 * PVZ detail sheet — the single modal component for both the list and map
 * steps of the pickup page (CHK-019). Pure: driven only by props, no
 * Zustand or RTKQ calls.
 *
 * The "Deliver here" button calls `onConfirm(point)` — the consumer
 * navigates to /checkout with URL params (lat/lon is also written for the
 * CHK-018 chain).
 *
 * Sheet is bottom-anchored, max-width 28rem (mobile-first); focus trap and
 * ESC binding will be added in CHK-008 (Sprint 2).
 *
 * @typedef {Object} PvzPoint
 * @property {string} externalId
 * @property {string} providerCode
 * @property {string} [providerLabel]
 * @property {string} [pickupPointTypeLabel]
 * @property {string} addressLine
 * @property {string} [workSchedule]
 * @property {string} [phone]
 * @property {boolean} [isCashAllowed]
 * @property {boolean} [isCardAllowed]
 * @property {number} [lat]
 * @property {number} [lon]
 *
 * @typedef {Object} PvzDetailSheetProps
 * @property {boolean} open
 * @property {PvzPoint | null} point
 * @property {() => void} onClose
 * @property {(point: PvzPoint) => void} onConfirm
 */
export default function PvzDetailSheet({ open, point, onClose, onConfirm }) {
  if (!open || !point) return null;

  const titleText = point.pickupPointTypeLabel
    ? `${point.providerLabel} · ${point.pickupPointTypeLabel}`
    : point.providerLabel || '';

  const scheduleLines = point.workSchedule
    ? point.workSchedule
        .split(/[;\n]+/)
        .map((s) => s.trim())
        .filter(Boolean)
    : [];

  const payment = [point.isCashAllowed ? 'наличные' : null, point.isCardAllowed ? 'карта' : null]
    .filter(Boolean)
    .join(', ');

  return (
    <div className={styles.sheet}>
      <div className={styles.sheetInner}>
        <div className={styles.card}>
          <div className={styles.handleWrap}>
            <div className={styles.handle} />
          </div>

          <div className={styles.content}>
            <div className={styles.header}>
              <div className={styles.title}>{titleText}</div>
              <button
                type="button"
                aria-label="Закрыть"
                onClick={onClose}
                className={styles.closeBtn}
              >
                <img src="/icons/global/xicon.svg" alt="" className={styles.closeIcon} />
              </button>
            </div>

            <div className={styles.detailList}>
              <div className={styles.detailRow}>
                <MapPin className={styles.detailIcon} />
                <div className={styles.detailText}>{point.addressLine}</div>
              </div>

              {scheduleLines.length > 0 ? (
                <div className={styles.detailRow}>
                  <Clock className={styles.detailIcon} />
                  <div className={styles.scheduleText}>
                    {scheduleLines.map((line, i) => (
                      <div key={i}>{line}</div>
                    ))}
                  </div>
                </div>
              ) : null}

              {point.phone ? (
                <div className={styles.detailRow}>
                  <Phone className={styles.detailIcon} />
                  <a href={`tel:${point.phone}`} className={styles.phoneLink}>
                    {point.phone}
                  </a>
                </div>
              ) : null}

              {payment ? (
                <div className={styles.detailRow}>
                  <CreditCard className={styles.detailIcon} />
                  <div className={styles.detailText}>{payment}</div>
                </div>
              ) : null}
            </div>

            <div className={styles.confirmContainer}>
              <Button
                type="button"
                variant="primary"
                size="lg"
                className={cn(styles.confirmBtn)}
                onClick={() => onConfirm(point)}
              >
                Доставить сюда
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
