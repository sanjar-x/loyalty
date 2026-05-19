'use client';

import { cn } from '@/shared/lib/utils';

// Section wrapper used by every block of the walk-in form. Keeps the
// outer rhythm (padding, rounded corner, panel background) consistent so
// the form reads as a single document rather than a stack of disparate
// cards.
export function FormSection({ title, description, children, className }) {
  return (
    <section
      className={cn(
        'bg-app-panel border-app-border flex flex-col gap-4 rounded-3xl border p-6',
        className,
      )}
    >
      <header className="flex flex-col gap-1">
        <h2 className="text-app-text text-lg font-semibold">{title}</h2>
        {description && <p className="text-app-muted text-sm">{description}</p>}
      </header>
      {children}
    </section>
  );
}

// Plain text-field primitive — the walk-in form has 15+ similar inputs
// and pulling in a heavier component (or adding one to shared/) for a
// single feature would just create more API surface. Keep it local until
// a second consumer appears.
//
// `className` lands on the outer <label> wrapper (for layout/width
// control); `inputClassName` extends the input's own styles. Spreading
// arbitrary props onto the input would clobber its baseline border /
// padding, so width/margin tweaks must go through `className`.
export function TextField({
  label,
  required = false,
  error,
  helper,
  className,
  inputClassName,
  ...inputProps
}) {
  const id = inputProps.id ?? inputProps.name;
  return (
    <label className={cn('flex flex-col gap-1', className)} htmlFor={id}>
      {label && (
        <span className="text-app-muted text-xs font-medium">
          {label}
          {required && <span className="text-app-danger ml-1">*</span>}
        </span>
      )}
      <input
        id={id}
        className={cn(
          'border-app-border bg-app-panel text-app-text rounded-lg border px-3 py-2 text-sm transition-colors outline-none',
          'focus:border-app-text',
          error && 'border-app-danger focus:border-app-danger',
          inputClassName,
        )}
        aria-invalid={error ? true : undefined}
        {...inputProps}
      />
      {error ? (
        <span className="text-app-danger text-xs" role="alert">
          {error}
        </span>
      ) : helper ? (
        <span className="text-app-muted text-xs">{helper}</span>
      ) : null}
    </label>
  );
}
