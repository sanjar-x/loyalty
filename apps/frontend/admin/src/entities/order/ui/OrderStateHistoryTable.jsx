'use client';

import { ORDER_STATUS_LABELS } from '../lib/constants';
import { formatDateTime, cn } from '@/shared/lib/utils';

// Renders the audit-log feed of FSM transitions with from→to / event type /
// actor / timestamp columns. Backend ships entries chronologically (oldest
// first) but admins typically want the freshest event at the top — we sort
// in render to keep the API contract untouched.
export function OrderStateHistoryTable({ entries = [], loading = false }) {
  if (loading) {
    return (
      <div className="bg-app-card h-32 w-full animate-pulse rounded-2xl" />
    );
  }
  if (!entries.length) {
    return (
      <div className="bg-app-card text-app-muted rounded-2xl p-6 text-sm">
        История статусов пуста.
      </div>
    );
  }

  const sorted = [...entries].sort(
    (a, b) =>
      new Date(b.occurredAt).valueOf() - new Date(a.occurredAt).valueOf(),
  );

  return (
    <div className="border-app-border overflow-hidden rounded-2xl border">
      <table className="w-full text-left text-sm">
        <thead className="bg-app-card text-app-muted">
          <tr>
            <th className="px-4 py-3 font-medium">Когда</th>
            <th className="px-4 py-3 font-medium">Из</th>
            <th className="px-4 py-3 font-medium">В</th>
            <th className="px-4 py-3 font-medium">Событие</th>
            <th className="px-4 py-3 font-medium">Кто</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((entry) => (
            <tr
              key={entry.id}
              className="border-app-border border-t last:border-b-0"
            >
              <td className="text-app-muted px-4 py-3 whitespace-nowrap">
                {formatDateTime(entry.occurredAt)}
              </td>
              <td className="text-app-text px-4 py-3">
                <StatusPill status={entry.fromStatus} />
              </td>
              <td className="text-app-text px-4 py-3">
                <StatusPill status={entry.toStatus} highlighted />
              </td>
              <td className="text-app-muted px-4 py-3">
                <code className="bg-app-card rounded px-1.5 py-0.5 text-xs">
                  {entry.eventType}
                </code>
              </td>
              <td className="text-app-muted px-4 py-3">
                <span className="font-medium">{entry.actorType}</span>
                {entry.actorId ? (
                  <span className="text-app-muted ml-1 text-xs">
                    {String(entry.actorId).slice(0, 8)}…
                  </span>
                ) : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StatusPill({ status, highlighted = false }) {
  if (!status) return <span className="text-app-muted">—</span>;
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium',
        highlighted
          ? 'bg-app-text-dark text-white'
          : 'bg-app-card text-app-text-dark',
      )}
    >
      {ORDER_STATUS_LABELS[status] ?? status}
    </span>
  );
}
