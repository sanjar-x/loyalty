'use client';

import { cn } from '@/shared/lib/ui-utils';

import { formatPassportIssueDate } from '../lib/formatPassportIssueDate';
import { maskPassportNumber } from '../lib/maskPassportNumber';
import PassportBadge from './PassportBadge';
import styles from './PassportCard.module.css';

/**
 * Read-only summary card for a Passport row. Used by `PassportStep` in
 * `features/buy-now-checkout/` (list-pick mode) and reusable in any
 * future passport-selection UI (e.g. cart-flow checkout, profile page).
 *
 * PII surface area is minimised: full ИНН stays inside the form/edit
 * sheet; the card shows only the masked passport identifier + issue
 * date + validation status.
 *
 * Props:
 *   • passport          — codegen `PassportSchema` shape
 *   • selected          — when true, the card renders the chosen state
 *   • onSelect          — invoked on tap / Enter; entity is read-only
 *                         so the selection callback is the only action
 *   • disabled          — when true, suppresses interaction (e.g. while
 *                         a parent mutation is in flight)
 *   • testId            — optional `data-testid` for the FE-8 Playwright
 *                         scenarios
 */
export default function PassportCard({
  passport,
  selected = false,
  onSelect,
  disabled = false,
  testId,
}) {
  if (!passport) return null;
  const display = passport.fullNameRu || passport.fullNameLat || 'Без имени';
  const masked = maskPassportNumber(passport.passportSerial, passport.passportNumber);
  const issued = formatPassportIssueDate(passport.passportIssueDate);

  return (
    <button
      type="button"
      onClick={() => (!disabled && onSelect ? onSelect(passport) : null)}
      aria-pressed={selected}
      aria-disabled={disabled || undefined}
      disabled={disabled}
      data-testid={testId}
      className={cn(styles.root, selected && styles.selected)}
    >
      <div className={styles.head}>
        <span className={styles.name}>{display}</span>
        <PassportBadge
          status={passport.validationStatus}
          reason={passport.validationFailedReason}
        />
      </div>
      <div className={styles.meta}>
        <span className={styles.passportLine}>{masked}</span>
        {issued ? <span className={styles.issued}>выдан {issued}</span> : null}
      </div>
    </button>
  );
}
