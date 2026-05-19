import { forwardRef } from 'react';

import { cn } from '@/shared/lib/utils';

// Sizes — matches the heights operators see across staff/roles/permissions.
// sm = 36px (filter pills, inline actions), md = 38px (primary action bar),
// lg = 42px (modal CTAs, deactivate/reactivate).
const SIZES = {
  sm: 'h-9 px-4 text-[13px]',
  md: 'h-[38px] px-[18px] text-sm',
  lg: 'h-[42px] px-5 text-sm',
};

// Variants. `primary` = dark filled (main CTA), `secondary` = bordered
// ghost on white, `danger` = red filled (destructive confirmations),
// `success` = green filled (reactivate-style flows). All share the same
// focus ring + disabled styling so behaviour stays predictable.
const VARIANTS = {
  primary:
    'bg-app-text-dark text-white hover:bg-black active:translate-y-[1px]',
  secondary:
    'border border-app-border text-app-text bg-white hover:bg-app-card',
  danger: 'bg-red-600 text-white hover:bg-red-700 active:translate-y-[1px]',
  success:
    'bg-app-success text-white hover:opacity-90 active:translate-y-[1px]',
};

/**
 * Single source of truth for buttons inside the staff/roles/permissions
 * surface. Scope-limited on purpose — a project-wide button refactor is a
 * separate effort (lots of places hard-code their own classes today).
 */
export const Button = forwardRef(function Button(
  {
    variant = 'primary',
    size = 'md',
    type = 'button',
    className,
    disabled,
    fullWidth = false,
    children,
    ...rest
  },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled}
      className={cn(
        'inline-flex items-center justify-center rounded-xl font-semibold whitespace-nowrap transition-colors focus-visible:ring-2 focus-visible:ring-[#4a90d9] focus-visible:ring-offset-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50',
        SIZES[size] ?? SIZES.md,
        VARIANTS[variant] ?? VARIANTS.primary,
        fullWidth && 'w-full',
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
});
