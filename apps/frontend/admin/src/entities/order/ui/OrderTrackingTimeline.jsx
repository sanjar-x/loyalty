'use client';

import { formatDateTime, cn } from '@/shared/lib/utils';

// Vertical, chronologically-ordered timeline of cross-border + last-mile
// shipping events. Backend already merges both legs into a single `steps`
// array on `OrderTrackingResponse`, so all this component does is render
// them with the leg badge alongside.
//
// TODO(backend-gap): /api/v1/admin/orders/{id}/tracking strict variant.
//   Admin currently relays through the customer-facing tracking endpoint
//   (`/api/v1/orders/{id}/tracking`) which carries a Bearer-only auth
//   check. If a strict admin variant lands later (raw FSM + dual-leg
//   breakdown) only the BFF route (`app/api/admin/orders/[orderId]/tracking/route.js`)
//   needs to flip its targetPath.
export function OrderTrackingTimeline({ tracking, loading = false }) {
  if (loading) {
    return (
      <div className="bg-app-card h-40 w-full animate-pulse rounded-2xl" />
    );
  }
  if (!tracking) {
    return (
      <div className="bg-app-card text-app-muted rounded-2xl p-6 text-sm">
        Трекинг недоступен. Возможно, заказ ещё не передан перевозчику.
      </div>
    );
  }

  const steps = Array.isArray(tracking.steps) ? tracking.steps : [];

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <TrackBlock
          title="Cross-border"
          number={tracking.crossBorderTrack}
          fallback={tracking.incomingDeclaration}
          fallbackLabel="incoming_declaration"
        />
        <TrackBlock
          title="Last-mile"
          number={tracking.lastMileTrack}
          fallback={tracking.crossBorderStatusLabel}
          fallbackLabel="последний статус"
        />
      </div>

      {steps.length === 0 ? (
        <div className="bg-app-card text-app-muted rounded-2xl p-6 text-sm">
          Событий ещё нет.
        </div>
      ) : (
        <ol className="border-app-border relative ml-4 border-l pl-6">
          {steps.map((step, idx) => (
            <li
              key={`${step.occurredAt}-${idx}`}
              className="relative pb-5 last:pb-0"
            >
              <span
                aria-hidden="true"
                className={cn(
                  'border-app-panel absolute -left-[31px] mt-1.5 h-3 w-3 rounded-full border-2',
                  step.leg === 'cross_border'
                    ? 'bg-app-text-dark'
                    : 'bg-app-success',
                )}
              />
              <div className="flex flex-wrap items-baseline gap-2">
                <span className="text-app-text text-sm font-semibold">
                  {step.label}
                </span>
                <LegBadge leg={step.leg} />
              </div>
              <p className="text-app-muted mt-0.5 text-xs">
                {formatDateTime(step.occurredAt)} ·{' '}
                <code className="bg-app-card rounded px-1 py-0.5">
                  {step.code}
                </code>
              </p>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

function TrackBlock({ title, number, fallback, fallbackLabel }) {
  return (
    <div className="border-app-border rounded-2xl border p-4">
      <p className="text-app-muted text-xs font-medium uppercase">{title}</p>
      {number ? (
        <p className="text-app-text mt-1 font-mono text-sm">{number}</p>
      ) : fallback ? (
        <p className="text-app-muted mt-1 text-xs">
          {fallbackLabel}: <span className="text-app-text">{fallback}</span>
        </p>
      ) : (
        <p className="text-app-muted mt-1 text-xs">—</p>
      )}
    </div>
  );
}

function LegBadge({ leg }) {
  if (!leg) return null;
  const isCross = leg === 'cross_border';
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-md px-1.5 py-0.5 text-[10px] font-semibold uppercase',
        isCross ? 'bg-app-text-dark text-white' : 'bg-app-success text-white',
      )}
    >
      {isCross ? 'cross-border' : leg}
    </span>
  );
}
