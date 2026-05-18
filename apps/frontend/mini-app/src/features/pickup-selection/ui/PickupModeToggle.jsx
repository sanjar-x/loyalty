import { cn } from '@/shared/lib/ui-utils';

import styles from './page.module.css';

/**
 * Pickup view mode toggle — "Map" / "List". Audit #1:
 * presentation extracted from `app/checkout/pickup/page.jsx`.
 *
 * @param {{ step: string, onSelectStep: (s: 'map'|'list') => void }} props
 */
export default function PickupModeToggle({ step, onSelectStep }) {
  return (
    <div className={styles.c2}>
      <button
        type="button"
        aria-pressed={step === 'map'}
        className={cn(
          styles.toggleButton,
          step === 'map' ? styles.toggleButtonActive : styles.toggleButtonInactive
        )}
        onClick={() => onSelectStep('map')}
      >
        На карте
      </button>
      <button
        type="button"
        aria-pressed={step === 'list'}
        className={cn(
          styles.toggleButton,
          step === 'list' ? styles.toggleButtonActive : styles.toggleButtonInactive
        )}
        onClick={() => onSelectStep('list')}
      >
        Списком
      </button>
    </div>
  );
}
