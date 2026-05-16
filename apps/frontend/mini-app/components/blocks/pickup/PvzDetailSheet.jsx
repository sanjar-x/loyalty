'use client';

import { Clock, CreditCard, MapPin, Phone } from 'lucide-react';

import Button from '@/components/ui/Button';
import { cn } from '@/lib/format/cn';

import styles from './PvzDetailSheet.module.css';

/**
 * PVZ detail sheet — pickup sahifasidagi list va map step'lari uchun
 * yagona modal komponent (CHK-019). Pure: faqat props orqali boshqariladi,
 * Zustand yoki RTKQ chaqirig'i yo'q.
 *
 * "Доставить сюда" tugmasi `onConfirm(point)` ni chaqiradi — iste'molchi
 * /checkout'ga URL params bilan navigate qiladi (lat/lon ham yoziladi
 * CHK-018 chain'i uchun).
 *
 * Sheet bottom-anchored, max-width 28rem (mobile-first); CHK-008 da
 * focus trap va ESC binding qo'shiladi (Sprint 2).
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
