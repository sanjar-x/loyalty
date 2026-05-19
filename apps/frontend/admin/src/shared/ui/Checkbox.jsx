import { cn } from '@/shared/lib/utils';

function CheckIcon({ className }) {
  return (
    <svg
      className={className}
      viewBox="0 0 12 12"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M2.5 6.4 4.7 8.6 9.5 3.4"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/**
 * Custom checkbox primitive. The native <input> is kept for semantics,
 * focus and keyboard handling — only its appearance is replaced: a raw
 * browser checkbox looks foreign in the themed UI and renders
 * inconsistently across operating systems.
 *
 * The native control is laid out behind a centred SVG tick; `peer-checked`
 * reveals the tick. `onChange` receives the next boolean (not the event).
 */
export function Checkbox({
  checked,
  onChange,
  disabled = false,
  id,
  ariaLabel,
  className,
}) {
  return (
    <span
      className={cn(
        'relative inline-flex h-[18px] w-[18px] shrink-0 items-center justify-center',
        disabled && 'opacity-50',
        className,
      )}
    >
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        disabled={disabled}
        aria-label={ariaLabel}
        className={cn(
          'peer absolute inset-0 h-full w-full cursor-pointer appearance-none rounded-md border transition-colors',
          'border-app-border bg-app-panel',
          'enabled:hover:border-app-muted',
          'checked:border-app-text-dark checked:bg-app-text-dark',
          'focus-visible:ring-app-text-dark/25 focus-visible:ring-2 focus-visible:outline-none',
          'disabled:cursor-not-allowed',
        )}
      />
      <CheckIcon className="pointer-events-none relative h-3 w-3 text-white opacity-0 transition-opacity peer-checked:opacity-100" />
    </span>
  );
}
